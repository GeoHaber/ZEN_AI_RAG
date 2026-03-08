import asyncio
from async_backend import backend


async def test():
    """Test."""
    print("Testing LLM...")
    async with backend:
        async for chunk in backend.send_message_async("Say only 'HELLO'"):
            # [X-Ray auto-fix] print(f"Chunk: {repr(chunk)}")
            pass


if __name__ == "__main__":
    asyncio.run(test())
