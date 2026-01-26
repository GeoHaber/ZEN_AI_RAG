import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from model_router import ModelRouter, TaskType

@pytest.mark.asyncio
async def test_butler_master_coordination():
    """Verify that the Butler/Master coordination flow works sequentially."""
    router = ModelRouter()
    
    # Mock the classifier to return a specific take and task
    router.classifier.classify_and_take = AsyncMock(return_value=(TaskType.CODE_GENERATION, "I will write that code for you!"))
    
    # Mock the model registry
    mock_model = MagicMock()
    mock_model.name = "Test-Master-Model"
    mock_model.path = "test/path.gguf"
    router.registry.get_best_for_task = MagicMock(return_value=mock_model)
    
    # Mock the worker execution (Master)
    # We need to mock the httpx client used in stream_butler_master
    chunks = [
        'data: {"choices": [{"delta": {"content": "Here "}}]}',
        'data: {"choices": [{"delta": {"content": "is "}}]}',
        'data: {"choices": [{"delta": {"content": "the code."}}]}',
        'data: [DONE]'
    ]
    
    async def mock_aiter_lines():
        for chunk in chunks:
            yield chunk
            
    # Mock the response object
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines
    
    # Mock the context manager returned by client.stream
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_response
    
    mock_client = MagicMock()
    mock_client.stream.return_value = mock_cm
    
    # Mock _ensure_worker_model to avoid subprocess calls
    router._ensure_worker_model = AsyncMock(return_value=True)
    
    # Mock the AsyncClient to be an async context manager
    mock_client_cm = AsyncMock()
    mock_client_cm.__aenter__.return_value = mock_client
    
    with patch('httpx.AsyncClient', return_value=mock_client_cm):
        full_response = ""
        async for chunk in router.stream_butler_master("Write a hello world"):
            full_response += chunk
        
        # Verify Butler was called and outputted
        assert "Butler" in full_response
        assert "I will write that code for you!" in full_response
        
        # Verify Master was called and outputted
        assert "Master" in full_response or "Test-Master-Model" in full_response
        assert "Here is the code." in full_response
        
        # Verify logic sequence
        assert full_response.index("Butler") < full_response.index("the code")

@pytest.mark.asyncio
async def test_butler_error_fallback():
    """Verify that Butler issues don't crash the whole flow."""
    router = ModelRouter()
    
    # Mock httpx.AsyncClient.post to raise an error
    with patch('httpx.AsyncClient.post', side_effect=Exception("Butler down")):
        task_type, take = await router.classifier.classify_and_take("test")
        assert task_type == TaskType.GENERAL_CHAT
        assert "immediately" in take

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
