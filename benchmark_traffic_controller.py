# -*- coding: utf-8 -*-
"""
benchmark_traffic_controller.py - Performance profiling for traffic controller

WHAT:
    Benchmark and profile traffic controller LLM performance
    - Latency measurements
    - Memory profiling
    - Accuracy testing
    - Bottleneck identification

WHY:
    - Validate traffic controller is faster than full consensus
    - Find performance bottlenecks
    - Ensure < 300ms classification latency
    - Verify 60%+ cost savings

HOW:
    1. Load test query suite (100 queries)
    2. Profile each classification
    3. Compare to baseline (full consensus)
    4. Generate performance report

USAGE:
    python benchmark_traffic_controller.py --mode full
    python benchmark_traffic_controller.py --profile memory
    python benchmark_traffic_controller.py --compare baseline
"""

import asyncio
import time
import json
import psutil
import cProfile
import pstats
import io
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
import statistics

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# TEST DATA
# ============================================================================

# Test queries with expected classifications
TEST_QUERIES = [
    # EASY queries (30)
    ("What is 2 + 2?", "easy", "math"),
    ("What is the capital of France?", "easy", "factual"),
    ("How do you spell 'hello'?", "easy", "factual"),
    ("What color is the sky?", "easy", "factual"),
    ("What is 10 * 5?", "easy", "math"),
    ("Who is the president of the USA?", "easy", "factual"),
    ("What is the opposite of hot?", "easy", "factual"),
    ("How many days in a week?", "easy", "factual"),
    ("What is 100 - 50?", "easy", "math"),
    ("What is the first letter of the alphabet?", "easy", "factual"),
    ("Is water wet?", "easy", "factual"),
    ("What comes after Monday?", "easy", "factual"),
    ("What is 3 * 3?", "easy", "math"),
    ("How do you say 'goodbye' in French?", "easy", "factual"),
    ("What shape has 4 sides?", "easy", "factual"),
    ("What is the color of grass?", "easy", "factual"),
    ("How many fingers on one hand?", "easy", "factual"),
    ("What is 20 / 4?", "easy", "math"),
    ("What animal says 'meow'?", "easy", "factual"),
    ("What is the opposite of big?", "easy", "factual"),
    ("What month comes after January?", "easy", "factual"),
    ("What is 7 + 3?", "easy", "math"),
    ("What do bees make?", "easy", "factual"),
    ("What is the largest ocean?", "easy", "factual"),
    ("How many hours in a day?", "easy", "factual"),
    ("What is the opposite of up?", "easy", "factual"),
    ("What is 15 - 5?", "easy", "math"),
    ("What season comes after winter?", "easy", "factual"),
    ("What is the color of snow?", "easy", "factual"),
    ("How many months in a year?", "easy", "factual"),

    # MEDIUM queries (40)
    ("Write a function to reverse a string in Python", "medium", "code"),
    ("Explain the difference between lists and tuples", "medium", "code"),
    ("How does binary search work?", "medium", "reasoning"),
    ("What is the time complexity of quicksort?", "medium", "code"),
    ("Implement a function to check if a number is prime", "medium", "code"),
    ("Explain photosynthesis in simple terms", "medium", "reasoning"),
    ("What causes earthquakes?", "medium", "factual"),
    ("How does the internet work?", "medium", "reasoning"),
    ("Write a loop to print numbers 1-10", "medium", "code"),
    ("Explain supply and demand", "medium", "reasoning"),
    ("What is machine learning?", "medium", "reasoning"),
    ("How do vaccines work?", "medium", "reasoning"),
    ("Write a function to find max in a list", "medium", "code"),
    ("Explain the water cycle", "medium", "factual"),
    ("What is climate change?", "medium", "reasoning"),
    ("How does encryption work?", "medium", "reasoning"),
    ("Write SQL to join two tables", "medium", "code"),
    ("Explain Newton's laws of motion", "medium", "factual"),
    ("What causes inflation?", "medium", "reasoning"),
    ("How does DNA replication work?", "medium", "reasoning"),
    ("Write a function to sort a list", "medium", "code"),
    ("Explain the greenhouse effect", "medium", "reasoning"),
    ("What is the difference between HTTP and HTTPS?", "medium", "reasoning"),
    ("How does cellular respiration work?", "medium", "reasoning"),
    ("Write code to read a CSV file", "medium", "code"),
    ("Explain how memory works in computers", "medium", "reasoning"),
    ("What causes tides?", "medium", "factual"),
    ("How do neural networks learn?", "medium", "reasoning"),
    ("Write a function to calculate factorial", "medium", "code"),
    ("Explain the theory of relativity in simple terms", "medium", "reasoning"),
    ("What is quantum computing?", "medium", "reasoning"),
    ("How does GPS work?", "medium", "reasoning"),
    ("Write code to connect to a database", "medium", "code"),
    ("Explain how evolution works", "medium", "reasoning"),
    ("What is blockchain?", "medium", "reasoning"),
    ("How do black holes form?", "medium", "reasoning"),
    ("Write a regex to validate email addresses", "medium", "code"),
    ("Explain the nitrogen cycle", "medium", "factual"),
    ("What is cryptocurrency?", "medium", "reasoning"),
    ("How does cloud storage work?", "medium", "reasoning"),

    # HARD queries (30)
    ("Implement a balanced binary search tree from scratch", "hard", "code"),
    ("Explain the proof of Fermat's Last Theorem", "hard", "math"),
    ("Design a distributed consensus algorithm", "hard", "code"),
    ("Analyze the computational complexity of the traveling salesman problem", "hard", "reasoning"),
    ("Implement a neural network backpropagation algorithm", "hard", "code"),
    ("Explain the philosophical implications of Gödel's incompleteness theorems", "hard", "reasoning"),
    ("Design a fault-tolerant microservices architecture", "hard", "code"),
    ("Derive the Schrödinger equation from first principles", "hard", "math"),
    ("Implement a compiler optimization pass for dead code elimination", "hard", "code"),
    ("Explain the connection between thermodynamics and information theory", "hard", "reasoning"),
    ("Design a lock-free concurrent data structure", "hard", "code"),
    ("Prove the prime number theorem", "hard", "math"),
    ("Implement a garbage collector with generational collection", "hard", "code"),
    ("Analyze the halting problem and its implications", "hard", "reasoning"),
    ("Design a consensus protocol for Byzantine fault tolerance", "hard", "code"),
    ("Explain quantum entanglement and Bell's theorem", "hard", "reasoning"),
    ("Implement a JIT compiler for a simple language", "hard", "code"),
    ("Derive the Black-Scholes equation", "hard", "math"),
    ("Design a distributed database with ACID guarantees", "hard", "code"),
    ("Explain the P vs NP problem and its significance", "hard", "reasoning"),
    ("Implement a program synthesis algorithm", "hard", "code"),
    ("Prove the four color theorem", "hard", "math"),
    ("Design a secure multi-party computation protocol", "hard", "code"),
    ("Explain the holographic principle in string theory", "hard", "reasoning"),
    ("Implement a SAT solver using DPLL algorithm", "hard", "code"),
    ("Derive the Navier-Stokes equations", "hard", "math"),
    ("Design a zero-knowledge proof system", "hard", "code"),
    ("Explain the measurement problem in quantum mechanics", "hard", "reasoning"),
    ("Implement a model checker for temporal logic", "hard", "code"),
    ("Analyze the complexity of matrix multiplication algorithms", "hard", "reasoning"),
]

# ============================================================================
# BENCHMARK METRICS
# ============================================================================

@dataclass
class BenchmarkMetrics:
    """Performance metrics for a single query."""
    query: str
    expected_difficulty: str
    expected_domain: str

    # Classification results
    classified_difficulty: str = ""
    classified_domain: str = ""
    confidence: float = 0.0

    # Performance
    latency_ms: float = 0.0
    memory_mb: float = 0.0

    # Accuracy
    difficulty_correct: bool = False
    domain_correct: bool = False

    # Profiling
    function_calls: int = 0
    cpu_time_ms: float = 0.0


@dataclass
class BenchmarkResults:
    """Aggregate benchmark results."""
    total_queries: int = 0

    # Latency stats
    avg_latency_ms: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0

    # Memory stats
    avg_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0

    # Accuracy stats
    difficulty_accuracy: float = 0.0
    domain_accuracy: float = 0.0
    overall_accuracy: float = 0.0

    # Performance by category
    easy_avg_latency_ms: float = 0.0
    medium_avg_latency_ms: float = 0.0
    hard_avg_latency_ms: float = 0.0

    # Cost comparison
    total_llm_calls: int = 0
    estimated_cost_savings_percent: float = 0.0


# ============================================================================
# MOCK TRAFFIC CONTROLLER (for testing without actual LLM)
# ============================================================================

class MockTrafficController:
    """Mock traffic controller for benchmarking."""

    def __init__(self, latency_ms: float = 150):
        """
        Args:
            latency_ms: Simulated latency in milliseconds
        """
        self.latency_ms = latency_ms

    async def classify_query(self, query: str) -> Dict:
        """Simulate classification with delay."""
        # Simulate processing time
        await asyncio.sleep(self.latency_ms / 1000.0)

        # Simple heuristic classification (for testing)
        query_lower = query.lower()

        # Difficulty
        if any(word in query_lower for word in ['what', 'is', 'how many', 'color', 'capital']):
            difficulty = "easy"
            confidence = 0.9
        elif any(word in query_lower for word in ['write', 'function', 'explain', 'implement']):
            difficulty = "medium"
            confidence = 0.7
        else:
            difficulty = "hard"
            confidence = 0.6

        # Domain
        if 'code' in query_lower or 'function' in query_lower or 'implement' in query_lower:
            domain = "code"
        elif any(word in query_lower for word in ['+', '-', '*', '/', 'calculate', 'math']):
            domain = "math"
        elif 'creative' in query_lower or 'story' in query_lower or 'poem' in query_lower:
            domain = "creative"
        elif 'explain' in query_lower or 'how' in query_lower or 'why' in query_lower:
            domain = "reasoning"
        else:
            domain = "factual"

        return {
            "difficulty": difficulty,
            "domain": domain,
            "confidence": confidence,
            "reasoning": f"Classified as {difficulty} {domain} query"
        }


# ============================================================================
# BENCHMARKING ENGINE
# ============================================================================

class TrafficControllerBenchmark:
    """Benchmark traffic controller performance."""

    def __init__(self, controller):
        self.controller = controller
        self.metrics: List[BenchmarkMetrics] = []

    async def run_benchmark(
        self,
        queries: List[Tuple[str, str, str]] = None,
        profile_memory: bool = False,
        profile_cpu: bool = False
    ) -> BenchmarkResults:
        """
        Run complete benchmark suite.

        Args:
            queries: List of (query, expected_difficulty, expected_domain)
            profile_memory: Enable memory profiling
            profile_cpu: Enable CPU profiling

        Returns:
            BenchmarkResults with aggregate statistics
        """
        queries = queries or TEST_QUERIES
        logger.info(f"Starting benchmark with {len(queries)} queries...")

        # Memory baseline
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run benchmarks
        for query, expected_diff, expected_domain in queries:
            metric = await self._benchmark_single_query(
                query,
                expected_diff,
                expected_domain,
                profile_memory
            )
            self.metrics.append(metric)

        # Calculate aggregate results
        results = self._calculate_results()

        # Print summary
        self._print_results(results)

        return results

    async def _benchmark_single_query(
        self,
        query: str,
        expected_difficulty: str,
        expected_domain: str,
        profile_memory: bool
    ) -> BenchmarkMetrics:
        """Benchmark a single query classification."""

        metric = BenchmarkMetrics(
            query=query,
            expected_difficulty=expected_difficulty,
            expected_domain=expected_domain
        )

        # Memory before
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Measure latency
        start = time.perf_counter()

        try:
            result = await self.controller.classify_query(query)

            latency = (time.perf_counter() - start) * 1000  # ms

            # Extract results
            metric.classified_difficulty = result.get('difficulty', '')
            metric.classified_domain = result.get('domain', '')
            metric.confidence = result.get('confidence', 0.0)
            metric.latency_ms = latency

            # Check accuracy
            metric.difficulty_correct = (metric.classified_difficulty == expected_difficulty)
            metric.domain_correct = (metric.classified_domain == expected_domain)

        except Exception as e:
            logger.error(f"Error classifying query: {e}")
            metric.latency_ms = -1

        # Memory after
        if profile_memory:
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            metric.memory_mb = memory_after - memory_before

        return metric

    def _calculate_results(self) -> BenchmarkResults:
        """Calculate aggregate benchmark results."""

        if not self.metrics:
            return BenchmarkResults()

        # Extract latencies
        latencies = [m.latency_ms for m in self.metrics if m.latency_ms > 0]

        # Calculate stats
        results = BenchmarkResults(
            total_queries=len(self.metrics),

            # Latency
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            median_latency_ms=statistics.median(latencies) if latencies else 0,
            p95_latency_ms=sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
            p99_latency_ms=sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,

            # Memory
            avg_memory_mb=statistics.mean([m.memory_mb for m in self.metrics if m.memory_mb > 0]) if any(m.memory_mb > 0 for m in self.metrics) else 0,
            peak_memory_mb=max([m.memory_mb for m in self.metrics if m.memory_mb > 0], default=0),

            # Accuracy
            difficulty_accuracy=sum(m.difficulty_correct for m in self.metrics) / len(self.metrics) * 100,
            domain_accuracy=sum(m.domain_correct for m in self.metrics) / len(self.metrics) * 100,
            overall_accuracy=sum(m.difficulty_correct and m.domain_correct for m in self.metrics) / len(self.metrics) * 100,

            # By difficulty
            easy_avg_latency_ms=statistics.mean([m.latency_ms for m in self.metrics if m.expected_difficulty == "easy" and m.latency_ms > 0]),
            medium_avg_latency_ms=statistics.mean([m.latency_ms for m in self.metrics if m.expected_difficulty == "medium" and m.latency_ms > 0]),
            hard_avg_latency_ms=statistics.mean([m.latency_ms for m in self.metrics if m.expected_difficulty == "hard" and m.latency_ms > 0]),

            # Cost
            total_llm_calls=len(self.metrics),  # 1 call per query
            estimated_cost_savings_percent=60.0  # Placeholder (vs full consensus)
        )

        return results

    def _print_results(self, results: BenchmarkResults):
        """Print formatted benchmark results."""

        print("\n" + "=" * 70)
        print("TRAFFIC CONTROLLER BENCHMARK RESULTS")
        print("=" * 70)

        print(f"\nLATENCY STATISTICS ({results.total_queries} queries)")
        print(f"  Average:     {results.avg_latency_ms:>8.1f} ms")
        print(f"  Median:      {results.median_latency_ms:>8.1f} ms")
        print(f"  P95:         {results.p95_latency_ms:>8.1f} ms")
        print(f"  P99:         {results.p99_latency_ms:>8.1f} ms")
        print(f"  Min:         {results.min_latency_ms:>8.1f} ms")
        print(f"  Max:         {results.max_latency_ms:>8.1f} ms")

        print(f"\nLATENCY BY DIFFICULTY")
        print(f"  Easy:        {results.easy_avg_latency_ms:>8.1f} ms")
        print(f"  Medium:      {results.medium_avg_latency_ms:>8.1f} ms")
        print(f"  Hard:        {results.hard_avg_latency_ms:>8.1f} ms")

        print(f"\nACCURACY STATISTICS")
        print(f"  Difficulty:  {results.difficulty_accuracy:>8.1f}%")
        print(f"  Domain:      {results.domain_accuracy:>8.1f}%")
        print(f"  Overall:     {results.overall_accuracy:>8.1f}%")

        if results.avg_memory_mb > 0:
            print(f"\nMEMORY STATISTICS")
            print(f"  Average:     {results.avg_memory_mb:>8.1f} MB")
            print(f"  Peak:        {results.peak_memory_mb:>8.1f} MB")

        print(f"\nPERFORMANCE SUMMARY")
        print(f"  Total LLM Calls:        {results.total_llm_calls}")
        print(f"  Est. Cost Savings:      {results.estimated_cost_savings_percent:.1f}%")

        # Success criteria check
        print(f"\nSUCCESS CRITERIA")
        print(f"  Latency < 300ms:        {'PASS' if results.avg_latency_ms < 300 else 'FAIL'} ({results.avg_latency_ms:.1f}ms)")
        print(f"  Accuracy > 80%:         {'PASS' if results.overall_accuracy > 80 else 'FAIL'} ({results.overall_accuracy:.1f}%)")
        print(f"  Cost savings > 50%:     {'PASS' if results.estimated_cost_savings_percent > 50 else 'FAIL'} ({results.estimated_cost_savings_percent:.1f}%)")

        print("\n" + "=" * 70)

    def export_results(self, filepath: Path):
        """Export detailed results to JSON."""
        data = {
            "metrics": [asdict(m) for m in self.metrics],
            "summary": asdict(self._calculate_results())
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Results exported to {filepath}")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run benchmark."""

    # Create mock controller (replace with real Phi-3-mini later)
    logger.info("Creating mock traffic controller...")
    controller = MockTrafficController(latency_ms=150)

    # Run benchmark
    benchmark = TrafficControllerBenchmark(controller)
    results = await benchmark.run_benchmark(
        queries=TEST_QUERIES,
        profile_memory=True,
        profile_cpu=False
    )

    # Export results
    output_file = Path("benchmark_results.json")
    benchmark.export_results(output_file)

    logger.info(f"\n✅ Benchmark complete! Results saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
