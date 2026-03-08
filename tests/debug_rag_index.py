import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from zena_mode.rag_pipeline import LocalRAG
from config_system import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAGDebug")


def debug_index():
    """Debug index."""
    # [X-Ray auto-fix] print(f"📂 Loading RAG Index from: {config.rag_cache_dir}")
    rag = LocalRAG()

    query = "CTO"
    # [X-Ray auto-fix] print(f"\n🔍 Searching for: '{query}'")
    results = rag.search(query, k=10)

    if not results:
        print("❌ No results found. Index might be empty or missing term.")
    else:
        # [X-Ray auto-fix] print(f"✅ Found {len(results)} chunks:")
        for i, res in enumerate(results):
            content = res.get("text", "")[:200].replace("\n", " ")
            # [X-Ray auto-fix] print(f"[{i + 1}] Score: {res.get('score', 0):.4f} | Source: {res.get('title')} | {content}...")
    # Also try hybrid
    # [X-Ray auto-fix] print(f"\n🔍 Hybrid Search for: '{query}'")
    try:
        results = rag.hybrid_search(query, k=10)
        for i, res in enumerate(results):
            content = res.get("text", "")[:200].replace("\n", " ")
            # [X-Ray auto-fix] print(f"[{i + 1}] Score: {res.get('fusion_score', 0):.4f} | Source: {res.get('title')} | {content}...")
    except Exception:
        # [X-Ray auto-fix] print(f"❌ Hybrid search failed: {e}")
        pass


if __name__ == "__main__":
    debug_index()
