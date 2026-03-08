import sys
import os
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from zena_mode.rag_pipeline import LocalRAG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_qdrant_flow():
    """Test qdrant flow."""
    test_dir = Path("./test_qdrant_db")
    if test_dir.exists():
        import shutil

        shutil.rmtree(test_dir)

    print("🚀 Initializing Qdrant LocalRAG...")
    rag = LocalRAG(cache_dir=test_dir)

    docs = [
        {
            "content": "The capital of France is Paris. It is a major European city and a global center for art, fashion, gastronomy and culture.",
            "title": "Geography",
            "url": "geo.com",
        },
        {
            "content": "ZenAI is a high-performance RAG assistant specializing in logic, coding, and advanced knowledge retrieval using vector databases.",
            "title": "ZenAI Info",
            "url": "zen.ai",
        },
        {
            "content": "Quantum computing uses qubits to represent data, allowing for much faster processing of complex problems than classical computers.",
            "title": "Quantum",
            "url": "science.net",
        },
    ]

    print("📥 Building index (Semantics + BM25)...")
    rag.build_index(docs)

    print("🔍 Testing Semantic Search (Paris)...")
    results = rag.search("What is the capital of France?")
    assert len(results) > 0
    assert "Paris" in results[0]["text"]
    # [X-Ray auto-fix] print(f"✅ Semantic Search Passed. Score: {results[0]['score']:.4f}")
    print("🔄 Testing Hybrid Search (ZenAI Spezial)...")
    # Intentional mix of keyword match and semantic
    results = rag.hybrid_search("ZenAI Assistant specializing in performance", alpha=0.5)
    assert len(results) > 0
    assert "ZenAI" in results[0]["text"]
    # [X-Ray auto-fix] print(f"✅ Hybrid Search Passed. Fusion Score: {results[0]['fusion_score']:.4f}")
    print("📊 Stats check...")
    stats = rag.get_stats()
    # [X-Ray auto-fix] print(f"Stats: {stats}")
    assert stats["total_chunks"] >= 3


if __name__ == "__main__":
    try:
        test_qdrant_flow()
        print("\n🏆 QDRANT MIGRATION VERIFIED! 🤵")
    except Exception:
        # [X-Ray auto-fix] print(f"❌ Verification FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
