import requests
import sys

try:
    resp = requests.get("http://localhost:8080/", timeout=5)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200 and "ZenAI" in resp.text:
        print("SUCCESS: UI is reachable and contains ZenAI.")
        sys.exit(0)
    else:
        print("FAILURE: UI reachable but unexpected content or status.")
        print(resp.text[:200])
        sys.exit(1)
except Exception as e:
    print(f"FAILURE: Could not connect: {e}")
    sys.exit(1)
