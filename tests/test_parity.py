import pytest
import asyncio
from unittest.mock import MagicMock, patch
from zena_mode.arbitrage import SwarmArbitrator, ConsensusProtocol, AgentPerformanceTracker
from pathlib import Path

@pytest.fixture
def arbitrator(tmp_path):
    """Arbitrator."""
    # Use a unique temporary DB for each test
    db_file = tmp_path / "test_performance.db"
    arb = SwarmArbitrator()
    arb.performance_tracker = AgentPerformanceTracker(db_path=str(db_file))
    yield arb

def test_protocol_routing(arbitrator):
    """Verify that different task types map to the correct research-backed protocols."""
    assert arbitrator.select_protocol("factual") == ConsensusProtocol.CONSENSUS
    assert arbitrator.select_protocol("reasoning") == ConsensusProtocol.WEIGHTED_VOTE
    assert arbitrator.select_protocol("creative") == ConsensusProtocol.VOTING
    assert arbitrator.select_protocol("math") == ConsensusProtocol.WEIGHTED_VOTE
    assert arbitrator.select_protocol("unknown") == ConsensusProtocol.HYBRID

def test_performance_stats(arbitrator):
    """Verify that AgentPerformanceTracker records and summarizes stats correctly."""
    tracker = arbitrator.performance_tracker
    tracker.record_response("agent-1", "factual", "hash1", "answer1", True, 0.9, 0.95)
    tracker.record_response("agent-1", "factual", "hash2", "answer2", False, 0.4, 0.60)
    
    stats = tracker.get_stats()
    assert stats["total_queries"] == 2
    assert stats["avg_consensus"] == pytest.approx(0.65)
    assert stats["avg_confidence"] == pytest.approx(0.775)

def test_agent_reliability(arbitrator):
    """Verify historical reliability calculation."""
    tracker = arbitrator.performance_tracker
    # agent-a is selected 100% of the time (3/3)
    tracker.record_response("agent-a", "factual", "h1", "ans", True, 0.9, 0.9)
    tracker.record_response("agent-a", "factual", "h2", "ans", True, 0.9, 0.9)
    tracker.record_response("agent-a", "code", "h3", "ans", True, 0.9, 0.9)
    
    # agent-b is selected 50% of the time (1/2)
    tracker.record_response("agent-b", "factual", "h1", "ans", True, 0.9, 0.9)
    tracker.record_response("agent-b", "factual", "h2", "ans", False, 0.9, 0.9)
    
    assert tracker.get_agent_reliability("agent-a") == 1.0
    assert tracker.get_agent_reliability("agent-b") == 0.5
    assert tracker.get_agent_reliability("agent-a", task_type="factual") == 1.0
    assert tracker.get_agent_reliability("agent-c") == 0.5 # Default for new agent

@pytest.mark.asyncio
async def test_contradiction_detection(arbitrator):
    """Verify that semantic contradictions are detected using embeddings."""
    # Patch the class in its own module since it's imported locally
    with patch('sentence_transformers.SentenceTransformer') as MockST:
        mock_model = MockST.return_value
        # Two very different vectors (sim ~ 0)
        mock_model.encode.return_value = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        
        # We also need to mock cosine_similarity
        with patch('sklearn.metrics.pairwise.cosine_similarity') as MockSim:
            MockSim.return_value = [[1.0, 0.0], [0.0, 1.0]]
            
            responses = ["Answer A", "Answer B"]
            contradictions = arbitrator.detect_contradictions(responses)
            
            assert len(contradictions) == 1
            assert contradictions[0]["pair"] == (1, 2)
            assert contradictions[0]["similarity"] < 0.2

@pytest.mark.asyncio
async def test_weighted_performance_recording(arbitrator):
    """Verify that get_cot_response records reliability and protocol info."""
    MagicMock()
    # Mocking single-model loop for simplicity
    arbitrator.endpoints = ["http://localhost:8001"]
    
    with patch.object(arbitrator, '_query_model_with_timeout') as mock_query:
        mock_query.return_value = {
            "content": "Perfectly logical answer.",
            "model": "qwen2.5-coder",
            "time": 0.1,
            "confidence": 0.95
        }
        
        # Consume the generator
        async for _ in arbitrator.get_cot_response("What is 1+1?", "Prompt", task_type="factual"):
            pass
            
        stats = arbitrator.performance_tracker.get_stats()
        assert stats["total_queries"] >= 2 # 2 calls in single-model reflection loop
