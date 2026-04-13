"""
Tests for all advanced zen_core_libs RAG features integrated into app.py.

Covers:
  1. SmartDeduplicator — chunk deduplication in crawl pipeline
  2. Reranker — heuristic re-ranking of search results
  3. QueryRouter — intent classification and routing config
  4. HallucinationDetector — hallucination checks on LLM output
  5. ZeroWasteCache — answer + context caching
  6. MetricsTracker — latency / counter recording
  7. CorrectiveRAG — retrieval grading
  8. App integration — Flask endpoints use new features correctly

Run:  python -m pytest test_advanced_rag.py -v
"""

from __future__ import annotations

# ── WMI hang workaround for Python 3.13 on Windows ──────────────────────
import platform, sys
if sys.platform == "win32" and sys.version_info >= (3, 13):
    try:
        platform._uname_cache = platform.uname_result("Windows", "", "10", "10.0.22631", "AMD64")
    except (AttributeError, TypeError):
        pass
# ─────────────────────────────────────────────────────────────────────────

import json
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ═══════════════════════════════════════════════════════════════════════════
# 1. SmartDeduplicator
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.rag import SmartDeduplicator


class TestSmartDeduplicator:
    """Verify 5-tier dedup removes duplicates without losing unique content."""

    @pytest.fixture(autouse=True)
    def _skip_semantic(self):
        """Prevent tier4 from loading sentence-transformers (hangs on Win+Py3.13)."""
        with patch.object(SmartDeduplicator, "model", new_callable=lambda: property(lambda self: None)):
            yield

    def test_exact_duplicates_removed(self):
        deduper = SmartDeduplicator()
        chunks = [
            {"text": "Python is a great language for data science and machine learning."},
            {"text": "Python is a great language for data science and machine learning."},
            {"text": "Rust is a fast and memory-safe systems programming language."},
        ]
        result = deduper.deduplicate(chunks)
        assert result.stats.total_input == 3
        assert result.stats.exact_dupes_removed >= 1
        texts = [c["text"] for c in result.unique_chunks]
        assert "Rust is a fast and memory-safe systems programming language." in texts

    def test_no_duplicates_unchanged(self):
        deduper = SmartDeduplicator()
        chunks = [
            {"text": "First unique chunk with enough content to pass."},
            {"text": "Second unique chunk with different content entirely."},
            {"text": "Third unique chunk about something else completely."},
        ]
        result = deduper.deduplicate(chunks)
        assert result.stats.total_output == 3
        assert result.stats.total_removed == 0

    def test_empty_input(self):
        deduper = SmartDeduplicator()
        result = deduper.deduplicate([])
        assert result.stats.total_input == 0
        assert result.unique_chunks == []

    def test_boilerplate_removed(self):
        deduper = SmartDeduplicator()
        chunks = [
            {"text": "Cookie policy: we use cookies to improve your experience."},
            {"text": "This is actual valuable content about machine learning algorithms and their applications."},
        ]
        result = deduper.deduplicate(chunks)
        assert result.stats.boilerplate_removed >= 1
        texts = [c["text"] for c in result.unique_chunks]
        assert any("machine learning" in t for t in texts)

    def test_short_chunks_removed(self):
        deduper = SmartDeduplicator(min_chunk_length=30)
        chunks = [
            {"text": "Too short"},
            {"text": "This chunk has enough content to survive the minimum length filter."},
        ]
        result = deduper.deduplicate(chunks)
        assert result.stats.total_output <= 1

    def test_metadata_preserved(self):
        deduper = SmartDeduplicator()
        chunks = [
            {"text": "Content about Python programming language and its ecosystem.",
             "source_url": "https://python.org", "page_title": "Python"},
        ]
        result = deduper.deduplicate(chunks)
        assert len(result.unique_chunks) == 1
        assert result.unique_chunks[0].get("source_url") == "https://python.org"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Reranker (heuristic mode)
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.rag import Reranker


class TestReranker:
    """Verify heuristic reranker improves result ordering."""

    def test_rerank_basic(self):
        reranker = Reranker(use_cross_encoder=False)
        chunks = [
            "JavaScript runs in browsers and Node.js.",
            "Python is great for data science and machine learning.",
            "Rust is a systems programming language.",
        ]
        ranked = reranker.rerank("Python data science", chunks)
        assert isinstance(ranked, list)
        assert len(ranked) == 3
        # Python chunk should rank higher for a Python query
        assert "Python" in ranked[0]

    def test_rerank_with_scores(self):
        reranker = Reranker(use_cross_encoder=False)
        chunks = ["Relevant content about cats.", "Unrelated stuff about space."]
        ranked, scores = reranker.rerank("cats", chunks, return_scores=True)
        assert len(ranked) == 2
        assert len(scores) == 2
        assert scores[0] >= scores[1]

    def test_rerank_top_k(self):
        reranker = Reranker(use_cross_encoder=False)
        chunks = [f"Chunk {i}" for i in range(10)]
        ranked = reranker.rerank("query", chunks, top_k=3)
        assert len(ranked) == 3

    def test_rerank_empty(self):
        reranker = Reranker(use_cross_encoder=False)
        ranked = reranker.rerank("query", [])
        assert ranked == []

    def test_rerank_stats(self):
        reranker = Reranker(use_cross_encoder=False)
        reranker.rerank("q", ["a", "b"])
        stats = reranker.get_stats()
        assert stats["total_rerankings"] == 1
        assert stats["model_type"] == "heuristic"


# ═══════════════════════════════════════════════════════════════════════════
# 3. QueryRouter
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.rag import QueryRouter, QueryIntent


class TestQueryRouter:
    """Verify query intent classification."""

    def test_simple_query(self):
        router = QueryRouter()
        result = router.route("What is Python?")
        assert result.intent in (QueryIntent.SIMPLE, QueryIntent.CONVERSATIONAL)

    def test_analytical_query(self):
        router = QueryRouter()
        result = router.route("Why does Python use garbage collection and what are the trade-offs?")
        assert result.intent == QueryIntent.ANALYTICAL
        assert result.config["rerank"] is True

    def test_temporal_query(self):
        router = QueryRouter()
        result = router.route("What is the history of Python since 1991?")
        assert result.intent == QueryIntent.TEMPORAL

    def test_aggregate_query(self):
        router = QueryRouter()
        result = router.route("How many programming languages are there? List all top 10.")
        assert result.intent == QueryIntent.AGGREGATE

    def test_routing_result_has_config(self):
        router = QueryRouter()
        result = router.route("explain quantum computing")
        assert "top_k" in result.config
        assert "retrieval" in result.config
        assert 0 <= result.confidence <= 1.0

    def test_empty_query(self):
        router = QueryRouter()
        result = router.route("")
        assert result.intent == QueryIntent.SIMPLE


# ═══════════════════════════════════════════════════════════════════════════
# 4. HallucinationDetector
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.rag import HallucinationDetector


class TestHallucinationDetector:
    """Verify hallucination detection heuristics."""

    def test_grounded_answer(self):
        detector = HallucinationDetector()
        context = "Python was created by Guido van Rossum in 1991."
        answer = "Python was created by Guido van Rossum."
        report = detector.detect(answer, context)
        assert report.score > 0.5  # mostly grounded

    def test_hallucinated_numbers(self):
        detector = HallucinationDetector()
        context = "The study showed 45% efficacy in trials."
        answer = "The drug is 100% effective in curing the disease."
        report = detector.detect(answer, context)
        assert report.has_hallucinations

    def test_absolute_claims_flagged(self):
        detector = HallucinationDetector()
        context = "Some studies suggest benefits."
        answer = "It is always effective and never fails. Everyone knows this."
        report = detector.detect(answer, context)
        assert report.has_hallucinations
        types = {f.type.value for f in report.findings}
        assert "reasoning" in types

    def test_empty_answer(self):
        detector = HallucinationDetector()
        report = detector.detect("", "Some context here.")
        assert report.score == 1.0  # no hallucination in empty answer

    def test_report_structure(self):
        detector = HallucinationDetector()
        report = detector.detect("Test answer", "Test context")
        assert hasattr(report, "score")
        assert hasattr(report, "findings")
        assert hasattr(report, "has_hallucinations")


# ═══════════════════════════════════════════════════════════════════════════
# 5. ZeroWasteCache
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.rag import ZeroWasteCache


class TestZeroWasteCache:
    """Verify two-tier cache operations."""

    def test_answer_put_get(self):
        cache = ZeroWasteCache(max_entries=10, ttl_seconds=60)
        cache.put_answer("what is Python?", "A programming language.")
        result = cache.get_answer("what is Python?")
        assert result == "A programming language."

    def test_answer_miss(self):
        cache = ZeroWasteCache(max_entries=10, ttl_seconds=60)
        assert cache.get_answer("unknown query") is None

    def test_context_put_get(self):
        cache = ZeroWasteCache(max_entries=10, ttl_seconds=60)
        ctx = [{"text": "chunk1"}, {"text": "chunk2"}]
        cache.put_context("search query", ctx)
        result = cache.get_context("search query")
        assert len(result) == 2

    def test_invalidate_specific(self):
        cache = ZeroWasteCache(max_entries=10, ttl_seconds=60)
        cache.put_answer("q1", "a1")
        cache.put_answer("q2", "a2")
        cache.invalidate("q1")
        assert cache.get_answer("q1") is None
        assert cache.get_answer("q2") == "a2"

    def test_invalidate_all(self):
        cache = ZeroWasteCache(max_entries=10, ttl_seconds=60)
        cache.put_answer("q1", "a1")
        cache.put_context("q1", [{"text": "x"}])
        cache.invalidate()
        assert cache.get_answer("q1") is None
        assert cache.get_context("q1") is None

    def test_fingerprint_mismatch(self):
        cache = ZeroWasteCache(max_entries=10, ttl_seconds=60)
        cache.put_answer("q", "a", fingerprint="v1")
        assert cache.get_answer("q", fingerprint="v1") == "a"
        assert cache.get_answer("q", fingerprint="v2") is None

    def test_stats(self):
        cache = ZeroWasteCache(max_entries=10, ttl_seconds=60)
        cache.put_answer("q", "a")
        cache.get_answer("q")
        cache.get_answer("miss")
        stats = cache.get_stats()
        assert stats["t1_hits"] == 1
        assert stats["t1_misses"] == 1
        assert stats["t1_size"] == 1

    def test_eviction(self):
        cache = ZeroWasteCache(max_entries=2, ttl_seconds=60)
        cache.put_answer("q1", "a1")
        cache.put_answer("q2", "a2")
        cache.put_answer("q3", "a3")  # should evict oldest
        assert cache.get_stats()["t1_size"] == 2


# ═══════════════════════════════════════════════════════════════════════════
# 6. MetricsTracker
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.rag import MetricsTracker


class TestMetricsTracker:
    """Verify metrics recording and aggregation."""

    def test_record_and_snapshot(self):
        tracker = MetricsTracker()
        tracker.record("latency", 10.0)
        tracker.record("latency", 20.0)
        tracker.record("latency", 30.0)
        snap = tracker.snapshot("latency")
        assert snap["count"] == 3
        assert snap["mean"] == 20.0
        assert snap["min"] == 10.0
        assert snap["max"] == 30.0

    def test_increment_counter(self):
        tracker = MetricsTracker()
        tracker.increment("requests")
        tracker.increment("requests")
        tracker.increment("requests", 3)
        snap = tracker.snapshot("requests")
        assert snap["total"] == 5

    def test_snapshot_all(self):
        tracker = MetricsTracker()
        tracker.record("a", 1.0)
        tracker.record("b", 2.0)
        all_snaps = tracker.snapshot_all()
        assert "a" in all_snaps
        assert "b" in all_snaps

    def test_reset(self):
        tracker = MetricsTracker()
        tracker.record("x", 1.0)
        tracker.increment("y")
        tracker.reset()
        assert tracker.snapshot("x")["count"] == 0
        assert tracker.snapshot("y")["total"] == 0

    def test_empty_snapshot(self):
        tracker = MetricsTracker()
        snap = tracker.snapshot("nonexistent")
        assert snap["count"] == 0
        assert snap["mean"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# 7. CorrectiveRAG
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.rag import CorrectiveRAG


class TestCorrectiveRAG:
    """Verify CRAG grading logic."""

    def test_grade_high_relevance(self):
        crag = CorrectiveRAG()
        chunks = [
            {"text": "Python programming language created by Guido van Rossum", "score": 0.9},
            {"text": "Python supports multiple paradigms including OOP", "score": 0.85},
        ]
        grade, confidence = crag._grade("Python programming language", chunks)
        assert grade.value in ("correct", "ambiguous")
        assert confidence > 0.0

    def test_grade_low_relevance(self):
        crag = CorrectiveRAG()
        chunks = [
            {"text": "Weather forecast for tomorrow", "score": 0.1},
        ]
        grade, confidence = crag._grade("quantum computing algorithms", chunks)
        assert confidence < 0.65

    def test_grade_empty_chunks(self):
        crag = CorrectiveRAG()
        grade, confidence = crag._grade("anything", [])
        assert grade.value == "incorrect"
        assert confidence == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# 8. HyDE / FLARE (unit tests, no LLM required)
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.rag import HyDERetriever, FLARERetriever


class TestHyDERetriever:
    """HyDE falls back gracefully when no LLM is configured."""

    def test_no_llm_returns_fallback(self):
        hyde = HyDERetriever()  # no llm_fn, embed_fn, search_fn
        result = hyde.retrieve("test query")
        assert result.fallback_used is True
        assert result.original_query == "test query"

    def test_with_mocked_llm(self):
        hyde = HyDERetriever(
            llm_fn=lambda prompt: "Hypothetical answer about testing.",
            embed_fn=lambda text: [0.1] * 384,
            search_fn=lambda emb, k: [{"text": "Real result", "score": 0.8}],
        )
        result = hyde.retrieve("what is testing?")
        assert result.fallback_used is False
        assert len(result.search_results) > 0


class TestFLARERetriever:
    """FLARE falls back gracefully when no LLM is configured."""

    def test_no_generate_fn(self):
        flare = FLARERetriever()
        result = flare.retrieve_and_generate("test query")
        assert result.final_answer == ""

    def test_with_mocked_functions(self):
        flare = FLARERetriever(
            retrieve_fn=lambda q, k=5: [{"text": "relevant data", "score": 0.9}],
            generate_fn=lambda q, chunks: "Definitive answer about testing.",
        )
        result = flare.retrieve_and_generate("test query", [{"text": "initial chunk"}])
        assert result.final_answer != ""
        assert result.iterations >= 1


# ═══════════════════════════════════════════════════════════════════════════
# 9. App integration — Flask endpoints
# ═══════════════════════════════════════════════════════════════════════════


class TestAppIntegration:
    """Test that app.py correctly wires up all zen_core_libs features."""

    @pytest.fixture
    def client(self):
        with patch("app.INDEX") as mock_idx, \
             patch("app.LLAMA") as mock_llama:
            mock_idx.is_built = False
            mock_idx.n_chunks = 0
            mock_idx.stats = {"n_chunks": 0, "model": "test", "n_bits": 3}
            mock_llama.is_running = False

            from app import app
            app.config["TESTING"] = True
            with app.test_client() as c:
                yield c, mock_idx

    def test_search_returns_intent(self, client):
        c, mock_idx = client
        mock_idx.search.return_value = []
        resp = c.post("/api/search", json={"query": "Why does Python use GIL?", "k": 3})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "intent" in data
        assert "intent_confidence" in data

    def test_search_empty_query(self, client):
        c, _ = client
        resp = c.post("/api/search", json={"query": "", "k": 3})
        assert resp.status_code == 400

    def test_stats_includes_reranker_cache_metrics(self, client):
        c, mock_idx = client
        resp = c.get("/api/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "reranker" in data
        assert "cache" in data
        assert "metrics" in data

    def test_clear_resets_cache(self, client):
        c, mock_idx = client
        mock_idx.clear = MagicMock()
        resp = c.post("/api/clear")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_search_caching(self, client):
        """Second identical search should hit cache."""
        c, mock_idx = client
        from zen_core_libs.rag import Chunk, SearchResult
        mock_chunk = MagicMock()
        mock_chunk.text = "Python is great"
        mock_chunk.source_url = "http://test.com"
        mock_chunk.page_title = "Test"
        mock_chunk.chunk_idx = 0
        mock_result = MagicMock()
        mock_result.chunk = mock_chunk
        mock_result.score = 0.9
        mock_idx.search.return_value = [mock_result]

        # First search
        resp1 = c.post("/api/search", json={"query": "Python", "k": 3})
        assert resp1.status_code == 200

        # Second search — should hit cache
        resp2 = c.post("/api/search", json={"query": "Python", "k": 3})
        data2 = resp2.get_json()
        assert data2.get("cache_hit") is True
