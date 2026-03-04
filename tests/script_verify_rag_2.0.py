
import sys
import os
import logging
import time

# Add root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_system import config
from zena_mode.rag_pipeline import LocalRAG

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAG2.0_Verify")

def _do_test_rag_upgrade_setup():
    """Helper: setup phase for test_rag_upgrade."""

    logger.info("🚀 Starting RAG 2.0 Verification")

    # 1. Inspect Config
    logger.info(f"Target Model: {config.embedding_config.MODELS['balanced']}")
    logger.info(f"Chunk Strategy: {config.rag.chunk_strategy}")

    # Force settings
    config.rag.chunk_strategy = "semantic"
    config.rag.embedding_model = "balanced" # BGE-Base

    # 2. Initialize RAG (should trigger BGE download/load)
    logger.info("Initializing LocalRAG (this may take time for model download)...")
    rag = LocalRAG()

    # 3. Test Semantic Chunking
    logger.info("Testing Semantic Chunking...")
    sample_text = (
        "Artificial Intelligence is a broad field. Machine learning is a subset of AI. "
        "Deep learning uses neural networks. "
        "The quick brown fox jumps over the lazy dog. "
        "Baking cookies requires flour and sugar. "
        "Preheat the oven to 350 degrees."
    )

    doc = {"content": sample_text, "title": "AI and Cookies", "url": "test://1"}
    chunks = rag.chunk_documents([doc], chunk_size=200, overlap=0)

    for i, c in enumerate(chunks):
        logger.info(f"Chunk {i}: {c['text'][:50]}... ({len(c['text'])} chars)")

    return chunks, rag


def test_rag_upgrade():
    """Test rag upgrade."""
    chunks, rag = _do_test_rag_upgrade_setup()
    # Expect at least 2 chunks (AI vs Cookies) if semantic splitting works well
    if len(chunks) >= 2:
        logger.info("✅ Semantic Chunking looks active (multiple chunks formed)")
    else:
        logger.warning(f"⚠️ Only {len(chunks)} chunks formed. Tune threshold?")

    # 4. Test Semantic Cache
    logger.info("Testing Semantic Cache...")
    rag.cache.clear()
    
    # Ingest chunks manually to index
    rag.add_chunks(chunks)
    
    # Query 1 (Miss)
    start = time.time()
    rag.search("How to bake cookies?", k=1)
    t1 = time.time() - start
    logger.info(f"Query 1 (Miss): {t1:.4f}s")
    
    # Query 2 (Semantic Hit - phrasing diff)
    start = time.time()
    rag.search("Baking instruction", k=1) # Should hit "How to bake cookies?" embedding in cache? 
    # Wait, semantic cache matches QUERY vectors.
    # So "Baking instruction" embedding should be close to "How to bake cookies?" embedding.
    time.time() - start
    
    # Check internals
    if rag.cache._semantic_cache:
        logger.info(f"Cache entries: {len(rag.cache._semantic_cache)}")
        logger.info("✅ Semantic Cache populated")
    else:
        logger.error("❌ Semantic Cache EMPTY")

    logger.info("✅ RAG 2.0 Verification Complete")

if __name__ == "__main__":
    test_rag_upgrade()
