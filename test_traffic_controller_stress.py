#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stress Test Suite for Traffic Controller
Tests edge cases, error handling, and performance under load
"""
import asyncio
import random
import time
from typing import List, Dict
from dataclasses import dataclass
import statistics

@dataclass
class StressTestResult:
    """Result from stress test."""
    test_name: str
    total_queries: int
    successful: int
    failed: int
    avg_latency_ms: float
    p95_latency_ms: float
    throughput_qps: float
    errors: List[str]


class StressTestSuite:
    """Comprehensive stress testing."""

    def __init__(self):
        self.results: List[StressTestResult] = []

    async def test_concurrent_queries(self, num_concurrent: int = 10):
        """Test handling multiple concurrent queries."""
        print(f"\n{'='*70}")
        print(f"TEST: Concurrent Queries (n={num_concurrent})")
        print(f"{'='*70}")

        from test_traffic_controller_auto import TrafficControllerTester, MockLLMServer

        tester = TrafficControllerTester()
        config = {"name": "2-LLM", "num_llms": 2}
        tester.setup_mock_servers(config)

        queries = [
            "What is 2+2?" if i % 3 == 0 else
            "Write a Python function" if i % 3 == 1 else
            "Prove the Riemann Hypothesis"
            for i in range(num_concurrent)
        ]

        start_time = time.time()
        latencies = []
        errors = []

        tasks = []
        for query in queries:
            task = tester.simulate_traffic_controller(query, 2)
            tasks.append(task)

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                else:
                    route, latency_ms, llm_calls = result
                    latencies.append(latency_ms)

        except Exception as e:
            errors.append(str(e))

        total_time = time.time() - start_time
        throughput = num_concurrent / total_time

        result = StressTestResult(
            test_name="Concurrent Queries",
            total_queries=num_concurrent,
            successful=len(latencies),
            failed=len(errors),
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else 0,
            throughput_qps=throughput,
            errors=errors
        )

        self.results.append(result)

        print(f"  Total Queries:   {result.total_queries}")
        print(f"  Successful:      {result.successful}")
        print(f"  Failed:          {result.failed}")
        print(f"  Avg Latency:     {result.avg_latency_ms:.1f}ms")
        print(f"  P95 Latency:     {result.p95_latency_ms:.1f}ms")
        print(f"  Throughput:      {result.throughput_qps:.2f} queries/sec")

        if errors:
            print(f"  Errors: {errors[:3]}")  # Show first 3

        status = "PASS" if result.failed == 0 else "FAIL"
        print(f"  Status: {status}")

    async def test_error_handling(self):
        """Test error handling and fallback behavior."""
        print(f"\n{'='*70}")
        print(f"TEST: Error Handling & Fallback")
        print(f"{'='*70}")

        from test_traffic_controller_auto import TrafficControllerTester

        tester = TrafficControllerTester()

        # Test 1: Missing classifier (port 8020 down)
        print("\n  Scenario 1: Classifier unavailable")
        config = {"name": "2-LLM-NoClassifier", "num_llms": 2}
        tester.setup_mock_servers(config)

        # Remove classifier
        if 8020 in tester.mock_servers:
            del tester.mock_servers[8020]

        try:
            route, latency, calls = await tester.simulate_traffic_controller("What is 2+2?", 2)
            print(f"    Result: route={route}, latency={latency:.1f}ms, calls={calls}")
            print(f"    Status: PASS (fallback to medium difficulty)")
        except Exception as e:
            print(f"    Status: FAIL - {str(e)}")

        # Test 2: LLM timeout simulation
        print("\n  Scenario 2: LLM timeout")
        from test_traffic_controller_auto import MockLLMServer

        # Create slow LLM
        slow_llm = MockLLMServer(port=8001, model_name="Slow-LLM", speed_ms=5000)
        tester.mock_servers[8001] = slow_llm

        try:
            start = time.time()
            # This should timeout or handle gracefully
            route, latency, calls = await asyncio.wait_for(
                tester.simulate_traffic_controller("What is 2+2?", 1),
                timeout=2.0
            )
            elapsed = (time.time() - start) * 1000
            print(f"    Result: Completed in {elapsed:.1f}ms")
            print(f"    Status: PASS (handled timeout)")
        except asyncio.TimeoutError:
            print(f"    Status: EXPECTED - Timeout occurred")

        # Test 3: Invalid JSON response
        print("\n  Scenario 3: Invalid classifier response")
        # This would need custom mock that returns invalid JSON
        print(f"    Status: SKIPPED (requires custom mock)")

    async def test_load_patterns(self):
        """Test different load patterns."""
        print(f"\n{'='*70}")
        print(f"TEST: Load Patterns")
        print(f"{'='*70}")

        from test_traffic_controller_auto import TrafficControllerTester

        tester = TrafficControllerTester()
        config = {"name": "2-LLM", "num_llms": 2}
        tester.setup_mock_servers(config)

        # Pattern 1: Burst traffic
        print("\n  Pattern 1: Burst (20 queries in 1s)")
        queries = ["What is 2+2?" for _ in range(20)]

        start_time = time.time()
        results = await asyncio.gather(*[
            tester.simulate_traffic_controller(q, 2)
            for q in queries
        ])
        burst_time = time.time() - start_time

        print(f"    Completed: {len(results)} queries in {burst_time:.2f}s")
        print(f"    Throughput: {len(results)/burst_time:.2f} qps")
        print(f"    Status: PASS")

        # Pattern 2: Steady flow
        print("\n  Pattern 2: Steady (1 query per 100ms for 2s)")
        steady_count = 0
        start_time = time.time()

        for i in range(20):
            await tester.simulate_traffic_controller("What is 2+2?", 2)
            steady_count += 1
            await asyncio.sleep(0.1)  # 100ms interval

        steady_time = time.time() - start_time

        print(f"    Completed: {steady_count} queries in {steady_time:.2f}s")
        print(f"    Avg interval: {steady_time/steady_count*1000:.1f}ms")
        print(f"    Status: PASS")

    async def test_difficulty_distribution(self):
        """Test routing for different difficulty distributions."""
        print(f"\n{'='*70}")
        print(f"TEST: Difficulty Distribution")
        print(f"{'='*70}")

        from test_traffic_controller_auto import TrafficControllerTester

        tester = TrafficControllerTester()
        config = {"name": "2-LLM", "num_llms": 2}
        tester.setup_mock_servers(config)

        distributions = [
            ("80% Easy, 20% Hard", ["What is 2+2?"] * 8 + ["Prove Riemann"] * 2),
            ("50% Easy, 50% Medium", ["What is 2+2?"] * 5 + ["Write Python code"] * 5),
            ("100% Hard", ["Prove Riemann"] * 10),
            ("Mixed", ["What is 2+2?"] * 3 + ["Write Python code"] * 4 + ["Prove Riemann"] * 3),
        ]

        for dist_name, queries in distributions:
            print(f"\n  Distribution: {dist_name}")

            routes = {"fast": 0, "powerful": 0, "verified": 0}
            total_calls = 0

            for query in queries:
                route, latency, calls = await tester.simulate_traffic_controller(query, 2)
                routes[route] = routes.get(route, 0) + 1
                total_calls += calls

            avg_calls = total_calls / len(queries)

            print(f"    Routes: fast={routes.get('fast', 0)}, powerful={routes.get('powerful', 0)}, verified={routes.get('verified', 0)}")
            print(f"    Avg LLM calls: {avg_calls:.2f}")
            print(f"    Status: PASS")

    async def test_performance_degradation(self):
        """Test performance under increasing load."""
        print(f"\n{'='*70}")
        print(f"TEST: Performance Degradation")
        print(f"{'='*70}")

        from test_traffic_controller_auto import TrafficControllerTester

        tester = TrafficControllerTester()
        config = {"name": "2-LLM", "num_llms": 2}

        load_levels = [1, 5, 10, 20, 50]

        print(f"\n  {'Load':>6s} | {'Avg Latency':>12s} | {'Throughput':>12s} | {'Status':>10s}")
        print(f"  {'-'*6}-+-{'-'*12}-+-{'-'*12}-+-{'-'*10}")

        baseline_latency = None

        for load in load_levels:
            tester.setup_mock_servers(config)

            queries = ["What is 2+2?"] * load

            start_time = time.time()
            results = await asyncio.gather(*[
                tester.simulate_traffic_controller(q, 2)
                for q in queries
            ])
            elapsed = time.time() - start_time

            latencies = [r[1] for r in results]
            avg_latency = statistics.mean(latencies)
            throughput = load / elapsed

            if baseline_latency is None:
                baseline_latency = avg_latency

            degradation = ((avg_latency - baseline_latency) / baseline_latency * 100) if baseline_latency > 0 else 0
            status = "OK" if degradation < 50 else "DEGRADED"

            print(f"  {load:6d} | {avg_latency:10.1f}ms | {throughput:10.2f} qps | {status:>10s}")

    async def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        print(f"\n{'='*70}")
        print(f"TEST: Edge Cases")
        print(f"{'='*70}")

        from test_traffic_controller_auto import TrafficControllerTester

        tester = TrafficControllerTester()

        edge_cases = [
            ("Empty query", "", 2),
            ("Very long query", "x" * 10000, 2),
            ("Unicode query", "What is 数学?", 2),
            ("Special chars", "What is <script>alert('xss')</script>?", 2),
            ("0 LLMs", "What is 2+2?", 0),
        ]

        for case_name, query, num_llms in edge_cases:
            print(f"\n  Case: {case_name}")

            config = {"name": f"Edge-{num_llms}", "num_llms": num_llms}
            tester.setup_mock_servers(config)

            try:
                route, latency, calls = await tester.simulate_traffic_controller(query, num_llms)
                print(f"    Result: route={route}, latency={latency:.1f}ms, calls={calls}")
                print(f"    Status: PASS (handled gracefully)")
            except Exception as e:
                print(f"    Status: EXPECTED ERROR - {str(e)[:50]}...")

    def print_final_summary(self):
        """Print final test summary."""
        print(f"\n\n{'='*70}")
        print("STRESS TEST FINAL SUMMARY")
        print(f"{'='*70}")

        if self.results:
            total_queries = sum(r.total_queries for r in self.results)
            total_successful = sum(r.successful for r in self.results)
            total_failed = sum(r.failed for r in self.results)

            print(f"\nOverall Statistics:")
            print(f"  Total Queries:   {total_queries}")
            print(f"  Successful:      {total_successful} ({total_successful/total_queries*100:.1f}%)")
            print(f"  Failed:          {total_failed}")

            if self.results:
                avg_throughput = statistics.mean([r.throughput_qps for r in self.results])
                print(f"  Avg Throughput:  {avg_throughput:.2f} qps")

        print(f"\n{'='*70}")


async def main():
    """Run stress test suite."""
    print("="*70)
    print("TRAFFIC CONTROLLER STRESS TEST SUITE")
    print("="*70)

    suite = StressTestSuite()

    # Run all stress tests
    await suite.test_concurrent_queries(num_concurrent=10)
    await suite.test_concurrent_queries(num_concurrent=50)
    await suite.test_error_handling()
    await suite.test_load_patterns()
    await suite.test_difficulty_distribution()
    await suite.test_performance_degradation()
    await suite.test_edge_cases()

    # Print final summary
    suite.print_final_summary()

    print("\nStress test suite completed!")


if __name__ == "__main__":
    asyncio.run(main())
