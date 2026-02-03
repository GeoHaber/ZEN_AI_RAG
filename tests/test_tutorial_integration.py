import requests
import time
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://127.0.0.1:8080"

def test_tutorial_trigger():
    print("🚀 Starting Tutorial Integration Test...")
    
    # 1. Check if server is up
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✅ Server is UP (Status: {resp.status_code})")
    except Exception as e:
        print(f"❌ Server is DOWN: {e}")
        return False

    # 2. Get initial state
    print("Checking initial UI state...")
    state_resp = requests.get(f"{BASE_URL}/test/state")
    if state_resp.status_code == 200:
        state = state_resp.json()
        print(f"Initial Notifications: {state.get('notifications', [])}")
    
    # 3. Trigger the Tour Button via Test API
    print("Triggering 'Start Quick Tour' button...")
    click_resp = requests.post(f"{BASE_URL}/test/click/ui-btn-start-tour")
    if click_resp.status_code == 200:
        print("✅ Click command sent successfully.")
    else:
        print(f"❌ Failed to send click command: {click_resp.text}")
        return False

    # 4. Wait for JS execution and dialog appearance
    print("Waiting for tutorial dialog to appear (3s)...")
    time.sleep(3)
    
    # 5. Verify transition to Tutorial State
    # In a mock environment, index_internal_docs or start_tutorial should log or trigger something.
    # We check if a notification or dialog is active.
    state_resp = requests.get(f"{BASE_URL}/test/state")
    if state_resp.status_code == 200:
        state = state_resp.json()
        active_dialogs = state.get('active_dialogs', 0)
        print(f"Active Dialogs: {active_dialogs}")
        
        # In UITutorial, we open a dialog.
        if active_dialogs > 0:
            print("✅ Tutorial Dialog DETECTED!")
            return True
        else:
            print("❌ No Tutorial Dialog detected. Tour failed to start.")
            return False
    
    return False

if __name__ == "__main__":
    success = test_tutorial_trigger()
    if success:
        print("\n✨ INTEGRATION TEST PASSED! Tour is responding. 🤵")
        sys.exit(0)
    else:
        print("\n❌ INTEGRATION TEST FAILED! 🤵")
        sys.exit(1)
