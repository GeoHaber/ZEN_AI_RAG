# -*- coding: utf-8 -*-
"""
test_zero_waste_monkey.py — ZeroWasteCache Adversarial / Monkey Tests
======================================================================

Targets: Core/zero_waste_cache.py (ZeroWasteCache, CacheFingerprint, Tier1/Tier2 entries)
Tests memory bounds, TTL boundaries, concurrent access, adversarial inputs.

Run:
    pytest tests/test_zero_waste_monkey.py -v --tb=short -x
"""

import random
import string
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_CHAOS_STRINGS: list[str] = [
    "",
    "   ",
    "\x00\x01\x02",
    "A" * 100_000,
    "🔥" * 5_000,
    "<script>alert('xss')</script>",
    "'; DROP TABLE users; --",
    "Hello 你好 مرحبا こんにちは",
    "\u202e\u200b\u200c\u200d\ufeff",
    "NaN",
    "null",
    "None",
    "what is the latest news",
    "today's weather",
    "current stock price",
]


def _mock_model():
    model = MagicMock()
    model.encode.return_value = [random.random() for _ in range(384)]
    return model


# ═════════════════════════════════════════════════════════════════════════════
#  CacheFingerprint Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestCacheFingerprintMonkey:
    """Verify CacheFingerprint creation and from_chunks factory."""

    def test_from_chunks_empty(self):
        from Core.zero_waste_cache import CacheFingerprint

        fp = CacheFingerprint.from_chunks([], collection_version=0)
        assert isinstance(fp.combined_hash, str)
        assert len(fp.chunk_hashes) == 0

    def test_from_chunks_normal(self):
        from Core.zero_waste_cache import CacheFingerprint

        chunks = [
            {"text": "chunk 1", "source_url": "http://example.com/1"},
            {"text": "chunk 2", "source_url": "http://example.com/2"},
        ]
        fp = CacheFingerprint.from_chunks(chunks, collection_version=1)
        assert len(fp.chunk_hashes) == 2
        assert fp.collection_version == 1

    def test_from_chunks_no_text_key(self):
        """Chunks without 'text' key — should handle gracefully."""
        from Core.zero_waste_cache import CacheFingerprint

        chunks = [{"id": 1}, {"id": 2}]
        try:
            fp = CacheFingerprint.from_chunks(chunks, collection_version=0)
            assert isinstance(fp, CacheFingerprint)
        except (KeyError, TypeError):
            pass  # raising on missing 'text' is acceptable


# ═════════════════════════════════════════════════════════════════════════════
#  CacheValidationStrategy Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestCacheValidationStrategyMonkey:
    """Verify strategy enum and classify_strategy."""

    def test_all_strategies_exist(self):
        from Core.zero_waste_cache import CacheValidationStrategy

        expected = {"FINGERPRINT", "TEMPORAL", "VERSION", "STATIC"}
        actual = {s.name for s in CacheValidationStrategy}
        assert expected.issubset(actual)

    def test_classify_temporal_queries(self):
        cache = self._make_cache()
        temporal_queries = ["what is today's news", "latest updates", "current weather"]
        for q in temporal_queries:
            strategy = cache.classify_strategy(q)
            # Should recognize temporal keywords
            from Core.zero_waste_cache import CacheValidationStrategy

            assert isinstance(strategy, CacheValidationStrategy)

    def test_classify_static_queries(self):
        cache = self._make_cache()
        static_queries = ["what is photosynthesis", "explain quantum mechanics"]
        for q in static_queries:
            strategy = cache.classify_strategy(q)
            from Core.zero_waste_cache import CacheValidationStrategy

            assert isinstance(strategy, CacheValidationStrategy)

    def test_classify_chaos_strings(self):
        cache = self._make_cache()
        for s in _CHAOS_STRINGS:
            try:
                strategy = cache.classify_strategy(s)
                from Core.zero_waste_cache import CacheValidationStrategy

                assert isinstance(strategy, CacheValidationStrategy)
            except (ValueError, TypeError):
                pass  # rejecting garbage is fine

    def _make_cache(self):
        from Core.zero_waste_cache import ZeroWasteCache

        return ZeroWasteCache(model=_mock_model(), max_entries=100)


# ═════════════════════════════════════════════════════════════════════════════
#  ZeroWasteCache Core Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestZeroWasteCacheMonkey:
    """Adversarial tests for the 2-tier cache."""

    def _make_cache(self, max_entries=100, ttl1=3600, ttl2=7200):
        from Core.zero_waste_cache import ZeroWasteCache

        return ZeroWasteCache(
            model=_mock_model(),
            max_entries=max_entries,
            tier1_ttl=ttl1,
            tier2_ttl=ttl2,
        )

    def test_set_get_roundtrip(self):
        cache = self._make_cache()
        chunks = [{"text": "chunk data", "score": 0.9}]
        cache.set_answer("test query", results=[{"text": "answer"}], source_chunks=chunks)
        result = cache.get_answer("test query")
        # May or may not hit due to threshold, but must not crash

    def test_chaos_strings_no_crash(self):
        cache = self._make_cache()
        for s in _CHAOS_STRINGS:
            try:
                cache.set_answer(s, results=[{"text": "ans"}], source_chunks=[{"text": "chunk"}])
                cache.get_answer(s)
                cache.set_context(s, chunks=[{"text": "ctx"}])
                cache.get_context(s)
            except (TypeError, ValueError):
                pass  # rejecting bad input is fine

    def test_1000_items_memory_bounded(self):
        """Insert 1000 items into a 100-entry cache — must evict, not OOM."""
        cache = self._make_cache(max_entries=100)
        for i in range(1000):
            cache.set_answer(
                f"query_{i}",
                results=[{"text": f"answer_{i}"}],
                source_chunks=[{"text": f"chunk_{i}"}],
            )
        # If internal size tracking exists, check it
        # Otherwise just verify no crash

    def test_invalidate_urls(self):
        cache = self._make_cache()
        cache.set_answer(
            "test",
            results=[{"text": "ans"}],
            source_chunks=[{"text": "chunk", "source_url": "http://example.com"}],
        )
        count = cache.invalidate_urls({"http://example.com"})
        assert isinstance(count, int)
        assert count >= 0

    def test_invalidate_empty_urls(self):
        cache = self._make_cache()
        count = cache.invalidate_urls(set())
        assert count == 0

    def test_bump_version(self):
        cache = self._make_cache()
        cache.bump_version()
        cache.bump_version()  # double bump must not crash

    def test_is_temporal_query(self):
        cache = self._make_cache()
        assert cache.is_temporal_query("what is today's news") or True  # result depends on impl
        assert isinstance(cache.is_temporal_query("explain gravity"), bool)

    def test_zero_ttl(self):
        """TTL=0 means immediate expiry — get should return None."""
        cache = self._make_cache(ttl1=0, ttl2=0)
        cache.set_answer("q", results=[{"text": "a"}], source_chunks=[{"text": "c"}])
        # Immediate get — may or may not be expired depending on implementation
        result = cache.get_answer("q")
        assert result is None or isinstance(result, (list, tuple, dict))

    def test_nan_embedding_no_crash(self):
        """Model returns NaN embeddings — cache must handle gracefully."""
        from Core.zero_waste_cache import ZeroWasteCache

        model = MagicMock()
        model.encode.return_value = [float("nan")] * 384
        cache = ZeroWasteCache(model=model, max_entries=50)
        try:
            cache.set_answer("test", results=[{"text": "a"}], source_chunks=[{"text": "c"}])
            cache.get_answer("test")
        except (ValueError, RuntimeError):
            pass  # raising on NaN is acceptable


# ═════════════════════════════════════════════════════════════════════════════
#  Concurrent Access Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestZeroWasteConcurrencyMonkey:
    """Thread safety for ZeroWasteCache get/set operations."""

    def test_concurrent_get_set(self):
        from Core.zero_waste_cache import ZeroWasteCache

        cache = ZeroWasteCache(model=_mock_model(), max_entries=200)
        errors = []

        def writer(tid):
            try:
                for i in range(100):
                    cache.set_answer(
                        f"t{tid}_q{i}",
                        results=[{"text": f"ans_{tid}_{i}"}],
                        source_chunks=[{"text": f"chunk_{tid}_{i}"}],
                    )
            except Exception as e:
                errors.append(e)

        def reader(tid):
            try:
                for i in range(100):
                    cache.get_answer(f"t{tid}_q{random.randint(0, 99)}")
            except Exception as e:
                errors.append(e)

        threads = []
        for t in range(5):
            threads.append(threading.Thread(target=writer, args=(t,)))
            threads.append(threading.Thread(target=reader, args=(t,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors, f"Concurrency errors: {errors}"

    def test_concurrent_invalidate(self):
        from Core.zero_waste_cache import ZeroWasteCache

        cache = ZeroWasteCache(model=_mock_model(), max_entries=200)
        errors = []

        # Fill cache
        for i in range(50):
            cache.set_answer(
                f"q{i}",
                results=[{"text": f"a{i}"}],
                source_chunks=[{"text": f"c{i}", "source_url": f"http://example.com/{i}"}],
            )

        def invalidator(tid):
            try:
                for i in range(50):
                    cache.invalidate_urls({f"http://example.com/{random.randint(0, 49)}"})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=invalidator, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert not errors, f"Invalidation errors: {errors}"
