"""
RAG_RAT Python Baseline Benchmarks

Establishes performance metrics for key modules to compare against Rust implementations.
Runs comprehensive tests on:
- inference_guard.py (token counting, validation)
- Core/services/rag_service.py (document retrieval)
- llm_adapters.py (adapter routing)
- rag_integration.py (pipeline orchestration)
"""

import time
import json
import sys
from pathlib import Path

# Add project root and Rustified to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
rustified_path = project_root / "Rustified" / "benchmarks"
sys.path.insert(0, str(rustified_path))

from benchmark_harness import BenchmarkHarness  # noqa: E402
import traceback  # noqa: E402


class RAGRATBaselineBenchmarks:
    """Benchmark suite for RAG_RAT Python implementations"""

    def __init__(self):
        self.harness = BenchmarkHarness(output_dir="Rustified/benchmarks")
        self.results = {}

    def benchmark_inference_guard(self):
        """Benchmark token counting and validation"""
        print("\n" + "=" * 80)
        print("BENCHMARKING: inference_guard.py")
        print("=" * 80)

        try:
            from inference_guard import count_tokens, validate_prompt

            # Test 1: Short text token counting
            print("\n📊 Test 1: Token Counting (Short Text)")
            short_text = "What is machine learning?"

            result1 = self.harness.benchmark_function(
                name="inference_guard/count_tokens_short",
                func=lambda: count_tokens(short_text, "tinyllama"),
                iterations=1000,
                warmup=10,
            )
            result1.implementation = "python"

            # Test 2: Long text token counting
            print("📊 Test 2: Token Counting (Long Text)")
            long_text = " ".join(["token"] * 1000)

            result2 = self.harness.benchmark_function(
                name="inference_guard/count_tokens_long",
                func=lambda: count_tokens(long_text, "tinyllama"),
                iterations=100,
                warmup=5,
                payload_size=len(long_text),
            )
            result2.implementation = "python"

            # Test 3: Prompt validation
            print("📊 Test 3: Prompt Validation")
            prompt = "This is a test prompt for validation"

            result3 = self.harness.benchmark_function(
                name="inference_guard/validate_prompt",
                func=lambda: validate_prompt(prompt),
                iterations=500,
                warmup=10,
            )
            result3.implementation = "python"

            stats = {
                "token_count_short": {
                    "duration_ms": result1.duration_ms,
                    "memory_peak_mb": result1.memory_peak_mb,
                    "iterations": result1.iterations,
                },
                "token_count_long": {
                    "duration_ms": result2.duration_ms,
                    "memory_peak_mb": result2.memory_peak_mb,
                    "iterations": result2.iterations,
                },
                "validate_prompt": {
                    "duration_ms": result3.duration_ms,
                    "memory_peak_mb": result3.memory_peak_mb,
                    "iterations": result3.iterations,
                },
            }

            self.results["inference_guard"] = stats
            print("\n✅ inference_guard benchmarks complete")
            return stats

        except Exception:
            # [X-Ray auto-fix] print(f"❌ Error benchmarking inference_guard: {e}")
            traceback.print_exc()
            return None

    def benchmark_rag_service(self):
        """Benchmark RAG document retrieval"""
        print("\n" + "=" * 80)
        print("BENCHMARKING: Core/services/rag_service.py")
        print("=" * 80)

        try:
            from Core.services.rag_service import RAGService

            # Initialize RAG service
            rag = RAGService()

            # Add test documents
            test_docs = [
                "Machine learning is a subset of artificial intelligence",
                "Deep learning uses neural networks with multiple layers",
                "Natural language processing handles text and speech",
                "Computer vision processes images and videos",
                "Transfer learning uses pre-trained models",
            ] * 4  # 20 documents total

            print("📊 Building retrieval index...")
            for doc in test_docs:
                rag.add_document(doc)

            # Test 1: Simple query
            print("📊 Test 1: Query (Top 5 Results)")

            result1 = self.harness.benchmark_function(
                name="rag_service/query_top5",
                func=lambda: rag.query("What is machine learning?", top_k=5),
                iterations=50,
                warmup=5,
            )
            result1.implementation = "python"

            # Test 2: Larger result set
            print("📊 Test 2: Query (Top 20 Results)")

            result2 = self.harness.benchmark_function(
                name="rag_service/query_top20",
                func=lambda: rag.query("What is learning?", top_k=20),
                iterations=30,
                warmup=3,
            )
            result2.implementation = "python"

            stats = {
                "query_top5": {
                    "duration_ms": result1.duration_ms,
                    "memory_peak_mb": result1.memory_peak_mb,
                    "iterations": result1.iterations,
                },
                "query_top20": {
                    "duration_ms": result2.duration_ms,
                    "memory_peak_mb": result2.memory_peak_mb,
                    "iterations": result2.iterations,
                },
                "doc_count": len(test_docs),
            }

            self.results["rag_service"] = stats
            print("\n✅ rag_service benchmarks complete")
            return stats

        except Exception:
            # [X-Ray auto-fix] print(f"❌ Error benchmarking rag_service: {e}")
            traceback.print_exc()
            return None

    def benchmark_llm_adapters(self):
        """Benchmark LLM adapter routing"""
        print("\n" + "=" * 80)
        print("BENCHMARKING: llm_adapters.py")
        print("=" * 80)

        try:
            from llm_adapters import get_adapter

            # Test 1: Simple adapter selection
            print("📊 Test 1: Adapter Selection (TinyLlama)")

            result1 = self.harness.benchmark_function(
                name="llm_adapters/select_tinyllama",
                func=lambda: get_adapter("tinyllama"),
                iterations=500,
                warmup=10,
            )
            result1.implementation = "python"

            # Test 2: Adapter instantiation
            print("📊 Test 2: Adapter Instantiation with Config")

            config = {"max_tokens": 512, "temperature": 0.7, "top_p": 0.9}

            result2 = self.harness.benchmark_function(
                name="llm_adapters/create_with_config",
                func=lambda: get_adapter("tinyllama", config),
                iterations=100,
                warmup=5,
            )
            result2.implementation = "python"

            stats = {
                "select_adapter": {
                    "duration_ms": result1.duration_ms,
                    "memory_peak_mb": result1.memory_peak_mb,
                    "iterations": result1.iterations,
                },
                "create_configured": {
                    "duration_ms": result2.duration_ms,
                    "memory_peak_mb": result2.memory_peak_mb,
                    "iterations": result2.iterations,
                },
            }

            self.results["llm_adapters"] = stats
            print("\n✅ llm_adapters benchmarks complete")
            return stats

        except Exception:
            # [X-Ray auto-fix] print(f"⚠️  Warning benchmarking llm_adapters: {e}")
            # Not critical, continue
            return None

    def benchmark_rag_integration(self):
        """Benchmark RAG pipeline orchestration"""
        print("\n" + "=" * 80)
        print("BENCHMARKING: rag_integration.py")
        print("=" * 80)

        try:
            from rag_integration import RAGIntegration

            # Initialize RAG integration
            rag_int = RAGIntegration()

            # Test 1: Document loading
            print("📊 Test 1: Document Loading & Indexing")

            test_docs = {
                "doc1": "First document about machine learning",
                "doc2": "Second document about deep learning",
                "doc3": "Third document about neural networks",
            }

            def load_docs():
                for doc_id, content in test_docs.items():
                    rag_int.add_document(doc_id, content)

            result1 = self.harness.benchmark_function(
                name="rag_integration/load_documents",
                func=load_docs,
                iterations=20,
                warmup=2,
            )
            result1.implementation = "python"

            # Test 2: Pipeline retrieval
            print("📊 Test 2: Pipeline Retrieval")

            result2 = self.harness.benchmark_function(
                name="rag_integration/pipeline_query",
                func=lambda: rag_int.retrieve("What is learning?", top_k=5),
                iterations=30,
                warmup=3,
            )
            result2.implementation = "python"

            stats = {
                "load_documents": {
                    "duration_ms": result1.duration_ms,
                    "memory_peak_mb": result1.memory_peak_mb,
                    "iterations": result1.iterations,
                },
                "pipeline_query": {
                    "duration_ms": result2.duration_ms,
                    "memory_peak_mb": result2.memory_peak_mb,
                    "iterations": result2.iterations,
                },
            }

            self.results["rag_integration"] = stats
            print("\n✅ rag_integration benchmarks complete")
            return stats

        except Exception:
            # [X-Ray auto-fix] print(f"⚠️  Warning benchmarking rag_integration: {e}")
            return None

    def benchmark_config_parsing(self):
        """Benchmark configuration parsing"""
        print("\n" + "=" * 80)
        print("BENCHMARKING: config_enhanced.py")
        print("=" * 80)

        try:
            from config_enhanced import ConfigManager

            # Test: Config initialization and access
            print("📊 Test 1: Config Initialization & Access")

            def config_ops():
                cfg = ConfigManager()
                _ = cfg.get("max_tokens", 512)
                _ = cfg.get("temperature", 0.7)
                _ = cfg.get("model", "tinyllama")

            result = self.harness.benchmark_function(
                name="config_enhanced/init_and_access",
                func=config_ops,
                iterations=5000,
                warmup=100,
            )
            result.implementation = "python"

            stats = {
                "config_operations": {
                    "duration_ms": result.duration_ms,
                    "memory_peak_mb": result.memory_peak_mb,
                    "iterations": result.iterations,
                },
            }

            self.results["config_enhanced"] = stats
            print("\n✅ config_enhanced benchmarks complete")
            return stats

        except Exception:
            # [X-Ray auto-fix] print(f"⚠️  Warning benchmarking config_enhanced: {e}")
            return None

    def run_all_benchmarks(self):
        """Run all baseline benchmarks"""
        print("\n")
        print("=" * 80)
        print("  RAG_RAT PYTHON BASELINE BENCHMARKS - PHASE 2 VALIDATION".center(80))
        print("=" * 80)

        # Run benchmarks
        self.benchmark_inference_guard()
        self.benchmark_rag_service()
        self.benchmark_llm_adapters()
        self.benchmark_rag_integration()
        self.benchmark_config_parsing()

        # Generate report
        self.generate_baseline_report()

    def generate_baseline_report(self):
        """Generate comprehensive baseline report"""
        print("\n" + "=" * 80)
        print("BASELINE PERFORMANCE SUMMARY")
        print("=" * 80)

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "phase": "Python Baseline (Phase 2)",
            "modules": self.results,
            "summary": {
                "total_benchmarks_run": sum(len(m) for m in self.results.values() if isinstance(m, dict)),
                "modules_benchmarked": len(self.results),
            },
        }

        # Print summary table
        print("\n📊 Module Performance Summary:")
        print("-" * 80)
        print(f"{'Module':<30} | {'Test':<25} | {'Time (ms)':<12} | {'Memory (MB)':<10}")
        print("-" * 80)

        for module, tests in self.results.items():
            if tests is None:
                continue
            if isinstance(tests, dict):
                for test_name, metrics in tests.items():
                    if isinstance(metrics, dict) and "duration_ms" in metrics:
                        print(
                            f"{module:<30} | {test_name:<25} | "
                            f"{metrics['duration_ms']:>10.2f} | "
                            f"{metrics.get('memory_peak_mb', 0):>8.1f}"
                        )

        print("-" * 80)

        # Save report
        output_path = Path("Rustified/benchmarks/python_baseline_results.json")
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Baseline report saved to: {output_path}")

        # Also save using harness
        self.harness.save_results("python_baseline_results.json")

        return report


def main():
    benchmarks = RAGRATBaselineBenchmarks()
    benchmarks.run_all_benchmarks()

    print("\n" + "=" * 80)
    print("✅ PYTHON BASELINE BENCHMARKING COMPLETE")
    print("=" * 80)
    print("\nNext Steps for Phase 2:")
    print("  1. Review baseline results in: Rustified/benchmarks/python_baseline_results.json")
    print("  2. Initialize Rust project: cd Rustified && cargo init . --lib")
    print("  3. Begin module conversion using: CONVERSION_GUIDE.md")
    print("\n")


if __name__ == "__main__":
    main()
