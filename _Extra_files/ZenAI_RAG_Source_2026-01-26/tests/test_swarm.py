import pytest
import asyncio
import json
import httpx
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from zena_mode.arbitrage import SwarmArbitrator, ConsensusMethod

class TestSwarmArbitrator:
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_discover_swarm_enabled(self, mock_client_class):
        """Test discover_swarm detects live endpoints correctly."""
        # Mock client and its GET method
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        async def mock_get(url, timeout=None):
            mock_resp = Mock()
            if "8001/health" in url or "8006/health" in url:
                mock_resp.status_code = 200
            else:
                mock_resp.status_code = 404
            return mock_resp
            
        mock_client.get.side_effect = mock_get
        
        with patch('zena_mode.arbitrage.SWARM_ENABLED', True), \
             patch('zena_mode.arbitrage.SWARM_SIZE', 3):
            arb = SwarmArbitrator(ports=None) 
            await arb.discover_swarm()
            
        assert 8001 in arb.ports
        assert 8006 in arb.ports
        assert len(arb.ports) == 2
        assert len(arb.endpoints) == 2

    @pytest.mark.asyncio
    async def test_discover_swarm_disabled(self):
        """Test discover_swarm respects SWARM_ENABLED=False."""
        with patch('zena_mode.arbitrage.SWARM_ENABLED', False):
            arb = SwarmArbitrator(ports=None)
            await arb.discover_swarm()
            
        assert len(arb.ports) == 1
        assert arb.ports[0] == 8001

    def test_calculate_consensus_simple(self):
        """Test word-overlap consensus calculation."""
        arb = SwarmArbitrator(ports=[8001])
        
        # 100% Match
        assert arb._calculate_consensus_simple(["hello world", "hello world"]) == 1.0
        
        # 50% Match (hello is common, world/there are distinct)
        # common={hello}, union={hello, world, there} -> 1/3 = 0.333
        score = arb._calculate_consensus_simple(["hello world", "hello there"])
        assert 0.3 < score < 0.4
        
        # 0% Match
        assert arb._calculate_consensus_simple(["apple", "banana"]) == 0.0

    @pytest.mark.asyncio
    async def test_query_model_success(self):
        """Test _query_model handles successful HTTP responses."""
        arb = SwarmArbitrator(ports=[8001])
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "I am 95% confident this works."}}],
            "model": "Test-Model-v1"
        }
        mock_client.post.return_value = mock_resp
        
        result = await arb._query_model(mock_client, arb.endpoints[0], [{"role": "user", "content": "hi"}])
        
        assert "95% confident" in result["content"]
        assert result["model"] == "Test-Model-v1"
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_query_model_error(self):
        """Test _query_model handles HTTP errors gracefully."""
        arb = SwarmArbitrator(ports=[8001])
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_client.post.return_value = mock_resp
        
        result = await arb._query_model(mock_client, arb.endpoints[0], [{"role": "user", "content": "hi"}])
        
        assert "Error: 500" in result["content"]

    @pytest.mark.asyncio
    async def test_get_cot_response_single_reflection(self):
        """Test CoT flow with a single model (Reflection mode)."""
        arb = SwarmArbitrator(ports=[8001])
        
        responses = [
            {"content": "Initial Thought", "time": 0.1, "model": "M1", "confidence": 0.8},
            {"content": "Refined Thought", "time": 0.1, "model": "M1", "confidence": 0.9}
        ]
        
        with patch.object(arb, '_query_model_with_timeout', side_effect=responses):
            class MockResp:
                async def aiter_lines(self):
                    yield 'data: {"choices": [{"delta": {"content": "Final Result"}}]}'
                    yield 'data: [DONE]'

            class MockContext:
                async def __aenter__(self): return MockResp()
                async def __aexit__(self, *args, **kwargs): pass

            class MockClient:
                async def __aenter__(self): return self
                async def __aexit__(self, *args, **kwargs): pass
                def stream(self, *args, **kwargs): return MockContext()
            
            with patch('httpx.AsyncClient', return_value=MockClient()):
                output = []
                async for chunk in arb.get_cot_response("test", "sys"):
                    output.append(chunk)
                
                full_text = "".join(output)
                assert "Final Result" in full_text

    def test_detect_contradictions(self):
        """Test embedding-based contradiction detection."""
        arb = SwarmArbitrator(ports=[8001])
        # Very different sentences should trigger contradiction
        responses = [
            "The capital of France is Paris.",
            "Sharks are a type of fruit that grows on trees."
        ]
        
        contradictions = arb.detect_contradictions(responses)
        assert len(contradictions) > 0
        assert contradictions[0]['pair'] == (1, 2)
        assert contradictions[0]['similarity'] < 0.2

    @pytest.mark.asyncio
    async def test_external_agent_bridge(self):
        """Test LiteLLM bridge placeholder."""
        arb = SwarmArbitrator(ports=[8001])
        result = await arb._query_external_agent("gpt-4o", [{"role": "user", "content": "hi"}])
        assert "LITELLM MOCK" in result["content"]
        assert result["model"] == "gpt-4o"

    def test_autogen_init(self):
        """Test AutoGen swarm initialization stub."""
        arb = SwarmArbitrator(ports=[8001])
        # Should not raise exception
        arb.init_autogen_swarm()
