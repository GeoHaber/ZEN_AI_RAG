#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Traffic Controller Test Suite
Tests all LLM configurations with random queries and comprehensive debugging
"""
import asyncio
import httpx
import json
import random
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import statistics

# Mock LLM server for testing
class MockLLMServer:
    """Simulates LLM endpoints for testing without real models."""

    def __init__(self, port: int, model_name: str, speed_ms: int = 100, quality: float = 0.8):
        self.port = port
        self.model_name = model_name
        self.speed_ms = speed_ms  # Simulated response time
        self.quality = quality  # Answer quality (0-1)
        self.call_count = 0

    async def handle_query(self, query: str) -> Dict:
        """Simulate LLM response."""
        self.call_count += 1

        # Simulate processing time
        await asyncio.sleep(self.speed_ms / 1000.0)

        # Classify query difficulty (simple heuristics)
        difficulty = self._classify_difficulty(query)
        domain = self._classify_domain(query)

        # Generate response based on port
        if self.port == 8020:
            # Traffic controller - return classification
            response = {
                "difficulty": difficulty,
                "domain": domain,
                "confidence": random.uniform(0.7, 0.95),
                "reasoning": f"Classified as {difficulty} {domain} query"
            }
            content = json.dumps(response)
        else:
            # Regular LLM - return answer
            content = f"[{self.model_name}] Answer to '{query[:50]}...': {self._generate_answer(query, difficulty)}"

        return {
            "content": content,
            "model": self.model_name,
            "time": self.speed_ms / 1000.0,
            "confidence": self.quality,
            "error": False
        }

    def _classify_difficulty(self, query: str) -> str:
        """Classify query difficulty."""
        query_lower = query.lower()

        # Easy: simple questions
        if any(word in query_lower for word in ['what is', 'define', 'who is', '2+2', 'capital of']):
            return "easy"

        # Hard: complex questions
        elif any(word in query_lower for word in ['prove', 'explain why', 'research', 'analyze', 'riemann']):
            return "hard"

        # Medium: everything else
        else:
            return "medium"

    def _classify_domain(self, query: str) -> str:
        """Classify query domain."""
        query_lower = query.lower()

        if any(word in query_lower for word in ['code', 'python', 'function', 'program']):
            return "code"
        elif any(word in query_lower for word in ['math', 'calculate', 'prove', 'equation']):
            return "math"
        elif any(word in query_lower for word in ['story', 'poem', 'creative', 'imagine']):
            return "creative"
        elif any(word in query_lower for word in ['why', 'how', 'explain', 'reason']):
            return "reasoning"
        else:
            return "factual"

    def _generate_answer(self, query: str, difficulty: str) -> str:
        """Generate mock answer."""
        if difficulty == "easy":
            return "Quick factual answer with high confidence."
        elif difficulty == "medium":
            return "Detailed explanation with code examples and reasoning. This requires some analysis."
        else:
            return "Complex answer requiring deep research and multi-step reasoning. This involves proofs, citations, and thorough analysis."


@dataclass
class TestResult:
    """Result of a single test."""
    config_name: str
    num_llms: int
    query: str
    expected_difficulty: str
    actual_route: str
    latency_ms: float
    llm_calls: int
    success: bool
    error_msg: str = ""


class TrafficControllerTester:
    """Automated test suite for traffic controller."""

    def __init__(self):
        self.mock_servers: Dict[int, MockLLMServer] = {}
        self.results: List[TestResult] = []

    def setup_mock_servers(self, config: Dict):
        """Setup mock LLM servers based on configuration."""
        self.mock_servers.clear()

        if config['num_llms'] >= 1:
            # Main LLM (fast)
            self.mock_servers[8001] = MockLLMServer(
                port=8001,
                model_name="Fast-LLM",
                speed_ms=100,
                quality=0.75
            )

        if config['num_llms'] >= 2:
            # Powerful LLM
            self.mock_servers[8005] = MockLLMServer(
                port=8005,
                model_name="Powerful-LLM",
                speed_ms=300,
                quality=0.95
            )

            # Traffic controller
            self.mock_servers[8020] = MockLLMServer(
                port=8020,
                model_name="Phi-3-mini",
                speed_ms=50,
                quality=0.88
            )

        if config['num_llms'] >= 3:
            # Third expert
            self.mock_servers[8006] = MockLLMServer(
                port=8006,
                model_name="Expert-3",
                speed_ms=200,
                quality=0.85
            )

    async def simulate_traffic_controller(
        self,
        query: str,
        num_llms: int
    ) -> Tuple[str, float, int]:
        """
        Simulate traffic controller routing.

        Returns:
            (route_taken, latency_ms, llm_calls)
        """
        start_time = time.time()
        llm_calls = 0

        if num_llms == 0:
            return "error", 0, 0

        elif num_llms == 1:
            # Direct routing
            await self.mock_servers[8001].handle_query(query)
            llm_calls = 1
            route = "direct"

        elif num_llms == 2:
            # Traffic controller mode
            # Step 1: Classify
            classifier_response = await self.mock_servers[8020].handle_query(query)
            llm_calls += 1

            classification = json.loads(classifier_response['content'])
            difficulty = classification['difficulty']
            confidence = classification['confidence']

            # Step 2: Route
            if difficulty == 'easy' and confidence > 0.8:
                # Fast LLM
                await self.mock_servers[8001].handle_query(query)
                llm_calls += 1
                route = "fast"
            elif difficulty == 'hard' or confidence < 0.5:
                # Powerful LLM
                await self.mock_servers[8005].handle_query(query)
                llm_calls += 1
                route = "powerful"
            else:
                # Both (verification)
                await asyncio.gather(
                    self.mock_servers[8001].handle_query(query),
                    self.mock_servers[8005].handle_query(query)
                )
                llm_calls += 2
                route = "verified"

        else:  # 3+ LLMs
            # Full consensus
            tasks = []
            for port in [8001, 8005, 8006]:
                if port in self.mock_servers:
                    tasks.append(self.mock_servers[port].handle_query(query))

            await asyncio.gather(*tasks)
            llm_calls = len(tasks)
            route = "consensus"

        latency_ms = (time.time() - start_time) * 1000
        return route, latency_ms, llm_calls

    async def test_configuration(
        self,
        config: Dict,
        test_queries: List[Tuple[str, str]]
    ):
        """Test a specific configuration with multiple queries."""
        print(f"\n{'='*70}")
        print(f"Testing Configuration: {config['name']}")
        print(f"  LLMs: {config['num_llms']}")
        print(f"  Queries: {len(test_queries)}")
        print(f"{'='*70}")

        self.setup_mock_servers(config)

        for query, expected_difficulty in test_queries:
            try:
                route, latency_ms, llm_calls = await self.simulate_traffic_controller(
                    query,
                    config['num_llms']
                )

                # Determine success
                success = True
                error_msg = ""

                # Validation rules
                if config['num_llms'] == 1:
                    if route != "direct" or llm_calls != 1:
                        success = False
                        error_msg = f"Expected direct routing with 1 call, got {route} with {llm_calls} calls"

                elif config['num_llms'] == 2:
                    if expected_difficulty == "easy" and route not in ["fast", "verified"]:
                        success = False
                        error_msg = f"Easy query should use fast or verified, got {route}"
                    elif expected_difficulty == "hard" and route not in ["powerful", "verified"]:
                        success = False
                        error_msg = f"Hard query should use powerful or verified, got {route}"

                # Record result
                result = TestResult(
                    config_name=config['name'],
                    num_llms=config['num_llms'],
                    query=query[:50] + "...",
                    expected_difficulty=expected_difficulty,
                    actual_route=route,
                    latency_ms=latency_ms,
                    llm_calls=llm_calls,
                    success=success,
                    error_msg=error_msg
                )

                self.results.append(result)

                # Print result
                status = "PASS" if success else "FAIL"
                print(f"  [{status}] {expected_difficulty:6s} -> {route:10s} ({latency_ms:6.1f}ms, {llm_calls} calls)")
                if not success:
                    print(f"        ERROR: {error_msg}")

            except Exception as e:
                print(f"  [ERROR] {query[:50]}... - {str(e)}")
                self.results.append(TestResult(
                    config_name=config['name'],
                    num_llms=config['num_llms'],
                    query=query[:50] + "...",
                    expected_difficulty=expected_difficulty,
                    actual_route="error",
                    latency_ms=0,
                    llm_calls=0,
                    success=False,
                    error_msg=str(e)
                ))

    def print_summary(self):
        """Print comprehensive test summary."""
        print(f"\n\n{'='*70}")
        print("TEST SUMMARY")
        print(f"{'='*70}")

        # Overall stats
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total_tests - passed
        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0

        print(f"\nOverall Results:")
        print(f"  Total Tests:  {total_tests}")
        print(f"  Passed:       {passed} ({pass_rate:.1f}%)")
        print(f"  Failed:       {failed}")

        # Performance by configuration
        print(f"\nPerformance by Configuration:")
        configs = set(r.config_name for r in self.results)

        for config in sorted(configs):
            config_results = [r for r in self.results if r.config_name == config]
            avg_latency = statistics.mean([r.latency_ms for r in config_results])
            avg_calls = statistics.mean([r.llm_calls for r in config_results])
            config_pass_rate = sum(1 for r in config_results if r.success) / len(config_results) * 100

            print(f"\n  {config}:")
            print(f"    Pass Rate:    {config_pass_rate:.1f}%")
            print(f"    Avg Latency:  {avg_latency:.1f}ms")
            print(f"    Avg LLM Calls: {avg_calls:.1f}")

        # Latency statistics
        latencies = [r.latency_ms for r in self.results if r.success]
        if latencies:
            print(f"\nLatency Statistics:")
            print(f"  Average:  {statistics.mean(latencies):6.1f}ms")
            print(f"  Median:   {statistics.median(latencies):6.1f}ms")
            print(f"  Min:      {min(latencies):6.1f}ms")
            print(f"  Max:      {max(latencies):6.1f}ms")

        # LLM call efficiency
        calls_by_config = {}
        for r in self.results:
            if r.config_name not in calls_by_config:
                calls_by_config[r.config_name] = []
            calls_by_config[r.config_name].append(r.llm_calls)

        print(f"\nLLM Call Efficiency:")
        for config, calls in calls_by_config.items():
            avg = statistics.mean(calls)
            print(f"  {config:20s}: {avg:.1f} calls/query")

        # Cost savings (2-LLM vs 3-LLM)
        two_llm_results = [r for r in self.results if r.num_llms == 2]
        three_llm_results = [r for r in self.results if r.num_llms == 3]

        if two_llm_results and three_llm_results:
            two_llm_avg_calls = statistics.mean([r.llm_calls for r in two_llm_results])
            three_llm_avg_calls = statistics.mean([r.llm_calls for r in three_llm_results])
            savings = (three_llm_avg_calls - two_llm_avg_calls) / three_llm_avg_calls * 100

            print(f"\nCost Savings (2-LLM vs 3-LLM):")
            print(f"  2-LLM avg:    {two_llm_avg_calls:.1f} calls")
            print(f"  3-LLM avg:    {three_llm_avg_calls:.1f} calls")
            print(f"  Savings:      {savings:.1f}%")

        # Failures breakdown
        if failed > 0:
            print(f"\nFailures Breakdown:")
            failure_reasons = {}
            for r in self.results:
                if not r.success:
                    reason = r.error_msg or "Unknown"
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

            for reason, count in sorted(failure_reasons.items(), key=lambda x: -x[1]):
                print(f"  {count:3d}x: {reason}")

        # Success criteria validation
        print(f"\nSuccess Criteria Validation:")

        # Check latency < 300ms
        if latencies:
            avg_latency = statistics.mean(latencies)
            latency_check = "PASS" if avg_latency < 300 else "FAIL"
            print(f"  Avg Latency < 300ms:    {latency_check} ({avg_latency:.1f}ms)")

        # Check pass rate > 90%
        pass_check = "PASS" if pass_rate > 90 else "FAIL"
        print(f"  Pass Rate > 90%:        {pass_check} ({pass_rate:.1f}%)")

        # Check cost savings
        if two_llm_results and three_llm_results:
            savings_check = "PASS" if savings > 50 else "FAIL"
            print(f"  Cost Savings > 50%:     {savings_check} ({savings:.1f}%)")

        print(f"\n{'='*70}")

    def export_results(self, filepath: Path):
        """Export results to JSON."""
        data = {
            "results": [asdict(r) for r in self.results],
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.success),
                "failed": sum(1 for r in self.results if not r.success),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        print(f"\nResults exported to: {filepath}")


async def main():
    """Run automated test suite."""
    print("="*70)
    print("AUTOMATED TRAFFIC CONTROLLER TEST SUITE")
    print("="*70)

    tester = TrafficControllerTester()

    # Test configurations
    configurations = [
        {
            "name": "0-LLM (Error Case)",
            "num_llms": 0
        },
        {
            "name": "1-LLM (Direct)",
            "num_llms": 1
        },
        {
            "name": "2-LLM (Traffic Controller)",
            "num_llms": 2
        },
        {
            "name": "3-LLM (Full Consensus)",
            "num_llms": 3
        }
    ]

    # Test queries with expected difficulty
    test_queries = [
        # Easy queries
        ("What is 2+2?", "easy"),
        ("Define photosynthesis", "easy"),
        ("What is the capital of France?", "easy"),
        ("Who wrote Romeo and Juliet?", "easy"),
        ("What year did World War 2 end?", "easy"),

        # Medium queries
        ("Write a Python function to check if a number is prime", "medium"),
        ("Explain how neural networks work", "medium"),
        ("What are the pros and cons of React vs Vue?", "medium"),
        ("How does garbage collection work in Java?", "medium"),
        ("Analyze the time complexity of quicksort", "medium"),

        # Hard queries
        ("Prove the Riemann Hypothesis", "hard"),
        ("Explain why the Monty Hall problem is counterintuitive", "hard"),
        ("Research the impact of quantum computing on cryptography", "hard"),
        ("Analyze the philosophical implications of AI consciousness", "hard"),
        ("Prove why P vs NP is an open problem", "hard"),
    ]

    # Randomly shuffle queries for variety
    random.shuffle(test_queries)

    # Run tests for each configuration
    for config in configurations:
        await tester.test_configuration(config, test_queries)

    # Print summary
    tester.print_summary()

    # Export results
    output_file = Path("test_traffic_controller_results.json")
    tester.export_results(output_file)

    print("\nTest suite completed!")

    # Return success/failure
    total = len(tester.results)
    passed = sum(1 for r in tester.results if r.success)
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
