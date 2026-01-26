import requests
import json

BASE_URL = "http://localhost:8081"

def main():
    print("🧠 Testing Long-Term Recall...")
    try:
        # Ask without context
        payload = {"message": "Do you remember my name?"}
        res = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=30)
        
        if res.status_code == 200:
            text = res.json().get("response", "")
            print(f"RESPONSE: {text}")
            if "ZenDeveloper" in text or "Zendeveloper" in text:
                print("✅ PASSED: Name recalled from disk!")
            else:
                print("❌ FAILED: Name not found.")
        else:
            print(f"❌ Error: {res.status_code}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    main()
