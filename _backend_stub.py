# -*- coding: utf-8 -*-
"""
_backend_stub.py - Minimal backend fallback when async_backend / mock_backend
are unavailable.  Allows the UI to render and display helpful error messages
rather than crashing on import.
"""

import logging

logger = logging.getLogger(__name__)


class StubBackend:
    """No-op backend that returns safe defaults for every UI call."""

    async def check_health(self):
        return {"status": "stub", "message": "No backend connected"}

    async def send_message(self, message: str, **kwargs):
        return {
            "response": "[Backend unavailable] Please start the LLM engine first.",
            "tokens": 0,
        }

    async def get_models(self):
        return []

    async def get_status(self):
        return {"engine": "stub", "status": "offline"}

    def __repr__(self):
        return "<StubBackend>"
