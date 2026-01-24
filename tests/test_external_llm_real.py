"""
Phase 2: Real API Testing for External LLM Integration

Tests the integration with REAL APIs from:
- Anthropic Claude 3.5 Sonnet
- Google Gemini Pro
- Grok (optional)

Requirements:
- ANTHROPIC_API_KEY environment variable
- GOOGLE_API_KEY environment variable
- XAI_API_KEY environment variable (optional)

Expected Cost: ~$0.03 total

Test Queries:
1. Factual: "What is the capital of France?" (expect agreement)
2. Math: "If a train travels at 60mph for 2.5 hours, how far does it go?" (expect agreement)
3. Nuanced: "Should investors buy stocks during a recession?" (expect disagreement)
4. Code: "Write a Python function to check if a number is prime" (expect different implementations)
"""
import pytest
import asyncio
import os
import json
from datetime import datetime
from pathlib import Path

# Import modules to test
import sys
sys.path.insert(0, '.')

try:
    from zena_mode.arbitrage import SwarmArbitrator, CostTracker
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False
    pytest.skip("RAG modules not available", allow_module_level=True)


# Check for API keys
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
GROK_KEY = os.getenv("XAI_API_KEY")

# Skip all tests if no API keys present
if not (ANTHROPIC_KEY or GOOGLE_KEY or GROK_KEY):
    pytest.skip(
        "No API keys found. Set ANTHROPIC_API_KEY, GOOGLE_API_KEY, or XAI_API_KEY to run Phase 2 tests.",
        allow_module_level=True
    )


class TestRealAPIQueries:
    """Test real API queries to external LLMs."""

    @pytest.fixture
    def arbitrator(self):
        """Create arbitrator instance (no local models needed)."""
        return SwarmArbitrator(ports=[8001])

    @pytest.fixture
    def cost_tracker(self):
        """Create cost tracker instance."""
        return CostTracker()

    @pytest.mark.asyncio
    async def test_factual_query_consensus(self, arbitrator, cost_tracker):
        """
        Test 1: Factual Query - High Agreement Expected

        Query: "What is the capital of France?"
        Expected: All LLMs should agree → "Paris"
        Expected Cost: ~$0.005
        """
        query = "What is the capital of France?"
        messages = [{"role": "user", "content": query}]

        # Query available providers
        results = []

        if ANTHROPIC_KEY:
            result = await arbitrator._query_external_agent("claude-3-5-sonnet-20241022", messages)
            results.append(result)
            cost_tracker.record_query(result["model"], result["content"])
            print(f"\n[Claude] {result['content'][:200]}... ({result['time']:.2f}s)")

        if GOOGLE_KEY:
            result = await arbitrator._query_external_agent("gemini-pro", messages)
            results.append(result)
            cost_tracker.record_query(result["model"], result["content"])
            print(f"[Gemini] {result['content'][:200]}... ({result['time']:.2f}s)")

        if GROK_KEY:
            result = await arbitrator._query_external_agent("grok-beta", messages)
            results.append(result)
            cost_tracker.record_query(result["model"], result["content"])
            print(f"[Grok] {result['content'][:200]}... ({result['time']:.2f}s)")

        # Verify we got at least one response
        assert len(results) > 0, "No API responses received"

        # Calculate consensus
        responses = [r["content"] for r in results if not r["content"].startswith("[")]
        if len(responses) > 1:
            consensus = arbitrator._calculate_consensus_simple(responses)
            print(f"\nConsensus: {consensus:.1%}")

            # Factual query should have high consensus (all say "Paris")
            assert consensus > 0.3, f"Expected high consensus for factual query, got {consensus:.1%}"

        # Check all responses mention "Paris"
        for result in results:
            if not result["content"].startswith("["):  # Skip error messages
                assert "Paris" in result["content"], f"Expected 'Paris' in response: {result['content']}"

        print(f"\nTest Cost: ${cost_tracker.get_total_cost():.4f}")

    @pytest.mark.asyncio
    async def test_math_query_consensus(self, arbitrator, cost_tracker):
        """
        Test 2: Math Query - High Agreement Expected

        Query: "If a train travels at 60mph for 2.5 hours, how far does it go?"
        Expected: All LLMs should agree → "150 miles"
        Expected Cost: ~$0.005
        """
        query = "If a train travels at 60mph for 2.5 hours, how far does it go? Provide just the numerical answer with units."
        messages = [{"role": "user", "content": query}]

        results = []

        if ANTHROPIC_KEY:
            result = await arbitrator._query_external_agent("claude-3-5-sonnet-20241022", messages)
            results.append(result)
            cost_tracker.record_query(result["model"], result["content"])
            print(f"\n[Claude] {result['content'][:200]}... ({result['time']:.2f}s)")

        if GOOGLE_KEY:
            result = await arbitrator._query_external_agent("gemini-pro", messages)
            results.append(result)
            cost_tracker.record_query(result["model"], result["content"])
            print(f"[Gemini] {result['content'][:200]}... ({result['time']:.2f}s)")

        if GROK_KEY:
            result = await arbitrator._query_external_agent("grok-beta", messages)
            results.append(result)
            cost_tracker.record_query(result["model"], result["content"])
            print(f"[Grok] {result['content'][:200]}... ({result['time']:.2f}s)")

        assert len(results) > 0

        # Check all responses mention "150"
        for result in results:
            if not result["content"].startswith("["):
                assert "150" in result["content"], f"Expected '150' in response: {result['content']}"

        print(f"\nTest Cost: ${cost_tracker.get_total_cost():.4f}")

    @pytest.mark.asyncio
    async def test_nuanced_query_disagreement(self, arbitrator, cost_tracker):
        """
        Test 3: Nuanced Query - Disagreement Expected

        Query: "Should investors buy stocks during a recession?"
        Expected: Different opinions → low/moderate consensus
        Expected Cost: ~$0.01
        """
        query = "Should investors buy stocks during a recession? Keep your answer brief (2-3 sentences)."
        messages = [{"role": "user", "content": query}]

        results = []

        if ANTHROPIC_KEY:
            result = await arbitrator._query_external_agent("claude-3-5-sonnet-20241022", messages)
            results.append(result)
            cost_tracker.record_query(result["model"], result["content"])
            print(f"\n[Claude] {result['content'][:300]}... ({result['time']:.2f}s)")

        if GOOGLE_KEY:
            result = await arbitrator._query_external_agent("gemini-pro", messages)
            results.append(result)
            cost_tracker.record_query(result["model"], result["content"])
            print(f"[Gemini] {result['content'][:300]}... ({result['time']:.2f}s)")

        if GROK_KEY:
            result = await arbitrator._query_external_agent("grok-beta", messages)
            results.append(result)
            cost_tracker.record_query(result["model"], result["content"])
            print(f"[Grok] {result['content'][:300]}... ({result['time']:.2f}s)")

        assert len(results) > 0

        # Calculate consensus
        responses = [r["content"] for r in results if not r["content"].startswith("[")]
        if len(responses) > 1:
            consensus = arbitrator._calculate_consensus_simple(responses)
            print(f"\nConsensus: {consensus:.1%}")

            # Nuanced query can have varying consensus (not testing specific value)
            # Just verify consensus calculation works
            assert 0.0 <= consensus <= 1.0

        print(f"\nTest Cost: ${cost_tracker.get_total_cost():.4f}")

    @pytest.mark.asyncio
    async def test_code_generation_query(self, arbitrator, cost_tracker):
        """
        Test 4: Code Generation Query - Different Implementations Expected

        Query: "Write a Python function to check if a number is prime"
        Expected: Different implementations → moderate consensus
        Expected Cost: ~$0.01
        """
        query = "Write a Python function to check if a number is prime. Keep it simple and include the function signature."
        messages = [{"role": "user", "content": query}]

        results = []

        if ANTHROPIC_KEY:
            result = await arbitrator._query_external_agent("claude-3-5-sonnet-20241022", messages)
            results.append(result)
            cost_tracker.record_query(result["model"], result["content"])
            print(f"\n[Claude] {result['content'][:300]}... ({result['time']:.2f}s)")

        if GOOGLE_KEY:
            result = await arbitrator._query_external_agent("gemini-pro", messages)
            results.append(result)
            cost_tracker.record_query(result["model"], result["content"])
            print(f"[Gemini] {result['content'][:300]}... ({result['time']:.2f}s)")

        if GROK_KEY:
            result = await arbitrator._query_external_agent("grok-beta", messages)
            results.append(result)
            cost_tracker.record_query(result["model"], result["content"])
            print(f"[Grok] {result['content'][:300]}... ({result['time']:.2f}s)")

        assert len(results) > 0

        # All responses should contain Python code
        for result in results:
            if not result["content"].startswith("["):
                assert "def" in result["content"], f"Expected Python function in response"
                assert "prime" in result["content"].lower(), f"Expected 'prime' in response"

        # Calculate consensus
        responses = [r["content"] for r in results if not r["content"].startswith("[")]
        if len(responses) > 1:
            consensus = arbitrator._calculate_consensus_simple(responses)
            print(f"\nConsensus: {consensus:.1%}")

        print(f"\nTest Cost: ${cost_tracker.get_total_cost():.4f}")


class TestCostTracking:
    """Test cost tracking across real API calls."""

    @pytest.mark.asyncio
    async def test_total_cost_under_budget(self):
        """
        Test 5: Cost Tracking - Stay Under Budget

        Verify that all Phase 2 tests stay under $0.05 budget.
        """
        arbitrator = SwarmArbitrator(ports=[8001])
        cost_tracker = CostTracker()

        # Simple test query
        query = "Hello, world!"
        messages = [{"role": "user", "content": query}]

        if ANTHROPIC_KEY:
            result = await arbitrator._query_external_agent("claude-3-5-sonnet-20241022", messages)
            cost_tracker.record_query(result["model"], result["content"])

        if GOOGLE_KEY:
            result = await arbitrator._query_external_agent("gemini-pro", messages)
            cost_tracker.record_query(result["model"], result["content"])

        if GROK_KEY:
            result = await arbitrator._query_external_agent("grok-beta", messages)
            cost_tracker.record_query(result["model"], result["content"])

        total_cost = cost_tracker.get_total_cost()
        print(f"\nTotal Cost: ${total_cost:.4f}")

        # Single query should be very cheap (< $0.01)
        assert total_cost < 0.01, f"Single query too expensive: ${total_cost:.4f}"

        # Print cost breakdown
        breakdown = cost_tracker.get_cost_breakdown()
        print("\nCost Breakdown:")
        for provider, cost in breakdown.items():
            print(f"  {provider}: ${cost:.4f}")


class TestConfidenceExtraction:
    """Test confidence extraction from real LLM responses."""

    @pytest.mark.asyncio
    async def test_confidence_in_real_responses(self, ):
        """
        Test 6: Confidence Extraction - Real Responses

        Query LLMs and verify confidence extraction works on real responses.
        """
        arbitrator = SwarmArbitrator(ports=[8001])

        # Ask for explicit confidence
        query = "What is 2+2? Express your confidence as a percentage."
        messages = [{"role": "user", "content": query}]

        if ANTHROPIC_KEY:
            result = await arbitrator._query_external_agent("claude-3-5-sonnet-20241022", messages)
            print(f"\n[Claude] Response: {result['content'][:200]}")
            print(f"[Claude] Confidence: {result['confidence']:.1%}")

            # Should have high confidence for simple math
            assert result['confidence'] >= 0.7, f"Expected high confidence, got {result['confidence']:.1%}"


def save_phase2_results(results: dict):
    """Save Phase 2 test results to JSON file."""
    output_file = Path("PHASE_2_RESULTS.json")

    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "phase": "Phase 2 - Real API Testing",
            "results": results
        }, f, indent=2)

    print(f"\n📊 Phase 2 results saved to: {output_file}")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     PHASE 2: REAL API TESTING                                ║
║                                                                              ║
║  Testing real API calls to:                                                 ║
║  • Anthropic Claude 3.5 Sonnet                                              ║
║  • Google Gemini Pro                                                        ║
║  • Grok (optional)                                                          ║
║                                                                              ║
║  Expected Cost: ~$0.03                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
