"""
Benchmark Framework for Python vs Rust Comparison
Measures performance across multiple dimensions:
- Execution time (latency, throughput)
- Memory usage (RSS, peak)
- Resource efficiency
"""

import time
import json
import psutil
import os
from pathlib import Path
from typing import List, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class BenchmarkResult:
    """Single benchmark run result"""

    name: str
    implementation: str  # "python" or "rust"
    duration_ms: float
    memory_peak_mb: float
    memory_avg_mb: float
    iterations: int
    timestamp: str
    payload_size: int = 0
    success: bool = True
    error: str = None


@dataclass
class ComparisonReport:
    """Comparison between Python and Rust implementations"""

    module: str
    test_name: str
    python_result: BenchmarkResult
    rust_result: BenchmarkResult
    speedup: float  # rust_time / python_time
    memory_delta_pct: float  # (rust - python) / python * 100


class BenchmarkHarness:
    """Harness for comparing Python vs Rust implementations"""

    def __init__(self, output_dir: str = "Rustified/benchmarks"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[BenchmarkResult] = []
        self.process = psutil.Process(os.getpid())

    def measure_memory(self) -> Tuple[float, float]:
        """Get current memory usage in MB"""
        try:
            mem_info = self.process.memory_info()
            return mem_info.rss / 1024 / 1024, mem_info.vms / 1024 / 1024
        except Exception:
            return 0.0, 0.0

    def benchmark_function(
        self,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        iterations: int = 1,
        warmup: int = 1,
        payload_size: int = 0,
    ) -> BenchmarkResult:
        """
        Benchmark a single function

        Args:
            name: Benchmark name
            func: Function to benchmark
            args: Positional arguments
            kwargs: Keyword arguments
            iterations: Number of iterations
            warmup: Warmup iterations
            payload_size: Size of input payload (for tracking)

        Returns:
            BenchmarkResult with measurements
        """
        if kwargs is None:
            kwargs = {}

        # Warmup phase
        for _ in range(warmup):
            try:
                func(*args, **kwargs)
            except Exception as e:
                return BenchmarkResult(
                    name=name,
                    implementation="unknown",
                    duration_ms=0,
                    memory_peak_mb=0,
                    memory_avg_mb=0,
                    iterations=0,
                    timestamp=datetime.now().isoformat(),
                    payload_size=payload_size,
                    success=False,
                    error=str(e),
                )

        # Measurement phase
        times = []
        memory_peak = 0
        memory_samples = []

        for _ in range(iterations):
            mem_before, _ = self.measure_memory()

            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                return BenchmarkResult(
                    name=name,
                    implementation="unknown",
                    duration_ms=0,
                    memory_peak_mb=0,
                    memory_avg_mb=0,
                    iterations=0,
                    timestamp=datetime.now().isoformat(),
                    payload_size=payload_size,
                    success=False,
                    error=str(e),
                )

            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # Convert to ms

            mem_after, _ = self.measure_memory()
            mem_delta = mem_after - mem_before
            memory_samples.append(mem_delta)
            memory_peak = max(memory_peak, mem_delta)

        avg_time = sum(times) / len(times)
        avg_memory = sum(memory_samples) / len(memory_samples) if memory_samples else 0

        result = BenchmarkResult(
            name=name,
            implementation="unknown",
            duration_ms=avg_time,
            memory_peak_mb=memory_peak,
            memory_avg_mb=avg_memory,
            iterations=iterations,
            timestamp=datetime.now().isoformat(),
            payload_size=payload_size,
            success=True,
        )

        self.results.append(result)
        return result

    def compare_implementations(
        self,
        module_name: str,
        test_name: str,
        python_func: Callable,
        rust_func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        iterations: int = 10,
    ) -> ComparisonReport:
        """
        Compare Python vs Rust implementation of same function

        Returns:
            ComparisonReport with speedup metrics
        """
        print(f"\n📊 Benchmarking {module_name}/{test_name}...")
        print("-" * 80)

        # Benchmark Python
        print("  🐍 Python implementation...", end=" ", flush=True)
        py_result = self.benchmark_function(
            f"{module_name}/{test_name}/python",
            python_func,
            args=args,
            kwargs=kwargs or {},
            iterations=iterations,
        )
        print(f"✓ {py_result.duration_ms:.2f}ms")
        py_result.implementation = "python"

        # Benchmark Rust (placeholder - will use actual Rust binding)
        print("  🦀 Rust implementation...   ", end=" ", flush=True)
        rust_result = self.benchmark_function(
            f"{module_name}/{test_name}/rust",
            rust_func,
            args=args,
            kwargs=kwargs or {},
            iterations=iterations,
        )
        print(f"✓ {rust_result.duration_ms:.2f}ms")
        rust_result.implementation = "rust"

        # Calculate comparison
        speedup = py_result.duration_ms / rust_result.duration_ms if rust_result.duration_ms > 0 else 0
        memory_delta = (rust_result.memory_avg_mb - py_result.memory_avg_mb) / max(py_result.memory_avg_mb, 0.1) * 100

        report = ComparisonReport(
            module=module_name,
            test_name=test_name,
            python_result=py_result,
            rust_result=rust_result,
            speedup=speedup,
            memory_delta_pct=memory_delta,
        )

        # Print summary
        print("\n  📈 Results:")
        print(f"     Speedup: {speedup:.2f}x {'✨' if speedup > 1.5 else '⚠️ ' if speedup < 1 else '👍'}")
        print(f"     Memory Delta: {memory_delta:+.1f}%")
        print(f"     Python: {py_result.duration_ms:.2f}ms ({py_result.memory_avg_mb:.2f}MB)")
        print(f"     Rust:   {rust_result.duration_ms:.2f}ms ({rust_result.memory_avg_mb:.2f}MB)")

        return report

    def save_results(self, filename: str = "benchmark_results.json"):
        """Save all results to JSON file"""
        results_list = [
            {
                **asdict(result),
                "implementation": result.implementation,
            }
            for result in self.results
        ]

        output_path = self.output_dir / filename
        with open(output_path, "w") as f:
            json.dump(results_list, f, indent=2)

        print(f"\n💾 Results saved to {output_path}")
        return output_path

    def generate_report(self, filename: str = "benchmark_report.json"):
        """Generate comprehensive benchmark report"""
        # Group results by module and implementation
        comparisons = {}

        for result in self.results:
            # Parse module name
            if "/" in result.name:
                module = result.name.split("/")[0]
                test = result.name.split("/")[1]
                impl = result.implementation

                key = f"{module}/{test}"
                if key not in comparisons:
                    comparisons[key] = {}
                comparisons[key][impl] = result

        # Generate comparison data
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_benchmarks": len(self.results),
            "summary": {
                "python_total_time_ms": sum(r.duration_ms for r in self.results if r.implementation == "python"),
                "rust_total_time_ms": sum(r.duration_ms for r in self.results if r.implementation == "rust"),
            },
            "comparisons": {},
        }

        for test_name, impls in comparisons.items():
            if "python" in impls and "rust" in impls:
                py = impls["python"]
                rs = impls["rust"]
                speedup = py.duration_ms / rs.duration_ms if rs.duration_ms > 0 else 0
                memory_delta = (rs.memory_avg_mb - py.memory_avg_mb) / max(py.memory_avg_mb, 0.1) * 100

                report_data["comparisons"][test_name] = {
                    "python": asdict(py),
                    "rust": asdict(rs),
                    "speedup": speedup,
                    "memory_delta_pct": memory_delta,
                    "winner": "rust" if speedup > 1 else "python",
                }

        # Calculate summary stats
        speedups = [c["speedup"] for c in report_data["comparisons"].values() if c["speedup"] > 0]
        if speedups:
            report_data["summary"]["average_speedup"] = sum(speedups) / len(speedups)
            report_data["summary"]["max_speedup"] = max(speedups)
            report_data["summary"]["min_speedup"] = min(speedups)

        output_path = self.output_dir / filename
        with open(output_path, "w") as f:
            json.dump(report_data, f, indent=2)

        print(f"📊 Report saved to {output_path}")
        return report_data


# Example usage for testing framework
if __name__ == "__main__":
    harness = BenchmarkHarness()

    # Example: Simple RAG service mock
    def mock_python_rag_query(query: str, num_results: int = 10):
        """Simulated Python RAG query (slow)"""
        # Simulate vector search overhead
        import time

        time.sleep(0.05)  # 50ms overhead
        return {"results": [{"doc": i, "score": 0.9} for i in range(num_results)]}

    def mock_rust_rag_query(query: str, num_results: int = 10):
        """Simulated Rust RAG query (fast)"""
        # Simulate optimized implementation
        import time

        time.sleep(0.012)  # 12ms overhead
        return {"results": [{"doc": i, "score": 0.9} for i in range(num_results)]}

    # Run comparison
    print("=" * 80)
    print("RAG_RAT BENCHMARK FRAMEWORK - Test Run")
    print("=" * 80)

    comparison = harness.compare_implementations(
        module_name="Core/services",
        test_name="rag_query_throughput",
        python_func=mock_python_rag_query,
        rust_func=mock_rust_rag_query,
        args=("What is machine learning?",),
        kwargs={"num_results": 10},
        iterations=5,
    )

    # Save results
    harness.save_results("sample_benchmark_results.json")
    report = harness.generate_report("sample_benchmark_report.json")

    print("\n" + "=" * 80)
    print("Export Comparison Data:")
    print("=" * 80)
    for test, comparison in report["comparisons"].items():
        print(f"{test:50} | Speedup: {comparison['speedup']:.2f}x | 🏆 {comparison['winner']}")
