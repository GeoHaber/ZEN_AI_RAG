import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from async_backend import AsyncZenAIBackend

@pytest.mark.asyncio
async def test_swarm_scaling_logic():
    """Verify that scale_swarm sends the correct POST request to the Hub."""
    backend = AsyncZenAIBackend()
    
    # Mock the internal client
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        
        # Test scale up
        success = await backend.scale_swarm(3)
        assert success is True
        
        # Verify the call to Hub API (port 8002)
        call_args = mock_post.call_args
        assert "8002/swarm/scale" in str(call_args)
        assert call_args.kwargs['json'] == {"count": 3}
        
        # Test scale down
        await backend.scale_swarm(0)
        assert mock_post.call_args.kwargs['json'] == {"count": 0}

@pytest.mark.asyncio
async def test_router_initialization_on_toggle():
    """Verify that toggling Smart Routing initializes the ModelRouter."""
    # We'll test the glue logic in the UI layer (mocked)
    from ui_components import _on_smart_routing_change # We'll need to define this
    
    mock_router = MagicMock()
    mock_router.initialize = AsyncMock(return_value=True)
    
    # Simulate UI toggle
    await _on_smart_routing_change(True, mock_router)
    
    mock_router.initialize.assert_called_once()
