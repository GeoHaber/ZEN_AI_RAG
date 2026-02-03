import httpx
import asyncio
import json

url = "http://127.0.0.1:8001/v1/chat/completions"

payloads = [
    {"content": "What is RAG?"},
    {"content": "How many experts can run in a swarm?"},
    {"content": "What is ZenAI?"}
]

system_prompt = "You are ZenAI."

async def run():
    async with httpx.AsyncClient(timeout=30.0) as client:
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
                async with client.stream('POST', url, json=data) as response:
                    print(f"Status: {response.status_code}")
                    if response.status_code != 200:
                        error_text = await response.aread()
                        print(f"Error Body: {error_text.decode()}")
                    else:
                        # Read one chunk
                        async for line in response.aiter_lines():
                            if line.strip():
                                print(f"First chunk: {line[:50]}...")
                                break
            except Exception as e:
                print(f"Exception: {e}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(run())
