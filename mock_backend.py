# -*- coding: utf-8 -*-
"""
mock_backend.py - Mock backend for testing / offline mode.

Provides the same interface as AsyncZenAIBackend but returns canned
responses without needing a running LLM engine.
"""

import logging
from typing import AsyncGenerator, List

logger = logging.getLogger("MockBackend")


class MockAsyncBackend:
    """In-memory mock that mirrors AsyncZenAIBackend's interface."""

    def __init__(self):
        self.client = None
        self.api_url = "mock://localhost"
        logger.info("[MockBackend] Initialized (offline mode)")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        pass

    async def send_message_async(
        self, message: str, **kwargs
    ) -> AsyncGenerator[str, None]:
        """Return a canned streaming response."""
        response = f"[Mock] Received: {message[:80]}... (LLM engine not running)"
        for word in response.split():
            yield word + " "

    async def check_health(self) -> dict:
        return {"status": "mock", "message": "Mock backend — no LLM engine"}

    async def get_models(self) -> List[str]:
        return ["mock-model.gguf"]

    async def download_model(self, repo_id: str, filename: str) -> bool:
        logger.info(f"[MockBackend] download_model({repo_id}, {filename}) — no-op")
        return True

    async def set_active_model(self, model_name: str) -> bool:
        logger.info(f"[MockBackend] set_active_model({model_name}) — no-op")
        return True
