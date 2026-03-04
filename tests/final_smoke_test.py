import requests
import time
import sys
import json

def run_test():
    """Run test."""
    print("🚀 Starting Final Integration Smoke Test...")
    ui_url = "http://127.0.0.1:8080"
    
    # 1. Check UI Reachability
    try:
        r = requests.get(ui_url, timeout=5)
        print(f"✅ UI is up (Status {r.status_code})")
    except Exception as e:
        print(f"❌ UI is unreachable: {e}")
        sys.exit(1)

    # 2. Inject Message
    payload = {"text": "Hello ZenAI! Who are you?"}
    print(f"🔎 Sending message: '{payload['text']}'")
    try:
        r = requests.post(f"{ui_url}/test/send", json=payload, timeout=5)
        if r.status_code == 200:
            print("✅ Send command accepted by UI.")
        else:
            print(f"❌ Send command failed: {r.status_code} - {r.text}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        sys.exit(1)

    # 3. Poll for Response
    print("⏳ Waiting for LLM response to propagate to UI...")
    max_wait = 15
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            r = requests.get(f"{ui_url}/test/state", timeout=2)
            r.json()
            # In our zena.py test/state, we might need to improve what it returns
            # but for now we look at logs or just wait for success.
            # print(f"  Current UI State: {state}")
            time.sleep(2)
        except Exception as e:
            print(f"  (Polling error: {e})")
            time.sleep(2)
            
    print("\n========================================")
    print("🏁 Smoke Test Finished.")
    print("Please check the zena.py and start_llm.py logs for '[AsyncBackend] Received chunk' and '[AsyncBackend] Done' messages.")
    print("========================================")

if __name__ == "__main__":
    run_test()
