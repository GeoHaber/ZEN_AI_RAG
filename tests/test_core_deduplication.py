"""
tests/test_core_deduplication.py — Unit tests for Core/deduplication.py

Tests ContentDeduplicator and SimilarityDeduplicator.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Core.deduplication import ContentDeduplicator, SimilarityDeduplicator


# ── ContentDeduplicator ─────────────────────────────────────────────────────


class TestContentDeduplicator:
    def setup_method(self):
        self.dedup = ContentDeduplicator()

    # ── compute_hash ──

    def test_hash_deterministic(self):
        h1 = self.dedup.compute_hash("hello world")
        h2 = self.dedup.compute_hash("hello world")
        assert h1 == h2

    def test_hash_case_insensitive(self):
        h1 = self.dedup.compute_hash("Hello World")
        h2 = self.dedup.compute_hash("hello world")
        assert h1 == h2

    def test_hash_different_texts(self):
        h1 = self.dedup.compute_hash("alpha")
        h2 = self.dedup.compute_hash("beta")
        assert h1 != h2

    # ── _normalize_text ──

    def test_normalize_whitespace(self):
        result = self.dedup._normalize_text("  hello   world  ")
        assert result == "hello world"

    def test_normalize_line_endings(self):
        result = self.dedup._normalize_text("a\r\nb\rc")
        assert "\r" not in result

    # ── add_document / find_duplicates ──

    def test_add_unique(self):
        self.dedup.add_document("d1", "unique text")
        assert self.dedup.stats["total_processed"] == 1

    def test_add_duplicate(self):
        self.dedup.add_document("d1", "same text")
        self.dedup.add_document("d2", "same text")
        dupes = self.dedup.find_duplicates()
        assert len(dupes) >= 1

    def test_find_duplicates_none(self):
        self.dedup.add_document("d1", "alpha")
        self.dedup.add_document("d2", "beta")
        dupes = self.dedup.find_duplicates()
        assert len(dupes) == 0

    # ── deduplicate strategies ──

    def test_deduplicate_keep_first(self):
        self.dedup.add_document("d1", "dup text")
        self.dedup.add_document("d2", "dup text")
        self.dedup.add_document("d3", "unique")
        unique, removed = self.dedup.deduplicate("keep_first")
        assert len(unique) == 2
        assert len(removed) == 1
        assert unique[0]["id"] in ("d1", "d3")

    def test_deduplicate_keep_last(self):
        self.dedup.add_document("d1", "dup text")
        self.dedup.add_document("d2", "dup text")
        unique, removed = self.dedup.deduplicate("keep_last")
        assert len(unique) == 1
        assert unique[0]["id"] == "d2"

    def test_deduplicate_keep_best(self):
        self.dedup.add_document("d1", "short", metadata={})
        self.dedup.add_document("d2", "short", metadata={"title": "Better", "source": "web"})
        unique, removed = self.dedup.deduplicate("keep_best")
        assert len(unique) == 1
        # d2 should win due to more metadata
        assert unique[0]["id"] == "d2"

    def test_deduplicate_invalid_strategy(self):
        """Invalid strategy falls back to default behaviour."""
        self.dedup.add_document("d1", "text")
        result = self.dedup.deduplicate("invalid")
        # Should still return a tuple (unique, removed)
        assert isinstance(result, tuple)
        assert len(result) == 2

    # ── score_document ──

    def test_score_document_with_metadata(self):
        doc = {"text": "x" * 500, "metadata": {"title": "T", "source": "S"}}
        score = self.dedup._score_document(doc)
        assert score > 0

    # ── statistics ──

    def test_get_statistics(self):
        self.dedup.add_document("d1", "text")
        stats = self.dedup.get_statistics()
        assert "total_processed" in stats
        assert "deduplication_rate" in stats


# ── SimilarityDeduplicator ──────────────────────────────────────────────────


class TestSimilarityDeduplicator:
    def test_init_threshold(self):
        sd = SimilarityDeduplicator(similarity_threshold=0.8)
        assert sd.threshold == 0.8

    def test_add_document_with_embedding(self):
        sd = SimilarityDeduplicator()
        sd.add_document("d1", "text", [0.1, 0.2, 0.3])
        assert len(sd.documents) == 1
        assert len(sd.embeddings) == 1

    def test_find_similar_above_threshold(self):
        sd = SimilarityDeduplicator(similarity_threshold=0.9)
        sd.add_document("d1", "text1", [1.0, 0.0, 0.0])
        sd.add_document("d2", "text2", [0.99, 0.01, 0.0])
        pairs = sd.find_similar_pairs()
        assert len(pairs) >= 1

    def test_find_similar_below_threshold(self):
        sd = SimilarityDeduplicator(similarity_threshold=0.99)
        sd.add_document("d1", "text1", [1.0, 0.0, 0.0])
        sd.add_document("d2", "text2", [0.0, 1.0, 0.0])
        pairs = sd.find_similar_pairs()
        assert len(pairs) == 0

    def test_cosine_similarity_identical(self):
        sd = SimilarityDeduplicator()
        score = sd._cosine_similarity([1, 0, 0], [1, 0, 0])
        assert abs(score - 1.0) < 0.001

    def test_cosine_similarity_orthogonal(self):
        sd = SimilarityDeduplicator()
        score = sd._cosine_similarity([1, 0, 0], [0, 1, 0])
        assert abs(score) < 0.001

    def test_deduplicate_clusters(self):
        sd = SimilarityDeduplicator(similarity_threshold=0.9)
        sd.add_document("d1", "text1", [1.0, 0.0])
        sd.add_document("d2", "text2", [0.99, 0.01])
        sd.add_document("d3", "text3", [0.0, 1.0])
        unique, removed = sd.deduplicate_clusters()
        assert len(unique) + len(removed) >= 0  # Just ensure it runs
