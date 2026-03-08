# -*- coding: utf-8 -*-
"""
test_swarm_arbitrator.py - Comprehensive TDD test suite for SwarmArbitrator
Ronald Reagan: "Trust but Verify" - Every feature tested!
"""

import pytest
import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from zena_mode.swarm_arbitrator import (
    SwarmArbitrator,
    ArbitrationRequest,
    ExpertResponse,
    TaskType,
    get_arbitrator,
    AgentPerformanceTracker,
    ConsensusMethod,
    ConsensusProtocol,
)
from config_system import config

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test_performance.db"
    yield str(db_path)
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def performance_tracker(temp_db):
    """Create performance tracker with temp database."""
    return AgentPerformanceTracker(db_path=temp_db)


@pytest.fixture
def arbitrator():
    """Create arbitrator instance for testing."""
    config = {
        "enabled": True,
        "size": 3,
        "track_performance": False,  # Disable for unit tests
        "timeout_per_expert": 5.0,
    }
    return SwarmArbitrator(config=config)


@pytest.fixture
def mock_responses():
    """Mock expert responses for testing."""
    return [
        {
            "content": "The answer is 4 because 2 plus 2 equals 4.",
            "time": 0.5,
            "model": "model-a",
            "confidence": 0.9,
            "error": False,
        },
        {
            "content": "It equals four, which is the sum of two and two.",
            "time": 0.6,
            "model": "model-b",
            "confidence": 0.85,
            "error": False,
        },
        {
            "content": "The result is 4 (two plus two).",
            "time": 0.4,
            "model": "model-c",
            "confidence": 0.95,
            "error": False,
        },
    ]


# ============================================================================
# TEST AGENT PERFORMANCE TRACKER
# ============================================================================


class TestAgentPerformanceTracker:
    """Test performance tracking functionality."""

    def test_init_creates_database(self, temp_db):
        """Test database initialization."""
        AgentPerformanceTracker(db_path=temp_db)

        # Check database exists
        assert Path(temp_db).exists()

        # Check table exists
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_performance'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_record_response(self, performance_tracker):
        """Test recording agent response."""
        performance_tracker.record_response(
            agent_id="test-model",
            task_type="reasoning",
            query_hash="abc123",
            response_text="Test response",
            was_selected=True,
            consensus_score=0.85,
            confidence=0.9,
            response_time=1.5,
        )

        # Verify record exists
        conn = sqlite3.connect(performance_tracker.db_path)
        cursor = conn.execute("SELECT * FROM agent_performance WHERE agent_id='test-model'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[1] == "test-model"  # agent_id
        assert row[2] == "reasoning"  # task_type

    def test_get_agent_reliability_new_agent(self, performance_tracker):
        """Test reliability for new agent (no history)."""
        reliability = performance_tracker.get_agent_reliability("new-model")
        assert reliability == 0.5  # Default neutral

    def test_get_agent_reliability_with_history(self, performance_tracker):
        """Test reliability calculation with history."""
        # Record 3 successes, 1 failure
        for i in range(4):
            performance_tracker.record_response(
                agent_id="good-model",
                task_type="reasoning",
                query_hash=f"hash{i}",
                response_text="Response",
                was_selected=(i < 3),  # First 3 selected
                consensus_score=0.8,
                confidence=0.9,
                response_time=1.0,
            )

        reliability = performance_tracker.get_agent_reliability("good-model")
        assert reliability == 0.75  # 3/4 = 75%

    def test_get_stats(self, performance_tracker):
        """Test overall statistics."""
        # Record some data
        performance_tracker.record_response("model-1", "reasoning", "hash1", "Response 1", True, 0.8, 0.9, 1.0)
        performance_tracker.record_response("model-2", "reasoning", "hash2", "Response 2", False, 0.6, 0.7, 1.5)

        stats = performance_tracker.get_stats()

        assert stats["total_queries"] == 2
        assert stats["unique_agents"] == 2
        assert 0.0 <= stats["avg_consensus"] <= 1.0
        assert 0.0 <= stats["avg_confidence"] <= 1.0


# ============================================================================
# TEST CONFIDENCE EXTRACTION
# ============================================================================


class TestConfidenceExtraction:
    """Test confidence score extraction from responses."""

    def test_extract_explicit_percentage(self, arbitrator):
        """Test extraction of explicit percentage."""
        text = "I am 90% confident that this is correct."
        confidence = arbitrator._extract_confidence(text)
        assert confidence == 0.9

    def test_extract_explicit_decimal(self, arbitrator):
        """Test extraction of explicit decimal."""
        text = "Confidence: 0.85 in this answer."
        confidence = arbitrator._extract_confidence(text)
        assert confidence == 0.85

    def test_extract_linguistic_certain(self, arbitrator):
        """Test extraction from 'certain' marker."""
        text = "I am absolutely certain this is the answer."
        confidence = arbitrator._extract_confidence(text)
        assert confidence == 0.95

    def test_extract_linguistic_maybe(self, arbitrator):
        """Test extraction from 'maybe' marker."""
        text = "This might be the answer, maybe."
        confidence = arbitrator._extract_confidence(text)
        assert confidence == 0.5

    def test_extract_default_confidence(self, arbitrator):
        """Test default confidence when no markers found."""
        text = "The answer is 42."
        confidence = arbitrator._extract_confidence(text)
        assert confidence == 0.7  # Default


# ============================================================================
# TEST CONSENSUS CALCULATION
# ============================================================================


class TestConsensusCalculation:
    """Test consensus score calculation methods."""

    def test_wordset_identical_responses(self, arbitrator):
        """Test word-set method with identical responses."""
        responses = ["The answer is 4", "The answer is 4", "The answer is 4"]
        score = arbitrator._calculate_consensus_wordset(responses)
        assert score == 1.0  # Perfect agreement

    def test_wordset_completely_different(self, arbitrator):
        """Test word-set method with completely different responses."""
        responses = ["apple orange banana", "dog cat mouse", "car truck bus"]
        score = arbitrator._calculate_consensus_wordset(responses)
        assert score == 0.0  # No common words

    def test_wordset_partial_overlap(self, arbitrator):
        """Test word-set method with partial overlap."""
        responses = ["The answer is 4", "The result is 4", "The solution is 4"]
        score = arbitrator._calculate_consensus_wordset(responses)
        assert 0.0 < score < 1.0  # Partial agreement

    def test_wordset_single_response(self, arbitrator):
        """Test word-set method with single response."""
        responses = ["The answer is 4"]
        score = arbitrator._calculate_consensus_wordset(responses)
        assert score == 1.0  # Single response = perfect agreement

    def test_semantic_handles_synonyms(self, arbitrator):
        """Test semantic method handles synonyms better than word-set."""
        responses = ["The answer is 4", "The result is four", "It equals 4"]

        word_score = arbitrator._calculate_consensus_wordset(responses)

        try:
            semantic_score = arbitrator._calculate_consensus_semantic(responses)
            # Semantic should recognize similarity despite different words
            assert semantic_score >= word_score
        except ImportError:
            pytest.skip("sentence-transformers not installed")

    def test_consensus_method_selection(self, arbitrator):
        """Test consensus method selection."""
        responses = ["Answer A", "Answer B"]

        # Word-set method
        score1 = arbitrator._calculate_consensus(responses, ConsensusMethod.WORD_SET)
        assert isinstance(score1, float)

        # Hybrid method
        score2 = arbitrator._calculate_consensus(responses, ConsensusMethod.HYBRID)
        assert isinstance(score2, float)


# ============================================================================
# TEST PROTOCOL ROUTING
# ============================================================================


class TestProtocolRouting:
    """Test task-based protocol selection."""

    def test_select_protocol_factual(self, arbitrator):
        """Test protocol selection for factual tasks."""
        protocol = arbitrator.select_protocol("factual")
        assert protocol == ConsensusProtocol.CONSENSUS

    def test_select_protocol_reasoning(self, arbitrator):
        """Test protocol selection for reasoning tasks."""
        protocol = arbitrator.select_protocol("reasoning")
        assert protocol == ConsensusProtocol.WEIGHTED_VOTE

    def test_select_protocol_creative(self, arbitrator):
        """Test protocol selection for creative tasks."""
        protocol = arbitrator.select_protocol("creative")
        assert protocol == ConsensusProtocol.VOTING

    def test_select_protocol_unknown(self, arbitrator):
        """Test protocol selection for unknown task type."""
        protocol = arbitrator.select_protocol("unknown_task")
        assert protocol == ConsensusProtocol.HYBRID

    def test_protocol_routing_disabled(self):
        """Test protocol routing when disabled in config."""
        config = {"protocol_routing": False}
        arb = SwarmArbitrator(config=config)

        # Should always return WEIGHTED_VOTE when routing disabled
        protocol = arb.select_protocol("factual")
        assert protocol == ConsensusProtocol.WEIGHTED_VOTE


# ============================================================================
# TEST ADAPTIVE ROUND SELECTION
# ============================================================================


class TestAdaptiveRounds:
    """Test adaptive round selection logic."""

    def test_skip_round_two_high_agreement(self, arbitrator):
        """Test skipping Round 2 when agreement is high."""
        agreement = 0.85
        confidence_scores = [0.8, 0.9, 0.85]

        should_continue = arbitrator.should_do_round_two(agreement, confidence_scores)
        assert should_continue is False

    def test_skip_round_two_high_confidence(self, arbitrator):
        """Test skipping Round 2 when confidence is high."""
        agreement = 0.6
        confidence_scores = [0.9, 0.95, 0.88]

        should_continue = arbitrator.should_do_round_two(agreement, confidence_scores)
        assert should_continue is False

    def test_do_round_two_low_consensus(self, arbitrator):
        """Test doing Round 2 when consensus is low."""
        agreement = 0.3
        confidence_scores = [0.6, 0.7, 0.5]

        should_continue = arbitrator.should_do_round_two(agreement, confidence_scores)
        assert should_continue is True

    def test_adaptive_rounds_disabled(self):
        """Test behavior when adaptive rounds disabled."""
        config = {"adaptive_rounds": False}
        arb = SwarmArbitrator(config=config)

        # Should always return False (never do Round 2)
        should_continue = arb.should_do_round_two(0.3, [0.5, 0.6])
        assert should_continue is False


# ============================================================================
# TEST ASYNC DISCOVERY
# ============================================================================


class TestAsyncDiscovery:
    """Test async port discovery functionality."""

    @pytest.mark.asyncio
    async def test_discover_swarm_disabled(self):
        """Test discovery when swarm is disabled."""
        config = {"enabled": False}
        arb = SwarmArbitrator(config=config)

        await arb.discover_swarm()

        # Should only have main port
        assert len(arb.ports) == 1
        assert arb.ports[0] == 8001

    @pytest.mark.asyncio
    async def test_discover_swarm_respects_size_limit(self):
        """Test discovery respects SWARM_SIZE limit."""
        config = {"enabled": True, "size": 2}
        arb = SwarmArbitrator(config=config)

        # Mock port checks to return True for many ports
        async def mock_check(client, port):
            return True

        arb._check_port = mock_check
        await arb.discover_swarm()

        # Should be limited to 2
        assert len(arb.ports) <= 2

    @pytest.mark.asyncio
    async def test_check_port_handles_failure(self, arbitrator):
        """Test port check handles connection failures gracefully."""
        import httpx

        client = httpx.AsyncClient()

        # Check non-existent port
        is_live = await arbitrator._check_port(client, 9999)

        await client.aclose()

        assert is_live is False


# ============================================================================
# TEST TIMEOUT HANDLING
# ============================================================================


class TestTimeoutHandling:
    """Test per-expert timeout functionality."""

    @pytest.mark.asyncio
    async def test_query_with_timeout_success(self, arbitrator):
        """Test successful query within timeout."""
        import httpx

        client = httpx.AsyncClient()

        # Mock successful response
        async def mock_query(client, endpoint, messages):
            """Mock query."""
            await asyncio.sleep(0.1)  # Fast response
            return {"content": "Test response", "time": 0.1, "model": "test-model", "confidence": 0.8, "error": False}

        arbitrator._query_model = mock_query

        result = await arbitrator._query_model_with_timeout(client, "http://test", [], timeout=1.0)

        await client.aclose()

        assert result["error"] is False
        assert "Test response" in result["content"]

    @pytest.mark.asyncio
    async def test_query_with_timeout_timeout(self, arbitrator):
        """Test query timeout handling."""
        import httpx

        client = httpx.AsyncClient()

        # Mock slow response
        async def mock_query(client, endpoint, messages):
            await asyncio.sleep(10)  # Very slow
            return {"content": "Never reached"}

        arbitrator._query_model = mock_query

        result = await arbitrator._query_model_with_timeout(client, "http://test", [], timeout=0.1)

        await client.aclose()

        assert result["error"] is True
        assert "TIMEOUT" in result["content"]
        assert result["confidence"] == 0.0


# ============================================================================
# TEST PARTIAL FAILURE HANDLING
# ============================================================================


class TestPartialFailures:
    """Test handling of partial expert failures."""

    def test_filter_valid_responses(self, mock_responses):
        """Test filtering of valid vs failed responses."""
        # Add a failed response
        mock_responses.append(
            {"content": "[TIMEOUT after 30s]", "time": 30.0, "model": "model-d", "confidence": 0.0, "error": True}
        )

        # Filter valid responses
        valid = [r for r in mock_responses if not r.get("error", False)]

        assert len(valid) == 3
        assert len(mock_responses) == 4


# ============================================================================
# TEST FACTORY FUNCTION
# ============================================================================


class TestFactoryFunction:
    """Test arbitrator factory function."""

    def test_get_arbitrator_returns_instance(self):
        """Test factory returns SwarmArbitrator instance."""
        arb = get_arbitrator()
        assert isinstance(arb, SwarmArbitrator)

    def test_get_arbitrator_with_config(self):
        """Test factory accepts config."""
        config = {"size": 5}
        arb = get_arbitrator(config=config)
        assert arb.config["size"] == 5


# ============================================================================
# TEST INTEGRATION
# ============================================================================


class TestIntegration:
    """Integration tests for full workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow_mock(self, arbitrator):
        """Test full consensus workflow with mocked responses."""
        import httpx

        # Mock discovery
        arbitrator.ports = [8001, 8005, 8006]
        arbitrator.endpoints = [
            "http://127.0.0.1:8001/v1/chat/completions",
            "http://127.0.0.1:8005/v1/chat/completions",
            "http://127.0.0.1:8006/v1/chat/completions",
        ]

        # Mock query responses
        mock_responses = [
            {"content": "The answer is 4", "time": 0.5, "model": "model-a", "confidence": 0.9, "error": False},
            {"content": "The result is 4", "time": 0.6, "model": "model-b", "confidence": 0.85, "error": False},
            {"content": "It equals 4", "time": 0.4, "model": "model-c", "confidence": 0.95, "error": False},
        ]

        call_count = [0]

        async def mock_query(client, endpoint, messages, timeout=None):
            result = mock_responses[call_count[0] % len(mock_responses)]
            call_count[0] += 1
            return result

        arbitrator._query_model_with_timeout = mock_query

        # Mock streaming referee response
        async def mock_stream(*args, **kwargs):
            """Mock stream."""

            class MockStream:
                """MockStream class."""

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    pass

                async def aiter_lines(self):
                    yield 'data: {"choices":[{"delta":{"content":"Final"}}]}'
                    yield 'data: {"choices":[{"delta":{"content":" answer"}}]}'
                    yield "data: [DONE]"

            return MockStream()

        # Execute consensus
        chunks = []
        async for chunk in arbitrator.get_consensus("What is 2+2?"):
            chunks.append(chunk)

        # Verify we got output
        assert len(chunks) > 0
        full_output = "".join(chunks)
        assert "Analyzing" in full_output or "Thinking" in full_output


# ============================================================================
# TEST ERROR HANDLING
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_empty_responses_list(self, arbitrator):
        """Test consensus calculation with empty list."""
        score = arbitrator._calculate_consensus_wordset([])
        assert score == 0.0

    def test_single_empty_response(self, arbitrator):
        """Test consensus with one empty response."""
        responses = [""]
        score = arbitrator._calculate_consensus_wordset(responses)
        assert isinstance(score, float)

    @pytest.mark.asyncio
    async def test_no_endpoints_available(self):
        """Test behavior when no endpoints available."""
        config = {"enabled": False}
        arb = SwarmArbitrator(config=config)
        arb.ports = []
        arb.endpoints = []

        chunks = []
        async for chunk in arb.get_consensus("Test question"):
            chunks.append(chunk)

        output = "".join(chunks)
        assert "Error" in output or "available" in output.lower()


# ============================================================================
# PERFORMANCE BENCHMARKS
# ============================================================================


class TestPerformance:
    """Performance benchmarking tests."""

    def test_consensus_calculation_speed(self, arbitrator):
        """Test consensus calculation performance."""
        import time

        responses = ["Test response " + str(i) for i in range(10)]

        start = time.time()
        for _ in range(100):
            arbitrator._calculate_consensus_wordset(responses)
        duration = time.time() - start

        # Should be very fast (< 0.1s for 100 iterations)
        assert duration < 0.1

    def test_confidence_extraction_speed(self, arbitrator):
        """Test confidence extraction performance."""
        import time

        texts = [
            "I am 90% confident this is correct.",
            "Maybe this is the answer.",
            "I'm absolutely certain about this.",
        ] * 10

        start = time.time()
        for text in texts:
            arbitrator._extract_confidence(text)
        duration = time.time() - start

        # Should be very fast
        assert duration < 0.1


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
