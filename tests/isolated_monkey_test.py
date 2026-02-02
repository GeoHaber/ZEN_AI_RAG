# -*- coding: utf-8 -*-
"""
tests/isolated_monkey_test.py - Headless UI Monkey Test
Hits the test endpoints of zena.py to simulate user interactions.
"""

import requests
import time
import sys
import os

# Add parent dir to path to import registry
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui.registry import MONKEY_TARGETS

BASE_URL = "http://127.0.0.1:8080"

def run_monkey_test():
    print(f"🚀 Starting Isolated Monkey Test on {BASE_URL}")
    
    passed = 0
    failed = 0
    
    # Pre-test: Check if UI is up
    try:
        requests.get(BASE_URL, timeout=5)
        print("✅ UI Server is reachable.")
    except Exception as e:
        print(f"❌ UI Server is NOT reachable: {e}")
        return

    for element_id in MONKEY_TARGETS:
        print(f"🔎 Poking {element_id}...", end=" ", flush=True)
        try:
            # Simulate a click via the test endpoint
            resp = requests.post(f"{BASE_URL}/test/click/{element_id}", timeout=5)
            if resp.status_code == 200:
                print("OK")
                passed += 1
            else:
                print(f"FAIL (Status {resp.status_code})")
                failed += 1
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1
        
        # Give NiceGUI a moment to handle the "click"
        time.sleep(0.5)

    print("\n" + "="*40)
    print(f"🐒 Monkey Test Finished: {passed} PASSED, {failed} FAILED")
    print("="*40)
    
    if failed > 0:
        print("⚠️ Warning: Some UI elements caused errors. Check zena.py console/logs.")
        sys.exit(1)
    else:
        print("✨ All UI elements responded correctly!")
        sys.exit(0)

if __name__ == "__main__":
    run_monkey_test()
