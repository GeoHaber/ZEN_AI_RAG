
import requests
import json

url = "http://127.0.0.1:8001/v1/chat/completions"
headers = {"Content-Type": "application/json"}

payloads = [
    {"content": "What is ZenAI?", "id": "fail_1"},
    {"content": "How many experts can run in a swarm?", "id": "success_1"},
    {"content": "What is RAG?", "id": "fail_2"}
]

system_prompt = """You are ZenAI, a helpful AI assistant powered by Qwen2.5-Coder.
You are NOT ChatGPT, NOT GPT-4, and NOT made by OpenAI.
You were created by Alibaba Cloud (Qwen team) and integrated into the ZenAI application.
Be helpful, concise, and accurate. If asked about your identity, say you are ZenAI powered by Qwen."""

for p in payloads:
    data = {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": p["content"]}
        ],
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    print(f"Testing: {p['content']}...")
    try:
        response = requests.post(url, json=data, stream=True)
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error Body: {response.text}")
        else:
            # Read first chunk to ensure stream works
            for line in response.iter_lines():
                if line:
                    print(f"First chunk: {line}")
                    break
    except Exception as e:
        print(f"Exception: {e}")
    print("-" * 20)
