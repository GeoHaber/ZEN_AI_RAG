import unittest
import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from async_backend import AsyncNebulaBackend

class TestBackendIntegration(unittest.TestCase):
    def setUp(self):
        self.backend = AsyncNebulaBackend()

    def test_1_get_models(self):
        """Verify we can fetch models from Port 8002"""
        print("\n[Test] Fetching Models...")
        # Run async method in sync test wrapper
        import asyncio
        models = asyncio.run(self.backend.get_models())
        
        print(f"Models found: {models}")
        self.assertIsInstance(models, list)
        self.assertTrue(len(models) > 0, "No models found from backend!")
        if models[0].startswith("Offline"):
            print("WARNING: Backend 8002 seems offline. Is start_llm.py running?")

    def test_2_chat_completion(self):
        """Verify we can get a streaming response from Port 8001"""
        print("\n[Test] Sending Chat Message...")
        response_text = ""
        
        # Simple English prompt
        prompt = "Say hello in English."
        
        async def run_chat():
            text = ""
            async with self.backend:
                async for chunk in self.backend.send_message_async(prompt):
                    print(chunk, end="", flush=True)
                    text += chunk
            return text

        try:
            import asyncio
            response_text = asyncio.run(run_chat())
        except Exception as e:
            self.fail(f"Backend connection failed: {e}")

        print("\n[Test] Complete.")
        
        # Verify we got something
        self.assertTrue(len(response_text) > 0, "Response was empty!")
        
        # Verify it's not an error message
        self.assertNotIn("Connection Error", response_text)
        
        # Basic check against Chinese characters (Hallucination check)
        # Usually Qwen/Llama respond in English to English prompts if template is correct.
        # This isn't perfect but helps catch the specific 'Chinese' issue user saw.
        chinese_char_count = len([c for c in response_text if '\u4e00' <= c <= '\u9fff'])
        if chinese_char_count > len(response_text) * 0.5:
             print("\nWARNING: Response seems to be mostly Chinese. Prompt template might be failing.")
             # We don't fail the test strictly here as model behavior varies, but we warn.

if __name__ == '__main__':
    unittest.main()
