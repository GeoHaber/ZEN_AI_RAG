
import logging
import asyncio
import sys
import os

# Fix import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import httpx
from async_backend import AsyncZenAIBackend
from zena_mode.rag_pipeline import LocalRAG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Reproduction")


STRESS_TESTS = [
    # ("Normal Query", "What is ZenAI?"),
    # ("Large Context (2k tokens)", "Ignore previous." + " word" * 2000), 
    # ("Special Chars", "Hello \x00 World \uffff \U0001F600"), 
    ("Foreign Languages", "你好世界 (Hello World) | C'est la vie (That's life) | 🌮"), # UTF-8 Safety Check
]

async def reproduce():
    """Reproduce."""
    logger.info("🧪 Starting Stress Test...")
    backend = AsyncZenAIBackend()
    
    # Retry logic for health check... (omitted for brevity, assume present or safe to skip if we trust backend is up from prev run)
    
    async with backend:
        # 1. Stress Tests
        for name, prompt in STRESS_TESTS:
            logger.info(f"\n⚡ Testing: {name}")
            char_count = len(prompt)
            logger.info(f"📏 Size: {char_count} chars")
            
            try:
                # Manually construct payload to match async_backend's logic roughly, or use send_message_async
                # send_message_async constructs the full JSON.
                
                response_text = ""
                got_400 = False
                async for chunk in backend.send_message_async(prompt):
                    if "Server returned 400" in chunk:
                        logger.error(f"❌ CAUGHT 400 ERROR on {name}: {chunk}")
                        got_400 = True
                    else:
                        response_text += chunk
                
                if got_400:
                    logger.info("⚠️ Verified 400 Error Triggered!")
                elif response_text:
                    logger.info("✅ Success")
                else:
                    logger.warning("❓ No response, no error?")

            except Exception as e:
                logger.error(f"❌ Exception: {e}")


if __name__ == "__main__":
    asyncio.run(reproduce())
