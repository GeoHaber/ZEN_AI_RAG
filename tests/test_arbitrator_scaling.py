import requests
import time
import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch

# --- Path Injection ---
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

from zena_mode.arbitrage import SwarmArbitrator
from config_system import AppConfig


class TestArbitratorScaling(unittest.TestCase):
    """TestArbitratorScaling class."""

    def test_arbitrator_discovers_scaled_swarm(self):
        """Verify that arbitrator finds the correct number of experts after scaling."""

        # Mock Hub scale response and LLM health endpoints to make the test hermetic
        class _MockResp:
            """_MockResp class."""

            def __init__(self, status_code=200, text=""):
                self.status_code = status_code
                self.text = text

        def _fake_post(url, json=None, timeout=None):
            # Simulate hub returning ports 8005 and 8006
            body = '{"status": "scaled", "ports": [8005, 8006]}'
            return _MockResp(200, body)

        # Patch requests.post locally
        requests_post_original = requests.post
        requests.post = _fake_post

        # Use respx to mock httpx AsyncClient health checks for ports 8001,8005,8006
        import respx as _respx
        import httpx as _httpx

        # Patch the config object instead of module-level variables
        with patch("zena_mode.arbitrage.config") as mock_config:
            mock_config.swarm_enabled = True
            mock_config.swarm_size = 7  # Allow up to 7 for discovery tests
            mock_config.llm_port = 8001
            mock_config.host = "127.0.0.1"
            mock_config.BASE_DIR = root

            with _respx.mock() as mock:
                # register health endpoints for main + experts explicitly (including ports)
                mock.get("http://127.0.0.1:8001/health").mock(return_value=_httpx.Response(200, json={"status": "ok"}))
                mock.get("http://127.0.0.1:8005/health").mock(return_value=_httpx.Response(200, json={"status": "ok"}))
                mock.get("http://127.0.0.1:8006/health").mock(return_value=_httpx.Response(200, json={"status": "ok"}))

                # Initialize arbitrator and run discovery
                arbitrator = SwarmArbitrator()
                import asyncio

                asyncio.run(arbitrator.discover_swarm())

        # restore requests.post
        requests.post = requests_post_original

        # We expect 2 brains total: 8001 (main) + 8005 (expert)
        # [X-Ray auto-fix] print(f"Found ports: {arbitrator.ports}")
        self.assertGreaterEqual(len(arbitrator.ports), 2, "Arbitrator failed to discover 2 brains")
        self.assertIn(8001, arbitrator.ports)
        self.assertIn(8005, arbitrator.ports)


if __name__ == "__main__":
    unittest.main()
