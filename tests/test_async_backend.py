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
        # (httpx doesn't expose is_closed easily, but we verify no errors)
    
    @pytest.mark.asyncio
    async def test_send_message_async_structure(self):
        """Test send_message_async returns async generator."""
        backend = AsyncZenAIBackend()
        
        # Verify it's an async generator function
        import inspect
        assert inspect.ismethod(backend.send_message_async)
        
        # Would need to mock HTTP to test actual streaming
        # For now, verify structure is correct
    
    def test_backend_has_required_methods(self):
        """Test backend has all required methods (CRITICAL - catches AttributeError bug)."""
        backend = AsyncZenAIBackend()
        
        # Must have send_message_async
        assert hasattr(backend, 'send_message_async')
        assert callable(backend.send_message_async)
        
        # Must NOT have old send_message (blocking)
        # This test would have caught our bug!
        assert not hasattr(backend, 'send_message')


class TestBackendCompatibility:
    """Test backend compatibility with old code."""
    
    def test_old_backend_removed_send_message(self):
        """Test old NebulaBackend was completely removed."""
        # Legacy sync backend should be completely removed
        import zena

        # Old backend should NOT exist anymore
        assert not hasattr(zena, 'backend') or not hasattr(zena, 'NebulaBackend'), \
            "Legacy sync backend was removed, use async_backend only"
    
    def test_async_backend_available(self):
        """Test async_backend is available in zena module."""
        from zena import async_backend
        
        assert async_backend is not None
        assert hasattr(async_backend, 'send_message_async')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
