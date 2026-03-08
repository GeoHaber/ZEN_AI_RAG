import sys
import os
from pathlib import Path
import time
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FullSystemVerify")

# Add Root to Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_rag_completeness():
    """Test rag completeness."""
    logger.info(">>> 1. Verifying RAG 2.0 Components")
    from zena_mode.rag_pipeline import LocalRAG
    from config_system import config

    rag = LocalRAG()

    # 1. Check Model
    assert rag.model is not None, "Embedding model failed to load"
    logger.info(f"✅ Embedding Model: {rag.model}")

    # 2. Check Cache
    assert rag.cache is not None, "Semantic Cache missing"
    logger.info("✅ Semantic Cache: Active")

    # 3. Check Reranker
    assert hasattr(rag, "cross_encoder"), "Cross Encoder attribute missing"
    # Trigger lazy load
    try:
        rag.rerank("test", [{"text": "demo", "title": "t", "url": "u", "score": 0.5}], top_k=1)
        assert rag.cross_encoder is not None, "Cross Encoder failed to initialize"
        logger.info("✅ Cross-Encoder (Reranker): Active")
    except Exception as e:
        logger.error(f"❌ Reranker Failed: {e}")
        raise


def test_ui_components():
    """Test ui components."""
    logger.info(">>> 2. Verifying UI Components (Headless)")
    from ui.modern_chat import ModernChatMessage

    # Test Badge Logic
    msg = ModernChatMessage(
        role="assistant",
        content="Test",
        rag_enhanced=True,
        sources=[
            {"title": "Cache Hit", "url": "loc", "text": "txt", "_is_cached": True},
            {"title": "Reranked", "url": "loc", "text": "txt", "rerank_score": 0.99},
        ],
    )

    assert msg.rag_enhanced is True
    assert msg.sources[0]["_is_cached"] is True
    assert msg.sources[1]["rerank_score"] == 0.99
    logger.info("✅ UI Data Structure: Verified")


def main():
    """Main."""
    logger.info("🚀 Starting Pre-Commit Verification...")
    try:
        test_rag_completeness()
        test_ui_components()
        logger.info("\n🎉 ALL SYSTEMS GO! Ready for Check-in.")
    except Exception as e:
        logger.error(f"\n❌ VERIFICATION FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
