import requests
import time
import sys
import os
import unittest
from pathlib import Path

# --- Path Injection ---
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.append(str(root))

from zena_mode.arbitrage import SwarmArbitrator
from config_system import AppConfig

class TestArbitratorScaling(unittest.TestCase):
    def test_arbitrator_discovers_scaled_swarm(self):
        """Verify that arbitrator finds the correct number of experts after scaling."""
        # 0. Enable swarm in config
        from config_system import config
        config.SWARM_ENABLED = True
        config.SWARM_SIZE = 7 # Allow up to 7 for discovery tests
        
        # 1. Scale Hub to 2 experts (8005, 8006)
        hub_url = "http://127.0.0.1:8002/swarm/scale"
        try:
            print(f"Sending scale request to {hub_url}...")
            resp = requests.post(hub_url, json={"count": 2}, timeout=5.0)
            print(f"Hub response: {resp.status_code} - {resp.text}")
            self.assertEqual(resp.status_code, 200, "Hub rejected scale request")
        except Exception as e:
            self.fail(f"Failed to reach Hub: {e}")
        
        print("Waiting for experts to boot (20s)...")
        time.sleep(20) # Give them time to start
        
        # 2. Initialize arbitrator
        arbitrator = SwarmArbitrator()
        # discover_swarm() is called in __init__
        
        # We expect 2 brains total: 8001 (main) + 8005 (expert)
        print(f"Found ports: {arbitrator.ports}")
        
        self.assertGreaterEqual(len(arbitrator.ports), 2, "Arbitrator failed to discover 2 brains")
        self.assertIn(8001, arbitrator.ports)
        self.assertIn(8005, arbitrator.ports)

if __name__ == '__main__':
    unittest.main()
