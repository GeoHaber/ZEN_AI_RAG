# conftest.py - pytest configuration for ZenAI tests
import sys
import pytest
import respx
import httpx
from pathlib import Path

# Add project root to Python path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

@pytest.fixture
def mock_llm_api():
    """Fixture to mock LLM API responses (8001)."""
    with respx.mock(base_url="http://127.0.0.1:8001", assert_all_called=False) as respx_mock:
        # Health check
        respx_mock.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        
        # Chat completion stream
        stream_content = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n',
            'data: {"choices": [{"delta": {"content": " world!"}}]}\n\n',
            'data: [DONE]\n\n'
        ]
        respx_mock.post("/v1/chat/completions").mock(return_value=httpx.Response(200, content="".join(stream_content)))
        
        yield respx_mock

@pytest.fixture
def mock_hub_api():
    """Fixture to mock Hub API responses (8002)."""
    with respx.mock(base_url="http://127.0.0.1:8002", assert_all_called=False) as respx_mock:
        respx_mock.get("/models/available").mock(return_value=httpx.Response(200, json=["mock-model-1.gguf", "mock-model-2.gguf"]))
        respx_mock.post("/models/load").mock(return_value=httpx.Response(200, json={"status": "loaded"}))
        respx_mock.post("/models/download").mock(return_value=httpx.Response(200, json={"status": "started"}))
        
        yield respx_mock
