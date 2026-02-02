import asyncio
import logging
from async_backend import AsyncZenAIBackend

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_backend():
    print("Initializing Backend...")
    backend = AsyncZenAIBackend()
    
    print("Starting Stream...")
    async with backend:
        chunk_count = 0
        async for chunk in backend.send_message_async("Hello"):
            print(f"Chunk: {chunk}")
            chunk_count += 1
            
        print(f"Total Chunks: {chunk_count}")
        if chunk_count == 0:
            print("FAILURE: Class returned 0 chunks.")
        else:
            print("SUCCESS: Class is streaming.")

if __name__ == "__main__":
    try:
        asyncio.run(test_backend())
    except Exception as e:
        print(f"CRASH: {e}")
