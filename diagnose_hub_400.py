import requests
import json

url = "http://127.0.0.1:8002/api/chat"
headers = {"Content-Type": "application/json"}

payloads = [
    {"message": "What is ZenAI?"},
    {"message": "How many experts can run in a swarm?"},
    {"message": "What is RAG?"}
]

for p in payloads:
    print(f"Testing Hub API: {p['message']}...")
    try:
        response = requests.post(url, json=p, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    print("-" * 20)
