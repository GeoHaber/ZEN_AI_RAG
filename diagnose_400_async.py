
import httpx
import asyncio
import json

url = "http://127.0.0.1:8001/v1/chat/completions"

payloads = [
    {"content": "What is ZenAI?", "id": "fail_1"},
    {"content": "How many experts can run in a swarm?", "id": "success_1"},
    {"content": "What is RAG?", "id": "fail_2"}
]

system_prompt = """You are ZenAI, a helpful AI assistant powered by Qwen2.5-Coder.
You are NOT ChatGPT, NOT GPT-4, and NOT made by OpenAI.
You were created by Alibaba Cloud (Qwen team) and integrated into the ZenAI application.
Be helpful, concise, and accurate. If asked about your identity, say you are ZenAI powered by Qwen."""

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
                # Replicating async_backend.py logic exactly
                async with client.stream('POST', url, json=data) as response:
                    print(f"Status: {response.status_code}")
                    if response.status_code != 200:
                        error_text = await response.aread()
                        print(f"Error Body: {error_text.decode()}")
                    else:
                        async for line in response.aiter_lines():
                            if line.strip():
                                print(f"First chunk: {line[:50]}...")
                                break
            except Exception as e:
                print(f"Exception: {e}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(run())
