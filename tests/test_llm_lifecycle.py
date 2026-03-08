import pytest
import subprocess
import time
import requests
import os
import signal
import sys
from pathlib import Path

# Config
HUB_URL = "http://127.0.0.1:8002"
ENGINE_URL = "http://127.0.0.1:8001"
ROOT_DIR = Path(__file__).parent.parent.resolve()
START_SCRIPT = ROOT_DIR / "start_llm.py"


@pytest.fixture(scope="module")
def llm_server():
    """Starts start_llm.py in a subprocess and kills it after tests."""
    # [X-Ray auto-fix] print(f"\n[Test] Launching {START_SCRIPT}...")
    # Run in Hub Mode or just normal mode? Normal mode starts engine.
    # We use --hub-only to test API first, or full run?
    # User wants to test "start stop", so full run is better, but risky on CI/local unless we assume 8001/8002 are free.

    # We will assume environment is clean or we can kill existing.

    proc = subprocess.Popen(
        [sys.executable, str(START_SCRIPT), "--hub-only"],  # Start safe hub only first
        cwd=ROOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
    )

    # Wait for server to be ready
    api_ready = False
    for i in range(30):
        try:
            resp = requests.get(HUB_URL + "/", timeout=1)
            if resp.status_code == 200:
                api_ready = True
                break
        except Exception:
            time.sleep(1)

    if not api_ready:
        proc.terminate()
        pytest.fail("Hub API failed to start within 30 seconds")

    yield proc

    # Teardown
    print("\n[Test] Tearing down server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_hub_health(llm_server):
    """Verify Hub API is responding."""
    resp = requests.get(HUB_URL + "/", timeout=30)
    assert resp.status_code == 200
    assert "ZenAI Hub Active" in resp.text


def test_model_endpoints(llm_server):
    """Verify model listing endpoint."""
    resp = requests.get(HUB_URL + "/models/available", timeout=30)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Note: might be empty if no models, but list is expected.


def test_update_check(llm_server):
    """Verify update checker endpoint works."""
    resp = requests.get(HUB_URL + "/updates/check", timeout=30)
    # This might fail if no internet, but code usually returns 500 or json error.
    # We accept 200 or 500, as long as it returns JSON.
    assert resp.status_code in [200, 500]
    try:
        data = resp.json()
        assert isinstance(data, dict)
    except Exception:
        pytest.fail("Did not return valid JSON")
