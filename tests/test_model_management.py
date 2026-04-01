"""
test_model_management.py
TDD Test: Verify model selection and download API integration.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from async_backend import AsyncZenAIBackend


class TestModelManagement:
    """TestModelManagement class."""

    @pytest.mark.asyncio
    async def test_get_models_from_hub_api(self):
        """Test that AsyncZenAIBackend.get_models() fetches from Hub API (port 8002)."""
        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock successful API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = ["qwen2.5-coder-7b.gguf", "llama-3.2-3b.gguf"]
            mock_get.return_value = mock_response

            backend = AsyncZenAIBackend()
            models = await backend.get_models()

            # Verify API was called
            mock_get.assert_called()
            call_url = mock_get.call_args[0][0]
            assert "8002" in call_url
            assert "/models/available" in call_url

            # Verify models returned
            assert isinstance(models, list)
            assert len(models) == 2
            print(f"✓ get_models() returned: {models}")

    @pytest.mark.asyncio
    async def test_get_models_fallback_on_error(self):
        """Test that get_models() returns fallback list if Hub API fails."""
        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock API failure
            mock_get.side_effect = Exception("Connection refused")

            backend = AsyncZenAIBackend()
            models = await backend.get_models()

            # Should return fallback list
            assert isinstance(models, list)
            assert len(models) > 0
            print(f"✓ Fallback models: {models}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
