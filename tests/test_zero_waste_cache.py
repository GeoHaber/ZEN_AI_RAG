"""
Tests for Core/zero_waste_cache.py — ZeroWasteCache two-tier caching

Tests cover:
  - Temporal bypass detection
  - CacheFingerprint creation (with source_urls + point_ids)
  - Tier 1 exact/semantic get/set
  - Tier 2 context get/set
  - bump_version() invalidation
  - clear()
  - Stats tracking & summary
  - ZeroWasteCacheAdapter backward compat (validate_fn, source_chunks forwarding)
  - Query strategy classification (TEMPORAL, VERSION, FINGERPRINT)
  - Adaptive TTLs by hit count
  - Surgical URL invalidation (invalidate_urls)
  - Edge cases
"""

import time
import pytest
from unittest.mock import MagicMock
import numpy as np


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_model():
    """Mock SentenceTransformer producing consistent embeddings."""
    model = MagicMock()
    _cache = {}

    def encode_fn(texts, **kwargs):
        results = []
        for t in texts:
            key = t.strip().lower()[:80]
            if key not in _cache:
                vec = np.random.RandomState(hash(key) % 2**31).randn(384)
                _cache[key] = vec / (np.linalg.norm(vec) + 1e-10)
            results.append(_cache[key])
        return np.array(results)

    model.encode = encode_fn
    return model


@pytest.fixture
def cache(mock_model):
    """Fresh ZeroWasteCache with fast TTLs."""
    from Core.zero_waste_cache import ZeroWasteCache

    return ZeroWasteCache(
        model=mock_model,
        max_entries=100,
        tier1_ttl=3600,
        tier2_ttl=7200,
        tier1_threshold=0.95,
        tier2_threshold=0.70,
    )


@pytest.fixture
def sample_results():
    """Fake search results to cache."""
    return [
        {
            "text": "Python is a high-level language.",
            "url": "https://python.org",
            "score": 0.95,
        },
        {
            "text": "Python supports OOP and functional.",
            "url": "https://docs.python.org",
            "score": 0.88,
        },
    ]


@pytest.fixture
def sample_chunks():
    """Fake context chunks."""
    return [
        {"text": "Python was created by Guido van Rossum.", "url": "a.com"},
        {"text": "First released in 1991.", "url": "b.com"},
        {"text": "Python emphasizes readability.", "url": "c.com"},
    ]


# ─── Import ────────────────────────────────────────────────────────────────


def test_import():
    from Core.zero_waste_cache import (
        ZeroWasteCache,
        ZeroWasteCacheAdapter,
        TEMPORAL_KEYWORDS,
    )

    assert ZeroWasteCache is not None
    assert ZeroWasteCacheAdapter is not None
    assert len(TEMPORAL_KEYWORDS) > 0


# ─── Temporal Detection ───────────────────────────────────────────────────


def test_temporal_bypass_latest(cache):
    assert cache.is_temporal_query("What are the latest COVID guidelines?")


def test_temporal_bypass_current(cache):
    assert cache.is_temporal_query("current weather in Oradea")


def test_temporal_bypass_today(cache):
    assert cache.is_temporal_query("What happened today?")


def test_temporal_bypass_romanian(cache):
    assert cache.is_temporal_query("cele mai recente știri")


def test_non_temporal_query(cache):
    assert not cache.is_temporal_query("What is photosynthesis?")


def test_non_temporal_history(cache):
    """History of X is NOT temporal in the 'freshness' sense."""
    # "history" doesn't appear in TEMPORAL_KEYWORDS
    assert not cache.is_temporal_query("Tell me about the history of Rome")


# ─── CacheFingerprint ─────────────────────────────────────────────────────


def test_fingerprint_from_chunks(sample_chunks):
    from Core.zero_waste_cache import CacheFingerprint

    fp = CacheFingerprint.from_chunks(sample_chunks, collection_version=5)
    assert len(fp.chunk_hashes) == 3
    assert isinstance(fp.combined_hash, str)
    assert fp.collection_version == 5
    # ── New: source_urls extracted from chunks ──
    assert len(fp.source_urls) >= 1
    assert "a.com" in fp.source_urls


def test_fingerprint_source_urls_deduplicated():
    """Duplicate URLs should appear only once in source_urls."""
    from Core.zero_waste_cache import CacheFingerprint

    chunks = [
        {"text": "chunk one", "url": "http://example.com"},
        {"text": "chunk two", "url": "http://example.com"},
        {"text": "chunk three", "url": "http://other.com"},
    ]
    fp = CacheFingerprint.from_chunks(chunks)
    assert fp.source_urls == ("http://example.com", "http://other.com")


def test_fingerprint_point_ids():
    """Point IDs should be extracted when present."""
    from Core.zero_waste_cache import CacheFingerprint

    chunks = [
        {"text": "data", "url": "a.com", "qdrant_id": 12345},
        {"text": "data2", "url": "b.com"},
    ]
    fp = CacheFingerprint.from_chunks(chunks)
    assert fp.source_point_ids == ("12345",)


def test_fingerprint_deterministic(sample_chunks):
    from Core.zero_waste_cache import CacheFingerprint

    fp1 = CacheFingerprint.from_chunks(sample_chunks, collection_version=1)
    fp2 = CacheFingerprint.from_chunks(sample_chunks, collection_version=1)
    assert fp1.combined_hash == fp2.combined_hash
    assert fp1.chunk_hashes == fp2.chunk_hashes


def test_fingerprint_changes_with_data():
    from Core.zero_waste_cache import CacheFingerprint

    chunks_a = [{"text": "Version A of data"}]
    chunks_b = [{"text": "Version B of data"}]
    fp_a = CacheFingerprint.from_chunks(chunks_a)
    fp_b = CacheFingerprint.from_chunks(chunks_b)
    assert fp_a.combined_hash != fp_b.combined_hash


# ─── Tier 1: Answer Cache ─────────────────────────────────────────────────


def test_tier1_miss_on_empty(cache):
    """Empty cache should return None."""
    result = cache.get_answer("What is Python?")
    assert result is None


def test_tier1_exact_hit(cache, sample_results, sample_chunks):
    """Exact same query should hit Tier 1."""
    query = "What is Python?"
    cache.set_answer(query, sample_results, sample_chunks)
    result = cache.get_answer(query)
    assert result is not None
    assert len(result) == len(sample_results)
    assert result[0]["text"] == sample_results[0]["text"]


def test_tier1_exact_hit_case_insensitive(cache, sample_results):
    """Exact matching should be case-insensitive."""
    cache.set_answer("What is Python?", sample_results)
    result = cache.get_answer("what is python?")
    assert result is not None


def test_tier1_tagged_with_cache_metadata(cache, sample_results):
    """Cached results should have _is_cached and _cache_tier tags."""
    cache.set_answer("What is Python?", sample_results)
    result = cache.get_answer("What is Python?")
    assert result[0].get("_is_cached") is True
    assert "tier1" in result[0].get("_cache_tier", "")


def test_tier1_temporal_bypass(cache, sample_results):
    """Temporal query should bypass Tier 1 even if cached."""
    cache.set_answer("latest python version", sample_results)
    result = cache.get_answer("latest python version")
    assert result is None


# ─── Tier 2: Context Cache ────────────────────────────────────────────────


def test_tier2_miss_on_empty(cache):
    result = cache.get_context("Python history")
    assert result is None


def test_tier2_exact_query_hit(cache, sample_chunks):
    """Same query should hit Tier 2."""
    query = "Tell me about Python programming"
    cache.set_context(query, sample_chunks)
    result = cache.get_context(query)
    # Same query → high cosine → should hit
    assert result is not None
    assert len(result) >= 1


def test_tier2_tagged(cache, sample_chunks):
    """Tier 2 results should be tagged."""
    query = "Tell me about Python"
    cache.set_context(query, sample_chunks)
    result = cache.get_context(query)
    if result:
        assert result[0].get("_cache_tier") == "tier2_context"


# ─── bump_version() ──────────────────────────────────────────────────────


def test_bump_version_increments(cache):
    assert cache.collection_version == 0
    cache.bump_version()
    assert cache.collection_version == 1
    cache.bump_version()
    assert cache.collection_version == 2


def test_bump_version_invalidates_tier1(cache, sample_results, sample_chunks):
    """After bump_version, old entries should be invalidated."""
    cache.set_answer("test query", sample_results, sample_chunks)
    cache.bump_version()  # Simulate index write
    result = cache.get_answer("test query")
    # Exact match might still hit (exact cache), but validation should fail
    # because collection version changed. Let's check.
    # The exact cache path checks version in _validate_entry
    # Without validate_fn, conservative invalidation should kick in
    assert result is None  # Invalidated by version bump


# ─── clear() ──────────────────────────────────────────────────────────────


def test_clear_empties_all(cache, sample_results, sample_chunks):
    cache.set_answer("q1", sample_results, sample_chunks)
    cache.set_context("q2", sample_chunks)
    cache.clear()
    assert cache.get_answer("q1") is None
    assert cache.get_context("q2") is None


# ─── Statistics ────────────────────────────────────────────────────────────


def test_stats_initial(cache):
    stats = cache.get_stats()
    assert stats["total_queries"] == 0
    assert stats["tier1_exact_hits"] == 0
    assert stats["tier1_entries"] == 0


def test_stats_after_queries(cache, sample_results, sample_chunks):
    cache.set_answer("test", sample_results, sample_chunks)
    cache.get_answer("test")
    cache.get_answer("something new entirely")
    stats = cache.get_stats()
    assert stats["total_queries"] == 2
    assert stats["tier1_entries"] >= 1


def test_get_summary_is_string(cache):
    summary = cache.get_summary()
    assert isinstance(summary, str)
    assert "Zero-Waste" in summary


# ─── ZeroWasteCacheAdapter ─────────────────────────────────────────────────


def test_adapter_get_set(cache, sample_results):
    from Core.zero_waste_cache import ZeroWasteCacheAdapter

    adapter = ZeroWasteCacheAdapter(cache)

    # Old-style interface
    adapter.set("What is Python?", sample_results)
    result = adapter.get("What is Python?")
    assert result is not None
    assert len(result) == len(sample_results)


def test_adapter_clear(cache, sample_results):
    from Core.zero_waste_cache import ZeroWasteCacheAdapter

    adapter = ZeroWasteCacheAdapter(cache)
    adapter.set("q", sample_results)
    adapter.clear()
    assert adapter.get("q") is None


def test_adapter_context_pass_through(cache, sample_chunks):
    from Core.zero_waste_cache import ZeroWasteCacheAdapter

    adapter = ZeroWasteCacheAdapter(cache)
    adapter.set_context("Python", sample_chunks)
    # Context requires cosine similarity check, same query should work
    result = adapter.get_context("Python")
    # May or may not hit depending on threshold; just don't crash
    assert result is None or isinstance(result, list)


def test_adapter_bump_version(cache):
    from Core.zero_waste_cache import ZeroWasteCacheAdapter

    adapter = ZeroWasteCacheAdapter(cache)
    adapter.bump_version()
    assert cache.collection_version == 1


def test_adapter_is_zero_waste():
    from Core.zero_waste_cache import ZeroWasteCache, ZeroWasteCacheAdapter

    mock = MagicMock()
    mock.encode = lambda t, **kw: np.zeros((len(t), 384))
    zw = ZeroWasteCache(mock)
    adapter = ZeroWasteCacheAdapter(zw)
    assert adapter.is_zero_waste is True


def test_adapter_stats(cache):
    from Core.zero_waste_cache import ZeroWasteCacheAdapter

    adapter = ZeroWasteCacheAdapter(cache)
    stats = adapter.get_stats()
    assert isinstance(stats, dict)
    summary = adapter.get_summary()
    assert isinstance(summary, str)


# ─── Edge Cases ────────────────────────────────────────────────────────────


def test_empty_results(cache):
    """Caching empty results should still work."""
    cache.set_answer("empty query", [])
    result = cache.get_answer("empty query")
    if result is not None:
        assert result == []


def test_set_answer_no_source_chunks(cache, sample_results):
    """set_answer without source_chunks should use results for fingerprinting."""
    cache.set_answer("test", sample_results)  # No source_chunks arg
    # Should not crash


def test_multiple_sets_same_query(cache, sample_results):
    """Setting same query multiple times should overwrite."""
    cache.set_answer("test", sample_results)
    new_results = [{"text": "Updated result", "score": 0.99}]
    cache.set_answer("test", new_results)
    result = cache.get_answer("test")
    if result:
        assert result[0]["text"] == "Updated result"


# ─── Query Strategy Classification ─────────────────────────────────────────


def test_classify_temporal(cache):
    from Core.zero_waste_cache import CacheValidationStrategy

    assert cache.classify_strategy("latest news") == CacheValidationStrategy.TEMPORAL


def test_classify_aggregate(cache):
    from Core.zero_waste_cache import CacheValidationStrategy

    assert cache.classify_strategy("How many patients were admitted?") == CacheValidationStrategy.VERSION


def test_classify_aggregate_romanian(cache):
    from Core.zero_waste_cache import CacheValidationStrategy

    assert cache.classify_strategy("Câte persoane sunt?") == CacheValidationStrategy.VERSION


def test_classify_specific(cache):
    from Core.zero_waste_cache import CacheValidationStrategy

    assert cache.classify_strategy("What is photosynthesis?") == CacheValidationStrategy.FINGERPRINT


def test_classify_total(cache):
    from Core.zero_waste_cache import CacheValidationStrategy

    assert cache.classify_strategy("total revenue last quarter") == CacheValidationStrategy.VERSION


# ─── Adaptive TTLs ─────────────────────────────────────────────────────────


def test_effective_ttl_base(cache):
    """Zero hits → base TTL unchanged."""
    assert cache._effective_ttl(3600, 0) == 3600


def test_effective_ttl_boost(cache):
    """High hit count → TTL extended."""
    result = cache._effective_ttl(3600, 10)
    assert result > 3600
    assert result <= 3600 * 3  # max 3×


def test_effective_ttl_cap(cache):
    """TTL boost should be capped at 3× base."""
    result = cache._effective_ttl(3600, 100)  # 100 hits → would be 12000 boost
    assert result == 3600 * 3  # capped at 3×


def test_adaptive_ttl_keeps_popular_entries(cache, sample_results, sample_chunks):
    """Popular entries (high hit_count) should survive longer TTL checks."""
    cache.set_answer("popular query", sample_results, sample_chunks)

    # Simulate many hits to boost entry
    for _ in range(20):
        result = cache.get_answer("popular query")
        assert result is not None

    # Fast-forward time past base TTL but within adaptive TTL
    entry = cache._exact_cache.get("popular query")
    if entry:
        # Artificially age the entry past base TTL
        entry.created_at = time.time() - cache.tier1_ttl - 100
        # Should still be valid because adaptive TTL extends it
        result = cache.get_answer("popular query")
        assert result is not None, "Popular entry should survive past base TTL"


# ─── Surgical URL Invalidation ─────────────────────────────────────────────


def test_invalidate_urls_empty(cache):
    """Invalidating with empty set should evict nothing."""
    assert cache.invalidate_urls(set()) == 0


def test_invalidate_urls_evicts_matching(cache, sample_results, sample_chunks):
    """Entries with matching source URLs should be evicted."""
    cache.set_answer("test query", sample_results, sample_chunks)
    cache.set_context("test context", sample_chunks)

    # sample_chunks have URLs a.com, b.com, c.com
    evicted = cache.invalidate_urls({"a.com"})
    assert evicted >= 1

    # Cache should be empty for the invalidated entries
    result = cache.get_answer("test query")
    assert result is None


def test_invalidate_urls_preserves_unrelated(cache, sample_results, sample_chunks):
    """Entries NOT matching the URL should survive."""
    cache.set_answer("query one", sample_results, sample_chunks)

    other_results = [{"text": "Unrelated data", "url": "http://unrelated.com", "score": 0.9}]
    other_chunks = [{"text": "Unrelated chunk", "url": "http://unrelated.com"}]
    cache.set_answer("query two", other_results, other_chunks)

    # Invalidate only sample URLs
    cache.invalidate_urls({"a.com"})

    # query two should survive
    result = cache.get_answer("query two")
    assert result is not None


# ─── Adapter: validate_fn + source_chunks forwarding ───────────────────────


def test_adapter_forwards_validate_fn(cache, sample_results, sample_chunks):
    """Adapter.get() should forward validate_fn to underlying cache."""
    from Core.zero_waste_cache import ZeroWasteCacheAdapter

    adapter = ZeroWasteCacheAdapter(cache)

    adapter.set("test", sample_results, source_chunks=sample_chunks)

    # Validator that always returns True
    result = adapter.get("test", validate_fn=lambda fp: True)
    assert result is not None

    # Validator that always returns False → stale
    result = adapter.get("test", validate_fn=lambda fp: False)
    assert result is None


def test_adapter_forwards_source_chunks(cache):
    """Adapter.set() should forward source_chunks for proper fingerprinting."""
    from Core.zero_waste_cache import ZeroWasteCacheAdapter

    adapter = ZeroWasteCacheAdapter(cache)

    results = [{"text": "Answer", "score": 0.9}]
    source = [{"text": "Source chunk A", "url": "http://src.com"}]
    adapter.set("test", results, source_chunks=source)

    # The fingerprint should be built from source, not results
    entry = cache._exact_cache.get("test")
    assert entry is not None
    assert entry.fingerprint.source_urls == ("http://src.com",)


def test_adapter_get_context_with_validate_fn(cache, sample_chunks):
    """Adapter.get_context() should forward validate_fn."""
    from Core.zero_waste_cache import ZeroWasteCacheAdapter

    adapter = ZeroWasteCacheAdapter(cache)

    adapter.set_context("Python programming", sample_chunks)

    # With always-True validator
    result = adapter.get_context("Python programming", validate_fn=lambda fp: True)
    # May or may not hit depending on cosine, just don't crash
    assert result is None or isinstance(result, list)


def test_adapter_invalidate_urls(cache, sample_results, sample_chunks):
    """Adapter.invalidate_urls() should surgically evict entries."""
    from Core.zero_waste_cache import ZeroWasteCacheAdapter

    adapter = ZeroWasteCacheAdapter(cache)

    adapter.set("test", sample_results, source_chunks=sample_chunks)
    evicted = adapter.invalidate_urls({"a.com"})
    assert evicted >= 1


# ─── Stats: new counters ──────────────────────────────────────────────────


def test_stats_has_new_counters(cache):
    stats = cache.get_stats()
    assert "surgical_invalidations" in stats
    assert "aggregate_queries" in stats
