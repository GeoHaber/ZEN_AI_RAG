import os
import sys
import time
import random
import asyncio
import subprocess
from pathlib import Path

# --- Path Injection: Ensure we can find zena_mode from any directory ---
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

from zena_mode.arbitrage import SwarmArbitrator
from test_utils import _default_models_dir

# Configuration
MODEL_DIR = _default_models_dir()
START_LLM_SCRIPT = Path(__file__).resolve().parent.parent / "start_llm.py"
PORTS = [8001] + list(range(8005, 8011))  # Ports for up to 7 experts
REF_PORT = 8001


def get_available_models():
    return list(MODEL_DIR.glob("*.gguf"))


def kill_swarm():
    """Kill any existing llama-server or start_llm processes."""
    print("[Clean] Cleaning up existing processes...")
    subprocess.run(["taskkill", "/F", "/IM", "llama-server.exe", "/T"], capture_output=True, shell=False)
    time.sleep(2)


def start_expert(model_path, port, agent_idx):
    """Launch a single LLM instance on a specific port."""
    env = os.environ.copy()
    env["LLM_PORT"] = str(port)
    # Give limited threads to experts to avoid system choke
    env["LLM_THREADS"] = "2"

    cmd = [sys.executable, str(START_LLM_SCRIPT), "--guard-bypass", "--model", str(model_path)]

    # Capture logs to help debug startup issues
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = open(log_dir / f"expert_{agent_idx}.log", "w")

    process = subprocess.Popen(
        cmd,
        env=env,
        cwd=str(START_LLM_SCRIPT.parent),  # CRITICAL: Run from project root
        stdout=log_file,
        stderr=log_file,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        shell=False,
    )
    return process, log_file


async def wait_for_swarm(ports):
    """Wait until all requested ports are responding to health check."""
    import httpx

    async with httpx.AsyncClient() as client:
        for port in ports:
            ready = False
            for _ in range(30):  # 30 attempts, 60s total
                try:
                    resp = await client.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
                    if resp.status_code == 200:
                        ready = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(2)
            if not ready:
                print(f"[Warning] Port {port} timed out during startup.")
                pass


async def run_tier_test(n):
    """Run tier test."""
    print(f"\n{'=' * 80}")
    print(f"🚀 STARTING STRESS TEST TIER: N={n}")
    print(f"{'=' * 80}")
    models = get_available_models()
    if not models:
        print("Error: No models found in C:\\AI\\Models")
        return

    selected_models = random.sample(models, min(n, len(models)))
    # If n > len(models), we repeat some (mocking unique models)
    while len(selected_models) < n:
        selected_models.append(random.choice(models))

    kill_swarm()

    processes = []
    log_files = []
    print(f"[Setup] Launching {n} random models...")
    for i in range(n):
        port = PORTS[i]
        m = selected_models[i]
        print(f"  > Agent {i + 1} [Identity]: {m.name}")
        p, log_f = start_expert(m, port, i + 1)
        processes.append(p)
        log_files.append(log_f)

    print("[Setup] Waiting for experts to initialize (this can take 20s+)...")
    await wait_for_swarm(PORTS[:n])

    # Run the query
    arbitrator = SwarmArbitrator(ports=PORTS[:n])
    question = "If I have 3 oranges and eat 2, then buy 5 more, how many do I have? Explain the logic."

    print("\n[Audit] Submitting Question: ", question)
    start_time = time.time()

    # We consume the generator to trigger terminal output (which already has our desired trace)
    full_answer = ""
    async for chunk in arbitrator.get_cot_response(question, "You are a logical math expert.", verbose=False):
        full_answer += chunk

    total_time = time.time() - start_time
    print(f"\n[Metrics] Global Tier Completion: {total_time:.2f}s")
    # Clean up
    for p in processes:
        p.terminate()
    for f in log_files:
        f.close()
    kill_swarm()


async def main():
    """Main."""
    # User requested 1 to 7
    # Let's do a few tiers to show the scaling clearly
    tiers = [1, 3, 5, 7]
    for n in tiers:
        try:
            await run_tier_test(n)
            print(f"\n[Tier {n}] Completed successfully.")
        except Exception:
            print(f"\n[Tier {n}] FAILED: {e}")
            pass
        print("\nCooldown (10s)...")
        await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Stopped] User interrupted.")
        kill_swarm()
