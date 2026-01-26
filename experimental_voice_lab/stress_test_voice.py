
import asyncio
import aiohttp
import time
import random
from datetime import datetime

BASE_URL = "http://localhost:8081"
NUM_REQUESTS = 20
CONCURRENT_LIMIT = 5

async def test_tts(session, i):
    text = f"Stress Testing Request Number {i}."
    voice = "en-US-AriaNeural"
    start = time.time()
    try:
        async with session.post(f"{BASE_URL}/api/tts", json={"text": text, "voice_id": voice}) as resp:
            data = await resp.json()
            latency = time.time() - start
            if data.get("status") == "ok":
                print(f"✅ TTS #{i} Success ({latency:.2f}s)")
                return True
            else:
                print(f"❌ TTS #{i} Failed: {data}")
                return False
    except Exception as e:
        print(f"❌ TTS #{i} Error: {e}")
        return False

async def test_chat(session, i):
    msg = "Hello Quen, are you working?"
    start = time.time()
    try:
        async with session.post(f"{BASE_URL}/api/chat", json={"message": msg}) as resp:
            data = await resp.json()
            latency = time.time() - start
            if resp.status == 200:
                print(f"🧠 Chat #{i} Success ({latency:.2f}s)")
                return True
            else:
                print(f"❌ Chat #{i} Failed: {resp.status}")
                return False
    except Exception as e:
        print(f"❌ Chat #{i} Error: {e}")
        return False

async def main():
    print(f"🚀 Starting Stress Test on {BASE_URL}")
    print(f"Target: {NUM_REQUESTS} TTS requests with limit {CONCURRENT_LIMIT}")
    
    # Check Health
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/api/test-llm") as resp:
                print(f"Health Check: {resp.status}")
                if resp.status != 200:
                    print("❌ Server not healthy. Aborting.")
                    return
        except:
             print("❌ Server unreachable. Make sure run_voice_lab.py is running!")
             return

        # Run TTS Storm
        tasks = []
        start_time = time.time()
        semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)

        async def bounded_tts(i):
            async with semaphore:
                # Alternate between TTS and Chat
                if i % 2 == 0:
                    return await test_tts(session, i)
                else:
                    return await test_chat(session, i)

        for i in range(NUM_REQUESTS):
            tasks.append(bounded_tts(i))
        
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        success_count = sum(results)
        print("\n📊 STRESS TEST RESULTS")
        print(f"Total Requests: {NUM_REQUESTS}")
        print(f"Successful: {success_count}")
        print(f"Failed: {NUM_REQUESTS - success_count}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Avg Latency: {total_time/NUM_REQUESTS:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
