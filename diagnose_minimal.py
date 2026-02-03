import requests
import json

url = "http://127.0.0.1:8001/v1/chat/completions"

def test(content):
    payload = {
        "model": "local-model",
        "messages": [{"role": "user", "content": content}],
        "stream": False
    }
    print(f"Testing: {content}")
    r = requests.post(url, json=payload)
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text}")
    print("-" * 20)

test("Hello")
test("What is RAG?")
test("What is ZenAI?")
