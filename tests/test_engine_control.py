import pytest
import subprocess
import sys
import time
import requests
import psutil
from pathlib import Path

# --- Config ---
from test_utils import _default_models_dir
MODEL_DIR = _default_models_dir()
MODEL_PATH = MODEL_DIR / "qwen2.5-0.5b-instruct-q5_k_m.gguf"

if not MODEL_PATH.exists():
    candidates = list(MODEL_DIR.glob("*.gguf"))
    if candidates:
        MODEL_PATH = candidates[0]
ROOT_DIR = Path(__file__).parent.parent.resolve()
START_SCRIPT = ROOT_DIR / "start_llm.py"
BIN_DIR = ROOT_DIR / "_bin"
LLAMA_EXE = "llama-server.exe"


def get_llama_pids():
    """Return list of PIDs for llama-server.exe"""
    pids = []
    for proc in psutil.process_iter(["pid", "name"]):
        if proc.info["name"] == LLAMA_EXE:
            pids.append(proc.info["pid"])
    return pids


def kill_all_llama():
    """Cleanup helper"""
    for proc in psutil.process_iter(["pid", "name"]):
        if proc.info["name"] != LLAMA_EXE:
            continue
        try:
            proc.kill()
        except Exception:
            pass


@pytest.fixture(scope="module")
def clean_env():
    kill_all_llama()
    yield
    kill_all_llama()


def _do_test_engine_lifecycle_setup():
    """Helper: setup phase for test_engine_lifecycle."""

    # Skip if model or native llama binary not present in this environment
    LLAMA_EXE_PATH = Path(__file__).parent.parent / "_bin" / "llama-server.exe"
    if not MODEL_PATH.exists() or not LLAMA_EXE_PATH.exists():
        pytest.skip(f"Required model or LLM binary not found ({MODEL_PATH}, {LLAMA_EXE_PATH})")

    # --- Step 1: Start Instance A ---
    print("\n[Test] Starting Instance A...")
    # We use --guard-bypass for the first one so it doesn't kill unrelated things,
    # but strictly we want to test guard.
    # Let's just run it.

    cmd = [sys.executable, str(START_SCRIPT), "--model", str(MODEL_PATH)]

    # We set environment variable to avoid "input()" pause on crash/exit?
    # The script uses input() at end. We can pipe \n to it if needed.
    # But usually we keep it running.

    proc_a = subprocess.Popen(
        cmd,
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,  # To send \n if needed
        text=True,
        shell=False,
    )

    return cmd, proc_a


def _do_test_engine_lifecycle_init():
    """Helper: setup phase for test_engine_lifecycle."""

    cmd, proc_a = _do_test_engine_lifecycle_setup()
    # Wait for startup (API 8001)
    port_active = False
    pid_a = None

    for i in range(20):
        pids = get_llama_pids()
        if pids:
            pid_a = pids[0]
            # Check API
            try:
                resp = requests.get("http://127.0.0.1:8001/health", timeout=1)
                if resp.status_code == 200:
                    port_active = True
                    break
            except Exception:
                pass
        time.sleep(1)

    if not pid_a:
        # Check stdout
        out, err = proc_a.communicate(timeout=1)
        # [X-Ray auto-fix] print(f"STDOUT: {out}")
        # [X-Ray auto-fix] print(f"STDERR: {err}")
        pytest.fail("Instance A failed to start llama-server.exe")

    # [X-Ray auto-fix] print(f"[Test] Instance A Running (PID: {pid_a})")
    assert port_active, "API 8001 not responding"

    return cmd, pid_a, proc_a


def test_engine_lifecycle(clean_env):
    """
    1. Start Engine (Instance A)
    2. Verify Running
    3. Start Engine (Instance B) -> Should kill A
    4. Verify A dead, B running
    """
    cmd, pid_a, proc_a = _do_test_engine_lifecycle_init()
    # --- Step 2: Start Instance B (Trigger Guard) ---
    print("[Test] Starting Instance B (Should kill A)...")

    proc_b = subprocess.Popen(
        cmd,
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        text=True,
        shell=False,
    )

    # Give it time to execute guard
    time.sleep(5)

    # --- Step 3: Verify Swap ---
    current_pids = get_llama_pids()
    # [X-Ray auto-fix] print(f"[Test] Current PIDs: {current_pids}")
    assert pid_a not in current_pids, "Instance A (PID {pid_a}) should have been killed!"
    assert len(current_pids) > 0, "Instance B should be running"

    pid_b = current_pids[0]
    assert pid_b != pid_a, "PID should have changed"

    # [X-Ray auto-fix] print(f"[Test] Instance B Running (PID: {pid_b}) - Swap Successful")
    # Cleanup
    proc_a.terminate()
    proc_b.terminate()


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
