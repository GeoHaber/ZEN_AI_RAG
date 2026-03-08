import pytest
import os
import shutil
import logging
from pathlib import Path
from zena_mode.rag_pipeline import LocalRAG


def test_rag_lock_graceful_handling(tmp_path):
    """Verify that LocalRAG handles concurrent storage access gracefully."""
    storage_dir = tmp_path / "rag_lock_test"
    storage_dir.mkdir()

    # 1. Initialize first instance (holds the lock)
    rag1 = LocalRAG(cache_dir=storage_dir)
    assert rag1.qdrant is not None
    assert not rag1.read_only

    # 2. Attempt to initialize second instance (should fail lock)
    # We expect a warning log and degraded mode
    rag2 = LocalRAG(cache_dir=storage_dir)

    # 3. Assertions for instance 2
    assert rag2.qdrant is None
    assert rag2.read_only is True

    # 4. Verify search fallback (should not crash)
    # Even in degraded mode, search should return empty or use in-memory buffers
    results = rag2.search("warmup")
    assert isinstance(results, list)

    # 5. Verify write protection
    # Adding chunks should skip gracefully
    rag2.add_chunks([{"text": "test", "url": "test.com", "title": "test"}])
    assert "test" not in [c["text"] for c in rag2.chunks]

    # Cleanup
    del rag1
    del rag2


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pytest.main([__file__, "-v"])
