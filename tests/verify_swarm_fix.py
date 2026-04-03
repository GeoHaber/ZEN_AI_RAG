import requests
import json
import time


def test_swarm_endpoint():
    """Test swarm endpoint."""
    print("Testing Swarm Endpoint to verify TaskType fix...")

    url = "http://127.0.0.1:8004/api/chat/swarm"
    payload = {"message": "Why is the sky blue? Explain simply."}

    try:
        time.time()
        print(f"Sending POST to {url}...")
        response = requests.post(url, json=payload, timeout=120)

        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Response received.")
            print(f"Response Preview: {str(data)[:200]}...")
            if "experts" in data and "response" in data:
                print("✅ Structure Valid: 'experts' and 'response' present.")
            else:
                print("⚠️ Warning: Unexpected response structure.")
        elif response.status_code == 500:
            data = response.json()
            print(f"❌ Failed: Server Error 500. Message: {data.get('error')}")
            if "TaskType" in str(data.get("error", "")):
                print("❌ 'TaskType' error still persistent!")
        else:
            print(f"❌ Failed: Unexpected status code {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"❌ Connection Error: {e}")


if __name__ == "__main__":
    test_swarm_endpoint()
