import asyncio
from async_backend import backend

async def test():
    print("Testing LLM...")
    async with backend:
        async for chunk in backend.send_message_async("Say only 'HELLO'"):
            print(f"Chunk: {repr(chunk)}")

if __name__ == "__main__":
    asyncio.run(test())
