import pytest
import asyncio
import aiohttp
import random
import string
import os
import sys
import psutil


# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_system import config


class TestLLMChaos:
    """Explicitly verify 'Iron-Clad' resilience of the LLM Engine."""

    @pytest.mark.asyncio
    async def test_concurrency_flood(self):
        """Flood the engine with 50 concurrent requests."""
        if not config.BIN_DIR.exists():
            pytest.skip("No engine binary found")

        async def send_request(session, i):
            """Send request."""
            try:
                payload = {"prompt": f"Test request {i}", "n_predict": 10}
                async with session.post(
                    f"http://127.0.0.1:{config.llm_port}/completion", json=payload, timeout=5
                ) as resp:
                    return resp.status
            except Exception as e:
                return f"Error: {e}"

        async with aiohttp.ClientSession() as session:
            tasks = [send_request(session, i) for i in range(50)]
            results = await asyncio.gather(*tasks)

            # We expect 200s or 503s (Busy), but NOT crashes (Connection Refused)
            # If server crashes, it's a fail.
            crashes = [r for r in results if isinstance(r, str) and "Connection refused" in r]
            assert len(crashes) == 0, f"Engine crashed under load: {crashes[:3]}"

    @pytest.mark.asyncio
    async def test_tokenizer_stress(self):
        """Send a massive 1MB payload to stress the tokenizer."""
        # Generating 1MB of random garbage text
        garbage = "".join(random.choices(string.ascii_letters + string.punctuation, k=1024 * 1024))

        payload = {"prompt": garbage, "n_predict": 1}

        async with aiohttp.ClientSession() as session:
            try:
                # Should return 400 (Context Limit) or handle gracefully
                async with session.post(
                    f"http://127.0.0.1:{config.llm_port}/completion", json=payload, timeout=10
                ) as resp:
                    assert resp.status in [200, 400, 413, 500], f"Unexpected status: {resp.status}"
            except Exception as e:
                # Timeout is acceptable for massive payload, but crash is not
                if "Connection refused" in str(e):
                    pytest.fail("Engine crashed on massive payload!")

    def test_recovery_logic(self):
        """Identify Llama Server process, KILL IT, and verify it comes back."""
        import time
        from utils import is_port_active

        # 1. Verify it's running originally
        assert is_port_active(config.llm_port), "Engine not running at start of test"

        # 2. Find the PID
        target_pid = None
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            if "llama-server" not in p.info["name"].lower():
                continue
            target_pid = p.info["pid"]
            break

        if not target_pid:
            pytest.skip("Could not find llama-server process to kill")

        # 3. KILL IT
        # [X-Ray auto-fix] print(f"\n💀 KILLING PID {target_pid} FOR SCIENCE...")
        psutil.Process(target_pid).kill()

        # 4. Wait for Auto-Recovery (Max 15s)
        # The Orchestrator loop runs every ~2s
        recovered = False
        for _ in range(15):
            time.sleep(1)
            if is_port_active(config.llm_port):
                recovered = True
                break

        assert recovered, "Orchestrator FAILED to restart the engine after crash!"
        print("\n✅ Engine successfully resurrected! 🧟")
