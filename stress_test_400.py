import httpx
import asyncio
import json
import time

url = "http://127.0.0.1:8001/v1/chat/completions"

data = {
    "model": "local-model",
    "messages": [
        {"role": "user", "content": "Hello"}
    ],
    "stream": True
}

async def run():
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(10):
            print(f"Request {i+1}...")
            try:
                async with client.stream('POST', url, json=data) as response:
                    print(f"Status: {response.status_code}")
                    if response.status_code == 200:
                        count = 0
                        async for line in response.aiter_lines():
                            count += 1
                        print(f"Chunks received: {count}")
                    else:
                        print(f"Error: {await response.aread()}")
            except Exception as e:
                print(f"Exception: {e}")
            time.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(run())
