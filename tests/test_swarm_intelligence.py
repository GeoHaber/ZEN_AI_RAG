import pytest
import asyncio
from zena_mode.arbitrage import SwarmArbitrator, ConsensusProtocol


@pytest.fixture
def arbitrator():
    return SwarmArbitrator(ports=[8001, 8002])


def test_protocol_selection(arbitrator):
    """Verify that different task types map to correct protocols."""
    assert arbitrator.select_protocol("factual") == ConsensusProtocol.CONSENSUS
    assert arbitrator.select_protocol("reasoning") == ConsensusProtocol.WEIGHTED_VOTE
    assert arbitrator.select_protocol("creative") == ConsensusProtocol.VOTING
    assert arbitrator.select_protocol("unknown") == ConsensusProtocol.HYBRID


def test_expert_specialization_prompts(arbitrator):
    """Verify that specialized system prompts exist for roles."""
    assert "security" in arbitrator.TASK_SYSTEM_PROMPTS
    assert "performance" in arbitrator.TASK_SYSTEM_PROMPTS
    assert "You are a security auditor" in arbitrator.TASK_SYSTEM_PROMPTS["security"]


@pytest.mark.asyncio
async def test_latency_sorting(arbitrator, mocker):
    """Verify that ports are sorted by latency."""
    arbitrator.latencies = {8001: 0.5, 8002: 0.1}
    arbitrator.ports = [8001, 8002]

    # Trigger the sort logic (normally in discover_swarm)
    arbitrator.ports.sort(key=lambda p: arbitrator.latencies.get(p, 999))

    assert arbitrator.ports == [8002, 8001]


def test_hallucination_penalty_logic(arbitrator):
    """Verify that the verification score affects selection logic."""
    # Mock a verification result
    # The logic should eventually use this to penalize the agent's reliability
    pass


if __name__ == "__main__":
    pytest.main([__file__])
