import requests
import json
import sys

url = "http://127.0.0.1:8001/v1/chat/completions"
payload = {
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": True,
    "max_tokens": 50
}

print(f"Checking LLM at {url}...")
try:
    with requests.post(url, json=payload, stream=True) as r:
        print(f"Status Code: {r.status_code}")
        if r.status_code != 200:
            print(f"Error: {r.text}")
            sys.exit(1)
            
        chunk_count = 0
        for line in r.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                print(f"Chunk: {decoded}")
                if decoded.startswith("data: ") and decoded != "data: [DONE]":
                    chunk_count += 1
        
        print(f"\nTotal Chunks: {chunk_count}")
        if chunk_count == 0:
            print("FAILURE: Connection open but 0 chunks received.")
            sys.exit(1)
        else:
            print("SUCCESS: LLM is streaming.")

except Exception as e:
    print(f"EXCEPTION: {e}")
    sys.exit(1)
