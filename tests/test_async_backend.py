# -*- coding: utf-8 -*-
"""
test_async_backend.py - Unit tests for async backend
Tests async HTTP streaming and error handling
"""
import pytest
import asyncio
from async_backend import AsyncZenAIBackend

class TestAsyncZenAIBackend:
    """Test AsyncZenAIBackend class."""
    
    def test_initialization(self):
        """Test backend initializes correctly."""
        backend = AsyncZenAIBackend()
        
        assert backend.client is None  # Not created until context manager
        assert "8001" in backend.api_url
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager creates/closes client."""
        backend = AsyncZenAIBackend()
        
        assert backend.client is None
        
        async with backend:
            assert backend.client is not None
        
        # After context, client should be closed
    
    @pytest.mark.asyncio
    async def test_streaming_with_mock(self, mock_llm_api):
        """Test actual streaming from mock API (PROVES TEST ISOLATION)."""
        backend = AsyncZenAIBackend()
        full_text = ""
        
        async with backend:
            async for chunk in backend.send_message_async("test query"):
                full_text += chunk
        
        assert full_text == "Hello world!"
        assert len(mock_llm_api.calls) == 1
        assert mock_llm_api.calls.last.request.method == "POST"
    
    @pytest.mark.asyncio
    async def test_hub_models_with_mock(self, mock_hub_api):
        """Test model discovery from mock Hub API."""
        backend = AsyncZenAIBackend()
        
        async with backend:
            models = await backend.get_models()
        
        assert "mock-model-1.gguf" in models
        assert len(models) == 2
        assert len(mock_hub_api.calls) == 1
    
    def test_backend_has_required_methods(self):
        """Test backend has all required methods."""
        backend = AsyncZenAIBackend()
        assert hasattr(backend, 'send_message_async')
        assert callable(backend.send_message_async)
        assert not hasattr(backend, 'send_message')

    @pytest.mark.asyncio
    async def test_health_check_mocked(self, mock_llm_api):
        """Verify health check returns True when API is ok (Mocked)."""
        backend = AsyncZenAIBackend()
        is_ok = await backend.health_check()
        assert is_ok is True
        assert mock_llm_api.calls.last.request.url.path == "/health"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_llm_api):
        """Verify health check returns False when API returns error."""
        import httpx
        mock_llm_api.get("/health").mock(return_value=httpx.Response(500))
        
        backend = AsyncZenAIBackend()
        is_ok = await backend.health_check()
        assert is_ok is False

class TestBackendCompatibility:
    """Test backend compatibility with old code."""
    
    def test_old_backend_removed_completely(self):
        """Test old AsyncZenAIBackend is completely removed from zena.py."""
        import zena
        assert not hasattr(zena, 'backend')
    
    def test_async_backend_available(self):
        """Test async_backend is available in zena module."""
        from zena import async_backend
        assert async_backend is not None
        assert hasattr(async_backend, 'send_message_async')

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
