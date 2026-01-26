import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from model_router import ModelRouter, TaskType

@pytest.mark.asyncio
async def test_butler_reranking_logic():
    """Verify that Butler can score and filter chunks."""
    router = ModelRouter()
    
    # Mock retrieval results (chunks)
    chunks = [
        {"url": "doc1", "text": "This is very relevant to unicorns.", "title": "Unicorns"},
        {"url": "doc2", "text": "This is about spaceships, totally irrelevant.", "title": "Spaceships"},
        {"url": "doc3", "text": "Unicorns have horns and like rainbows.", "title": "Unicorn Facts"}
    ]
    
    # Mock the Butler LLM response for reranking
    # We expect the Butler to return something like "score: 0.9" or "YES"
    # For simplicity, we'll mock the classifier's internal call or a new rerank method
    
    # Let's assume a semi-structured response from the Butler for each chunk
    mock_responses = [
        '{"relevance": 0.9, "reason": "Mentions unicorns"}',
        '{"relevance": 0.1, "reason": "No mention of unicorns"}',
        '{"relevance": 0.95, "reason": "Specific unicorn facts"}'
    ]
    
    async def mock_post(*args, **kwargs):
        idx = SideEffect.count
        SideEffect.count += 1
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"choices": [{"message": {"content": mock_responses[idx]}}]}
        return resp

    class SideEffect:
        count = 0

    mock_client_instance = MagicMock()
    mock_client_instance.post = AsyncMock(side_effect=mock_post)
    
    # We need to mock the context manager properly
    mock_client_cm = MagicMock()
    mock_client_cm.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_cm.__aexit__ = AsyncMock()
    
    with patch('httpx.AsyncClient', return_value=mock_client_cm):
        # The method we will implement
        reranked = await router.rerank_chunks("Tell me about unicorns", chunks, top_n=2)
        
        assert len(reranked) == 2
        assert reranked[0]['url'] == "doc3" # Highest score (0.95)
        assert reranked[1]['url'] == "doc1" # Second highest (0.9)
        assert any(c['url'] == "doc2" for c in reranked) is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
