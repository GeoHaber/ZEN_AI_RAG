"""
Integration tests for enhanced arbitrage.py with SwarmArbitrator backend.

Tests backward compatibility and new features.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from zena_mode.arbitrage import SwarmArbitrator, get_arbitrator


class TestArbitrageIntegration:
    """Test enhanced arbitrage maintains backward compatibility."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Mock config_system.config with proper DB path."""
        with patch('zena_mode.arbitrage.config') as mock_cfg:
            mock_cfg.SWARM_ENABLED = True
            mock_cfg.SWARM_SIZE = 4
            mock_cfg.llm_port = 8001
            mock_cfg.host = "127.0.0.1"
            mock_cfg.BASE_DIR = tmp_path  # Fixes DB Init Error
            yield mock_cfg

    def test_get_arbitrator_factory(self, mock_config):
        """Test factory function returns instance."""
        arb = get_arbitrator()
        assert isinstance(arb, SwarmArbitrator)
        assert hasattr(arb, 'ports')
        assert hasattr(arb, 'endpoints')
        assert hasattr(arb, 'discover_swarm')
        assert hasattr(arb, 'get_cot_response')

    def test_arbitrator_has_enhanced_backend(self, mock_config):
        """Test arbitrator uses EnhancedSwarmArbitrator backend."""
        arb = SwarmArbitrator(ports=[8001])
        assert hasattr(arb, '_enhanced')
        assert arb._enhanced is not None

    def test_arbitrator_backward_compatible_ports(self, mock_config):
        """Test arbitrator maintains ports/endpoints attributes."""
        arb = SwarmArbitrator(ports=[8001, 8005])
        assert arb.ports == [8001, 8005]
        assert len(arb.endpoints) == 2
        assert "http://127.0.0.1:8001" in arb.endpoints[0]
        assert "http://127.0.0.1:8005" in arb.endpoints[1]

    @pytest.mark.asyncio
    async def test_get_cot_response_signature(self, mock_config):
        """Test get_cot_response maintains original signature."""
        arb = SwarmArbitrator(ports=[8001])

        # Mock the _query_model method
        mock_response = {
            "content": "Test response",
            "time": 0.5,
            "model": "test-model",
            "error": False
        }

        with patch.object(arb, '_query_model', return_value=mock_response):
            result_chunks = []
            async for chunk in arb.get_cot_response(
                text="What is 2+2?",
                system_prompt="You are helpful",
                verbose=False
            ):
                result_chunks.append(chunk)

            # Should yield at least one chunk
            assert len(result_chunks) > 0

    def test_calculate_consensus_uses_enhanced_method(self, mock_config):
        """Test consensus calculation uses hybrid method from backend."""
        arb = SwarmArbitrator(ports=[8001])

        # Test identical responses
        responses = ["The answer is 4", "The answer is 4"]
        score = arb._calculate_consensus_simple(responses)
        assert score > 0.8  # Should be high agreement

        # Test different responses
        responses_diff = ["The answer is 4", "The answer is 5"]
        score_diff = arb._calculate_consensus_simple(responses_diff)
        assert score_diff < score  # Should be lower agreement

    @pytest.mark.asyncio
    async def test_query_model_uses_timeout(self, mock_config):
        """Test _query_model uses timeout from enhanced backend."""
        import httpx
        arb = SwarmArbitrator(ports=[8001])

        # Mock the enhanced backend's timeout method
        mock_result = {
            "content": "Test",
            "time": 0.1,
            "model": "test",
            "error": False
        }

        with patch.object(arb._enhanced, '_query_model_with_timeout', return_value=mock_result) as mock_timeout:
            async with httpx.AsyncClient() as client:
                result = await arb._query_model(client, "http://test", [])

            # Verify timeout method was called
            mock_timeout.assert_called_once()
            assert result["content"] == "Test"

    @pytest.mark.asyncio
    async def test_partial_failure_handling(self, mock_config):
        """Test arbitrator handles partial expert failures gracefully."""
        arb = SwarmArbitrator(ports=[8001, 8005, 8006])

        # Mock responses with one failure
        responses = [
            {"content": "Answer A", "time": 0.5, "model": "model-1", "error": False},
            {"content": "[TIMEOUT]", "time": 10.0, "model": "model-2", "error": True},
            {"content": "Answer A", "time": 0.6, "model": "model-3", "error": False},
        ]

        with patch.object(arb, '_query_model', side_effect=responses):
            result_chunks = []
            async for chunk in arb.get_cot_response(
                text="Test query",
                system_prompt="Test",
                verbose=False
            ):
                result_chunks.append(chunk)

            # Should still produce results despite one failure
            assert len(result_chunks) > 0

    def test_confidence_extraction_integration(self, mock_config):
        """Test confidence extraction works via backend."""
        arb = SwarmArbitrator(ports=[8001])

        # Test extraction through enhanced backend
        test_cases = [
            ("I am 90% confident", 0.9),
            ("I'm certain about this", 0.95),
            ("Maybe this is correct", 0.5),
            ("This is the answer", 0.7),  # default
        ]

        for text, expected in test_cases:
            confidence = arb._enhanced._extract_confidence(text)
            assert abs(confidence - expected) < 0.1, f"Failed for: {text}"

    def test_performance_tracking_initialized(self, mock_config):
        """Test performance tracker is initialized."""
        arb = SwarmArbitrator(ports=[8001])
        assert hasattr(arb._enhanced, 'performance_tracker')
        assert arb._enhanced.performance_tracker is not None


class TestDiscoveryCompatibility:
    """Test discovery_swarm backward compatibility."""

    @pytest.fixture
    def mock_config_disabled(self, tmp_path):
        """Mock config with swarm disabled."""
        with patch('zena_mode.arbitrage.config') as mock_cfg:
            mock_cfg.SWARM_ENABLED = False
            mock_cfg.SWARM_SIZE = 0
            mock_cfg.llm_port = 8001
            mock_cfg.host = "127.0.0.1"
            mock_cfg.BASE_DIR = tmp_path
            yield mock_cfg

    def test_discover_swarm_when_disabled(self, mock_config_disabled):
        """Test discovery falls back to 8001 when disabled."""
        arb = SwarmArbitrator()
        assert arb.ports == [8001]
        assert len(arb.endpoints) == 1

    @pytest.fixture
    def mock_config_enabled(self, tmp_path):
        """Mock config with swarm enabled."""
        with patch('zena_mode.arbitrage.config') as mock_cfg:
            mock_cfg.SWARM_ENABLED = True
            mock_cfg.SWARM_SIZE = 4
            mock_cfg.llm_port = 8001
            mock_cfg.host = "127.0.0.1"
            mock_cfg.BASE_DIR = tmp_path
            yield mock_cfg

    @pytest.mark.asyncio
    async def test_discover_swarm_async_backend(self, mock_config_enabled):
        """Test discovery uses async backend."""
        arb = SwarmArbitrator(ports=[8001])  # Skip discovery in __init__

        # Mock the enhanced backend's discover_swarm
        arb._enhanced.ports = [8001, 8005, 8006]
        arb._enhanced.endpoints = [
            "http://127.0.0.1:8001/v1/chat/completions",
            "http://127.0.0.1:8005/v1/chat/completions",
            "http://127.0.0.1:8006/v1/chat/completions",
        ]

        with patch.object(arb._enhanced, 'discover_swarm', new_callable=AsyncMock):
            arb.discover_swarm()

            # State should sync from backend
            # (discovery_swarm in arbitrage.py syncs self.ports from self._enhanced.ports)
            # For this test we've already set the backend state, so just verify sync
            assert arb.ports == arb._enhanced.ports
            assert arb.endpoints == arb._enhanced.endpoints


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
