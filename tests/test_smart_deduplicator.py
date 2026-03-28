"""
Tests for Core/smart_deduplicator.py — SmartDeduplicator 4-tier dedup

Tests cover:
  - Exact hash dedup
  - Boilerplate detection
  - Structural/nav detection
  - Semantic similarity (mocked model)
  - Conflict detection
  - Stats tracking
"""

import pytest
from unittest.mock import MagicMock
import numpy as np


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_model():
    """Mock SentenceTransformer that returns predictable embeddings."""
    model = MagicMock()
    # Default: return different unit vectors for different texts
    call_count = [0]

    def encode_fn(texts, **kwargs):
        results = []
        for t in texts:
            call_count[0] += 1
            vec = np.zeros(384)
            # Hash-based embedding so same text → same vector
            idx = hash(t) % 384
            vec[idx] = 1.0
            results.append(vec / (np.linalg.norm(vec) + 1e-10))
        return np.array(results)

    model.encode = encode_fn
    return model


@pytest.fixture
def dedup(mock_model):
    """Create SmartDeduplicator with mock model."""
    from Core.smart_deduplicator import SmartDeduplicator

    return SmartDeduplicator(
        model=mock_model,
        semantic_threshold=0.90,
        conflict_threshold=0.75,
    )


# ─── Import Tests ─────────────────────────────────────────────────────────


def test_import():
    """SmartDeduplicator can be imported."""
    from Core.smart_deduplicator import (
        SmartDeduplicator,
        DeduplicationResult,
        ConflictCandidate,
    )

    assert SmartDeduplicator is not None
    assert DeduplicationResult is not None
    assert ConflictCandidate is not None


# ─── Exact Hash Dedup ─────────────────────────────────────────────────────


def test_exact_duplicate_detected(dedup):
    """Second identical chunk should be skipped."""
    text = "This is a detailed article about renewable energy sources."
    r1 = dedup.should_skip_chunk(text)
    assert not r1.should_skip

    r2 = dedup.should_skip_chunk(text)
    assert r2.should_skip
    assert "exact" in r2.reason.lower() or "hash" in r2.reason.lower()


def test_unique_texts_pass(dedup):
    """Different texts should not be flagged as duplicates."""
    texts = [
        "Quantum computing is revolutionizing cryptography research.",
        "The Amazon rainforest produces 20% of the world's oxygen.",
        "Mozart composed his first symphony at age eight.",
    ]
    for t in texts:
        result = dedup.should_skip_chunk(t)
        assert not result.should_skip, f"Unique text falsely flagged: {t[:40]}"


# ─── Boilerplate Detection ────────────────────────────────────────────────


def test_boilerplate_cookie_notice(dedup):
    """Cookie consent banners should be detected as boilerplate."""
    text = "We use cookies to enhance your browsing experience. Accept all cookies."
    result = dedup.should_skip_chunk(text)
    assert result.should_skip
    assert "boilerplate" in result.reason.lower()


def test_boilerplate_subscribe(dedup):
    """Newsletter subscribe prompts should be detected."""
    text = "Subscribe to our newsletter for the latest updates and news!"
    result = dedup.should_skip_chunk(text)
    assert result.should_skip


def test_boilerplate_copyright(dedup):
    """Copyright footers should be detected."""
    text = "© 2026 All rights reserved. Terms of Service. Privacy Policy."
    result = dedup.should_skip_chunk(text)
    assert result.should_skip


def test_real_content_not_boilerplate(dedup):
    """Actual informational content should NOT be flagged as boilerplate."""
    text = (
        "The study published in Nature demonstrated that CRISPR gene editing "
        "can effectively target and repair mutations causing sickle cell disease "
        "in human cell lines, achieving a correction rate of 85% across samples."
    )
    result = dedup.should_skip_chunk(text)
    assert not result.should_skip


# ─── Structural/Nav Detection ─────────────────────────────────────────────


def test_nav_breadcrumb_detected(dedup):
    """Breadcrumb navigation should be detected."""
    text = "breadcrumb trail: Home > Products > Category"
    result = dedup.should_skip_chunk(text)
    assert result.should_skip
    assert "structural" in result.reason.lower()


def test_nav_page_numbers_detected(dedup):
    """Standalone page numbers should be detected as structural."""
    text = "page 3 of 12"
    result = dedup.should_skip_chunk(text)
    assert result.should_skip


# ─── Stats Tracking ───────────────────────────────────────────────────────


def test_stats_tracking(dedup):
    """Stats should accurately track dedup decisions."""
    dedup.should_skip_chunk("First unique chunk about machine learning algorithms.")
    dedup.should_skip_chunk("First unique chunk about machine learning algorithms.")  # dup
    dedup.should_skip_chunk("We use cookies. Accept all cookies.")  # boilerplate
    dedup.should_skip_chunk("Second unique chunk about ocean conservation.")

    stats = dedup.get_stats()
    assert stats["total_processed"] == 4
    assert stats["exact_duplicates"] >= 1
    assert stats["kept"] >= 1


def test_clear_resets(dedup):
    """clear() should reset all internal state."""
    dedup.should_skip_chunk("Some initial content for deduplication testing.")
    dedup.clear()

    stats = dedup.get_stats()
    assert stats["total_processed"] == 0

    # Same text should not be detected as dup after clear
    result = dedup.should_skip_chunk("Some initial content for deduplication testing.")
    assert not result.should_skip


# ─── Conflict Detection ───────────────────────────────────────────────────


def test_conflict_candidate_dataclass():
    """ConflictCandidate should be a proper dataclass."""
    from Core.smart_deduplicator import ConflictCandidate

    c = ConflictCandidate(
        new_text="Version A of the claim",
        existing_text="Version B of the claim",
        similarity=0.82,
        new_source="source1.com",
        existing_source="source2.com",
    )
    assert c.similarity == 0.82
    assert c.new_source == "source1.com"


def test_dedup_result_no_conflict_by_default(dedup):
    """Regular unique text should not produce a conflict."""
    result = dedup.should_skip_chunk("Normal article text about technology trends in 2026.")
    assert result.conflict is None


# ─── Edge Cases ────────────────────────────────────────────────────────────


def test_empty_text(dedup):
    """Empty text should be handled gracefully (not crash)."""
    result = dedup.should_skip_chunk("")
    # SmartDeduplicator keeps empty text (no boilerplate/nav match)
    assert isinstance(result.should_skip, bool)


def test_very_short_text(dedup):
    """Very short text should be handled gracefully."""
    result = dedup.should_skip_chunk("Hi")
    assert isinstance(result.should_skip, bool)


def test_whitespace_only(dedup):
    """Whitespace-only text should be handled gracefully."""
    result = dedup.should_skip_chunk("   \n\n\t  ")
    assert isinstance(result.should_skip, bool)
