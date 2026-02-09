import os
import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAGVerify")

def test_rag():
    try:
        from config_system import config
        from zena_mode.rag_pipeline import LocalRAG
        
        rag_cache = config.BASE_DIR / "rag_cache"
        logger.info(f"Using RAG cache: {rag_cache}")
        
        rag = LocalRAG(cache_dir=rag_cache)
        stats = rag.get_stats()
        logger.info(f"RAG Stats: {stats}")
        
        if stats.get('total_chunks', 0) == 0:
            logger.warning("No chunks found in RAG! Indexing a test document...")
            test_docs = [
                {
                    "title": "ZenAI Info",
                    "content": "ZenAI is a professional AI assistant with advanced RAG capabilities and modular UI.",
                    "url": "https://zenai.local/info"
                }
            ]
            rag.build_index(test_docs)
            logger.info("Indexing complete.")
            stats = rag.get_stats()
            logger.info(f"Updated RAG Stats: {stats}")

        # Test Search
        query = "What is ZenAI?"
        logger.info(f"Searching for: '{query}'")
        results = rag.search(query, k=3)
        
        if results:
            logger.info(f"Found {len(results)} results:")
            for i, res in enumerate(results, 1):
                logger.info(f"[{i}] Score: {res.get('score', 'N/A')}")
                logger.info(f"    Title: {res.get('title')}")
                logger.info(f"    Text: {res.get('text')[:100]}...")
        else:
            logger.error("No results found for search!")

        # Test Hybrid Search
        logger.info(f"Hybrid Searching for: '{query}'")
        results = rag.hybrid_search(query, k=3)
        if results:
            logger.info(f"Found {len(results)} hybrid results.")
        else:
            logger.error("No hybrid results found!")

    except Exception as e:
        logger.error(f"RAG Test Failed: {e}", exc_info=True)

if __name__ == "__main__":
    test_rag()
