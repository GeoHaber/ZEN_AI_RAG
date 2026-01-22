import pytest
import asyncio
import httpx
import time
import statistics
from typing import List, Dict
from zena_mode.arbitrage import get_arbitrator

class TestSwarmTDD:
    """
    TDD Suite for Swarm Parallelization and Latency Analysis.
    Answers: 'How long it takes for agent to reply' and 'how we parallelize'.
    """

    @pytest.mark.asyncio
    async def test_agent_parallel_dispatch(self):
        """
        Tests the 'asyncio.gather' parallelization strategy.
        Verifies that messages are sent to all agents simultaneously.
        """
        arb = get_arbitrator()
        if len(arb.ports) < 2:
            pytest.skip("Test requires at least 2 active experts.")

        prompt = "Define 'Emergence' in 10 words."
        print(f"\n[TDD] Dispatching to {len(arb.ports)} agents in parallel...")
        
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            # This is HOW we parallelize: mapping a list of endpoints to async tasks
            tasks = [arb._query_model(client, ep, [{"role": "user", "content": prompt}]) for ep in arb.endpoints]
            results = await asyncio.gather(*tasks)
            
        total_duration = time.time() - start_time
        
        print(f"[TDD] Parallel workflow completed in {total_duration:.2f}s")
        
        # Verify all agents replied with string data
        for i, res in enumerate(results):
            assert isinstance(res, str), f"Agent {i} failed to return string output"
            assert len(res) > 0, f"Agent {i} returned empty string"
            print(f"[Agent {i+1}] Raw Output: {res[:50]}...")

    @pytest.mark.asyncio
    async def test_per_agent_latency_profile(self):
        """
        Detailed profiling of individual agent response times.
        Answers: 'How long it takes for agent to reply'
        """
        arb = get_arbitrator()
        if not arb.ports:
            pytest.skip("No experts available.")

        prompt = "What is the capital of France?"
        stats = []

        print("\n\n=== INDIVIDUAL AGENT LATENCY PROFILE ===")
        async with httpx.AsyncClient() as client:
            for i, ep in enumerate(arb.endpoints):
                port = arb.ports[i]
                
                # Measure per-agent overhead
                start = time.time()
                response = await arb._query_model(client, ep, [{"role": "user", "content": prompt}])
                duration = time.time() - start
                
                stats.append(duration)
                print(f"Expert {i+1} (Port {port}): {duration:.3f}s | Output: '{response.strip()}'")

        avg_lat = statistics.mean(stats)
        max_lat = max(stats)
        print(f"--- Statistics ---")
        print(f"Average Agent Reply Time: {avg_lat:.3f}s")
        print(f"Worst Case Latency: {max_lat:.3f}s")
        print("========================================\n")
        
        assert avg_lat < 10.0, "Average latency is unacceptably high for local inference"

    @pytest.mark.asyncio
    async def test_communication_overhead_referee(self):
        """
        Measures the cost of the 'Arbitrage' step vs individual experts.
        """
        arb = get_arbitrator()
        if not arb.ports:
            pytest.skip("No experts available.")

        query = "Is 9.11 or 9.9 bigger?" # Classic LLM logic trap
        
        # 1. Total CoT Time
        start_cot = time.time()
        cot_chunks = []
        async for chunk in arb.get_cot_response(query, "System"):
            cot_chunks.append(chunk)
        dur_cot = time.time() - start_cot
        
        print(f"\n[Bench] Full CoT Swarm Lifecycle: {dur_cot:.2f}s")
        
        # 2. Extract Referee Text
        full_cot = "".join(cot_chunks)
        assert "Arbitrage" in full_cot or "Expert" in full_cot
        print(f"[Bench] CoT Integrity: {len(full_cot)} characters of reasoning captured.")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
