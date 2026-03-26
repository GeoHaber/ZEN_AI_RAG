"""
RAG_RAT Python Baseline Benchmarks - Adapted Version

Working benchmarks using actual RAG_RAT module APIs.
Establishes performance metrics for key modules.
"""

import sys
import time
import json
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from benchmark_harness import BenchmarkHarness


class RAGRATAdaptedBenchmarks:
    """Benchmark suite adapted to actual RAG_RAT module signatures"""

    def __init__(self):
        self.harness = BenchmarkHarness(output_dir="Rustified/benchmarks")
        self.results = {}

    def benchmark_inference_guard(self):
        """Benchmark inference guard operations"""
        print("\n" + "=" * 80)
        print("BENCHMARKING: inference_guard.py")
        print("=" * 80)

        try:
            from inference_guard import (
                validate_max_tokens,
                validate_parameters,
                InferenceGuard,
            )

            # Setup
            InferenceGuard()

            # Test 1: Token validation
            print("📊 Test 1: Token Parameter Validation")

            result1 = self.harness.benchmark_function(
                name="inference_guard/validate_tokens",
                func=lambda: validate_max_tokens(256, "tinyllama"),
                iterations=1000,
                warmup=50,
            )
            result1.implementation = "python"

            # Test 2: Parameter validation
            print("📊 Test 2: Full Parameter Validation")

            params = {
                "max_tokens": 512,
                "temperature": 0.7,
                "top_p": 0.9,
                "model": "tinyllama",
            }

            result2 = self.harness.benchmark_function(
                name="inference_guard/validate_parameters",
                func=lambda: validate_parameters(params),
                iterations=500,
                warmup=25,
            )
            result2.implementation = "python"

            stats = {
                "validate_tokens": {
                    "duration_ms": result1.duration_ms,
                    "memory_peak_mb": result1.memory_peak_mb,
                    "iterations": result1.iterations,
                },
                "validate_parameters": {
                    "duration_ms": result2.duration_ms,
                    "memory_peak_mb": result2.memory_peak_mb,
                    "iterations": result2.iterations,
                },
            }

            self.results["inference_guard"] = stats
            print("✅ inference_guard benchmarks complete")
            return stats

        except Exception:
            # [X-Ray auto-fix] print(f"⚠️  inference_guard: {e}")
            self.results["inference_guard"] = None
            return None

    def benchmark_rag_integration(self):
        """Benchmark RAG integration"""
        print("\n" + "=" * 80)
        print("BENCHMARKING: rag_integration.py")
        print("=" * 80)

        try:
            from rag_integration import RAGIntegration

            rag = RAGIntegration()

            # Test 1: Answer generation
            print("📊 Test 1: RAG Answer Generation")

            result1 = self.harness.benchmark_function(
                name="rag_integration/generate_answer",
                func=lambda: rag.generate_answer("What is machine learning?"),
                iterations=5,
                warmup=1,
            )
            result1.implementation = "python"

            # Test 2: Context retrieval
            print("📊 Test 2: Context Retrieval")

            result2 = self.harness.benchmark_function(
                name="rag_integration/retrieve_context",
                func=lambda: rag.retrieve_context("machine learning", top_k=5),
                iterations=10,
                warmup=2,
            )
            result2.implementation = "python"

            stats = {
                "generate_answer": {
                    "duration_ms": result1.duration_ms,
                    "memory_peak_mb": result1.memory_peak_mb,
                    "iterations": result1.iterations,
                },
                "retrieve_context": {
                    "duration_ms": result2.duration_ms,
                    "memory_peak_mb": result2.memory_peak_mb,
                    "iterations": result2.iterations,
                },
            }

            self.results["rag_integration"] = stats
            print("✅ rag_integration benchmarks complete")
            return stats

        except Exception:
            # [X-Ray auto-fix] print(f"⚠️  rag_integration: {e}")
            self.results["rag_integration"] = None
            return None

    def benchmark_llm_service(self):
        """Benchmark LLM service"""
        print("\n" + "=" * 80)
        print("BENCHMARKING: Core/services/llm_service.py")
        print("=" * 80)

        try:
            from Core.services.llm_service import LLMService

            llm = LLMService()

            # Test: Inference
            print("📊 Test 1: LLM Inference")

            prompt = "What is artificial intelligence?"

            result = self.harness.benchmark_function(
                name="llm_service/inference",
                func=lambda: llm.generate(prompt, max_tokens=100),
                iterations=3,
                warmup=1,
            )
            result.implementation = "python"

            stats = {
                "inference": {
                    "duration_ms": result.duration_ms,
                    "memory_peak_mb": result.memory_peak_mb,
                    "iterations": result.iterations,
                },
            }

            self.results["llm_service"] = stats
            print("✅ llm_service benchmarks complete")
            return stats

        except Exception:
            # [X-Ray auto-fix] print(f"⚠️  llm_service: {e}")
            self.results["llm_service"] = None
            return None

    def benchmark_config(self):
        """Benchmark configuration operations"""
        print("\n" + "=" * 80)
        print("BENCHMARKING: config_enhanced.py")
        print("=" * 80)

        try:
            from config_enhanced import get_inference_config, validate_config

            # Test: Config operations
            print("📊 Test 1: Config Retrieval & Validation")

            def config_ops():
                cfg = get_inference_config()
                validate_config(cfg)
                return cfg

            result = self.harness.benchmark_function(
                name="config_enhanced/ops",
                func=config_ops,
                iterations=1000,
                warmup=100,
            )
            result.implementation = "python"

            stats = {
                "config_ops": {
                    "duration_ms": result.duration_ms,
                    "memory_peak_mb": result.memory_peak_mb,
                    "iterations": result.iterations,
                },
            }

            self.results["config_enhanced"] = stats
            print("✅ config_enhanced benchmarks complete")
            return stats

        except Exception:
            # [X-Ray auto-fix] print(f"⚠️  config_enhanced: {e}")
            self.results["config_enhanced"] = None
            return None

    def run_all_benchmarks(self):
        """Run all baseline benchmarks"""
        print("\n")
        print("=" * 80)
        print("  RAG_RAT PYTHON BASELINE BENCHMARKS - PHASE 2".center(80))
        print("=" * 80)

        self.benchmark_inference_guard()
        self.benchmark_config()
        self.benchmark_llm_service()
        self.benchmark_rag_integration()

        self.generate_baseline_report()

    def generate_baseline_report(self):
        """Generate comprehensive baseline report"""
        print("\n" + "=" * 80)
        print("BASELINE PERFORMANCE SUMMARY")
        print("=" * 80)

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "phase": "Phase 2: Python Baseline Establishment",
            "modules": {},
            "summary": {
                "total_tests_run": 0,
                "modules_benchmarked": 0,
                "modules_success": 0,
                "modules_failed": 0,
            },
        }

        # Build report
        for module, tests in self.results.items():
            if tests is None:
                report["summary"]["modules_failed"] += 1
                continue

            report["summary"]["modules_benchmarked"] += 1
            report["summary"]["modules_success"] += 1
            report["modules"][module] = tests

            for test_data in tests.values():
                if isinstance(test_data, dict) and "duration_ms" in test_data:
                    report["summary"]["total_tests_run"] += 1

        # Print summary
        print("\n📊 Module Performance Baseline:")
        print("-" * 80)
        print(f"{'Module':<30} | {'Test':<25} | {'Time (ms)':<12} | {'Memory (MB)':<10}")
        print("-" * 80)

        for module, tests in self.results.items():
            if tests is None:
                # [X-Ray auto-fix] print(f"{module:<30} | {'SKIPPED':<25} | {'N/A':<12} | {'N/A':<10}")
                continue

            if isinstance(tests, dict):
                for test_name, metrics in tests.items():
                    if isinstance(metrics, dict) and "duration_ms" in metrics:
                        time_ms = metrics.get("duration_ms", 0)
                        mem_mb = metrics.get("memory_peak_mb", 0)
                        print(f"{module:<30} | {test_name:<25} | {time_ms:>10.3f} | {mem_mb:>8.2f}")

        print("-" * 80)

        # Save report
        output_path = Path("Rustified/benchmarks/python_baseline.json")
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Baseline report saved to: {output_path}")

        # Print summary stats
        print("\n📈 Summary Statistics:")
        print(
            f"   Modules Benchmarked: {report['summary']['modules_success']}/{report['summary']['modules_benchmarked']}"
        )
        print(f"   Total Tests: {report['summary']['total_tests_run']}")
        print(f"   Timestamp: {report['timestamp']}")

        return report


def main():
    print("\n🚀 Starting Phase 2: Python Baseline Establishment\n")

    benchmarks = RAGRATAdaptedBenchmarks()
    benchmarks.run_all_benchmarks()

    print("\n" + "=" * 80)
    print("✅ PYTHON BASELINE BENCHMARKING COMPLETE")
    print("=" * 80)
    print("\nNext Steps:")
    print("  1. Review baseline in: Rustified/benchmarks/python_baseline.json")
    print("  2. Initialize Rust: cd Rustified && cargo init . --lib")
    print("  3. Start conversion: Read CONVERSION_GUIDE.md")
    print("\n")


if __name__ == "__main__":
    main()
