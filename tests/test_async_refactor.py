import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from async_backend import AsyncZenAIBackend


class TestAsyncRefactor:
    """TestAsyncRefactor class."""

    @pytest.mark.asyncio
    async def test_get_models_success(self):
        """Test get models success."""
        backend = AsyncZenAIBackend()

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["model_a", "model_b"]

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            models = await backend.get_models()

        assert models == ["model_a", "model_b"]
        mock_client.get.assert_called_with("http://127.0.0.1:8002/models/available", timeout=2.0)

    @pytest.mark.asyncio
    async def test_get_models_failure_fallback(self):
        """Test get models failure fallback."""
        backend = AsyncZenAIBackend()

        # Mock httpx failure
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = Exception("Connection Refused")

        with patch("httpx.AsyncClient", return_value=mock_client):
            models = await backend.get_models()

        # Should return fallback
        assert any("qwen2.5-coder" in m for m in models)

    @pytest.mark.asyncio
    async def test_download_model(self):
        """Test download model."""
        backend = AsyncZenAIBackend()

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            success = await backend.download_model("repo", "file")

        assert success is True
        mock_client.post.assert_called_with(
            "http://127.0.0.1:8002/models/download", json={"repo_id": "repo", "filename": "file"}, timeout=5.0
        )

    @pytest.mark.asyncio
    async def test_set_active_model(self):
        """Test set active model."""
        backend = AsyncZenAIBackend()

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            success = await backend.set_active_model("new_model")

        assert success is True
