# -*- coding: utf-8 -*-
import pytest
import asyncio
from async_backend import AsyncZenAIBackend


@pytest.mark.asyncio
async def test_fetch_models_mocked(mock_hub_api):
    """Verify we can fetch models from Port 8002 (Mocked)."""
    backend = AsyncZenAIBackend()
    models = await backend.get_models()

    assert isinstance(models, list)
    assert "mock-model-1.gguf" in models
    assert len(mock_hub_api.calls) == 1


@pytest.mark.asyncio
async def test_chat_completion_mocked(mock_llm_api):
    """Verify we can get a streaming response from Port 8001 (Mocked)."""
    backend = AsyncZenAIBackend()
    response_text = ""

    async with backend:
        async for chunk in backend.send_message_async("Say hello in English."):
            response_text += chunk

    assert response_text == "Hello world!"
    assert len(mock_llm_api.calls) == 1
    assert mock_llm_api.calls.last.request.method == "POST"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
