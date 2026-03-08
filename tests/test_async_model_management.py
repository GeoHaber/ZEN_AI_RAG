# -*- coding: utf-8 -*-
import pytest
from async_backend import AsyncZenAIBackend


@pytest.mark.asyncio
async def test_set_active_model_mocked(mock_hub_api):
    """Verify we can switch models via Hub API (Mocked)."""
    backend = AsyncZenAIBackend()

    # Success case
    success = await backend.set_active_model("new-model.gguf")
    assert success is True
    assert len(mock_hub_api.calls) == 1
    assert mock_hub_api.calls.last.request.url.path == "/models/load"
    assert "new-model.gguf" in mock_hub_api.calls.last.request.content.decode()


@pytest.mark.asyncio
async def test_set_active_model_failure(mock_hub_api):
    """Verify failure handling when model loading fails."""
    import httpx

    # Override mock for this specific call to return 500
    mock_hub_api.post("/models/load").mock(return_value=httpx.Response(500))

    backend = AsyncZenAIBackend()
    success = await backend.set_active_model("broken-model.gguf")

    assert success is False


@pytest.mark.asyncio
async def test_download_model_mocked(mock_hub_api):
    """Verify we can trigger model download (Mocked)."""
    backend = AsyncZenAIBackend()

    success = await backend.download_model("repo/id", "model.gguf")
    assert success is True
    assert mock_hub_api.calls.last.request.url.path == "/models/download"
