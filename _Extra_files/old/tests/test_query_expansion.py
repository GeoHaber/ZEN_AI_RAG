import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from model_router import ModelRouter

@pytest.mark.asyncio
async def test_butler_query_expansion():
    """Verify that Butler can generate semantic variations of a query."""
    router = ModelRouter()
    
    # Mock the Butler LLM response for expansion
    # We expect a JSON list of variations
    mock_response = '["how to implement unicorns", "unicorn implementation tutorial", "best practices for unicorns"]'
    
    mock_client_instance = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"choices": [{"message": {"content": mock_response}}]}
    mock_client_instance.post = AsyncMock(return_value=resp)
    
    mock_client_cm = MagicMock()
    mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_cm.__aexit__ = AsyncMock()
    
    with patch('httpx.AsyncClient', return_value=mock_client_cm):
        variations = await router.expand_query("unicorn tutorial")
        
        # Original query should be included + variations
        assert len(variations) >= 3
        assert "unicorn tutorial" in variations
        assert "how to implement unicorns" in variations
        assert "best practices for unicorns" in variations

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
