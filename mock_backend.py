# -*- coding: utf-8 -*-
"""
mock_backend.py - Mock Backend for UI Isolation
Provides a stubbed version of AsyncZenAIBackend for UI testing.
"""

import asyncio
import random
import time
from typing import AsyncGenerator, List, Dict, Any, Optional
from config_system import EMOJI

class MockAsyncBackend:
    """Mock implementation of ZenAI Backend."""
    
    def __init__(self, api_url: str = "http://127.0.0.1:8001/v1", hub_url: str = "http://127.0.0.1:8002"):
        self.api_url = api_url
        self.hub_url = hub_url
        self.client = True # Dummy truthy value
        
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def get_models(self) -> List[str]:
        """Return a list of mock models."""
        await asyncio.sleep(0.5)
        return [
            "qwen2.5-coder-7b-instruct-q4_k_m.gguf (MOCK)",
            "llama-3.2-3b-instruct-q8_0.gguf (MOCK)",
            "phi-3-mini-4k-instruct.gguf (MOCK)"
        ]

    async def get_active_model(self) -> str:
        """Return the active mock model."""
        return "qwen2.5-coder-7b-instruct-q4_k_m.gguf (MOCK)"

    async def set_active_model(self, model_name: str) -> bool:
        """Simulate setting the active model."""
        await asyncio.sleep(1)
        return True

    async def check_health(self) -> Dict[str, Any]:
        """Return mock health status."""
        return {
            "status": "online",
            "model": "qwen2.5-coder-7b-instruct-q4_k_m.gguf (MOCK)",
            "port": 8001
        }

    async def send_message_async(
        self, 
        text: str, 
        system_prompt: str = "You are ZenAI.", 
        attachment_content: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Simulate a streaming AI response."""
        yield f"{EMOJI['ai']} **[MOCK MODE]** Processing your request...\n\n"
        
        responses = [
            "This is a simulated response from the ZenAI Mock Backend. The UI seems to be communicating correctly!",
            "I am currently running in isolation mode. No real LLM is being queried.",
            "Testing the RAG transparency layout... (Source: Mock Database)",
            "The quick brown fox jumps over the lazy developer."
        ]
        
        chosen_response = random.choice(responses)
        
        # Stream word by word
        for word in chosen_response.split():
            await asyncio.sleep(0.05)
            yield word + " "
            
        yield "\n\n---"
        yield f"\n*Generated in Mock Mode (TTFT: 100ms, TPS: 20.0)*"

    async def search_models(self, query: str) -> List[Dict]:
        """Mock model search."""
        return [{"name": f"Mock Model for '{query}'", "repo": "mock/repo", "downloads": "1M"}]

    async def get_popular_models(self) -> List[Dict]:
        """Mock popular models."""
        return [{"name": "Popular Mock Model", "repo": "mock/popular", "downloads": "5M"}]
