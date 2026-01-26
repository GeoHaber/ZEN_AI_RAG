import requests
import time
import sys

BASE_URL = "http://localhost:8081"

def test_chat(message):
    print(f"\n[User]: {message}")
    try:
        start = time.time()
        res = requests.post(f"{BASE_URL}/api/chat", json={"message": message}, timeout=30)
        latency = time.time() - start
        
        if res.status_code == 200:
            data = res.json()
            response = data.get("response", "")
            emotion = data.get("emotion", "Neutral")
            print(f"[Quen ({emotion})]: {response} ({latency:.2f}s)")
            return response
        else:
            print(f"❌ Error: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def main():
    print("🧠 Starting Memory Test on Port 8081...")
    
    # Turn 1: Establish Context
    print("--- Turn 1: Setting Name ---")
    test_chat("Hi! My name is ZenDeveloper.")
    
    # Turn 2: Verify Context
    print("--- Turn 2: Checking Memory ---")
    response = test_chat("Do you remember my name?")
    
    # Verification Logic
    if response and "ZenDeveloper" in response:
        print("\n✅ PASSED: Memory is working!")
    else:
        print("\n❌ FAILED: Name not found in response.")
        
    # Turn 3: Follow up
    print("--- Turn 3: Follow Up ---")
    test_chat("What can you help me with?")

if __name__ == "__main__":
    main()
