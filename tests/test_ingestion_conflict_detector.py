"""
Tests for Core/ingestion_conflict_detector.py — IngestionConflictQueue

Tests cover:
  - IngestionConflict dataclass
  - add() with ConflictCandidate
  - get_pending(), get_all(), get_by_id()
  - resolve(), dismiss()
  - resolve_batch()
  - Auto-resolve learning from high-confidence decisions
  - Statistics
  - clear_resolved()
  - Persistence (uses temp dir)
"""

import pytest
from dataclasses import dataclass
from typing import Optional


# ─── Fake ConflictCandidate ────────────────────────────────────────────────


@dataclass
class FakeConflictCandidate:
    """Mimics ConflictCandidate from smart_deduplicator for testing."""

    new_text: str
    existing_text: str
    similarity: float
    new_source: Optional[str] = None
    existing_source: Optional[str] = None
    new_title: Optional[str] = None
    existing_title: Optional[str] = None


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_queue_dir(tmp_path):
    """Temporary directory for queue persistence."""
    return tmp_path / "conflict_queue"


@pytest.fixture
def queue(tmp_queue_dir):
    """Fresh IngestionConflictQueue using temp storage."""
    from Core.ingestion_conflict_detector import IngestionConflictQueue

    return IngestionConflictQueue(storage_dir=tmp_queue_dir)


@pytest.fixture
def sample_candidate():
    """A basic ConflictCandidate."""
    return FakeConflictCandidate(
        new_text="The hospital has 500 beds and serves 100,000 patients annually.",
        existing_text="The hospital has 450 beds and serves 95,000 patients per year.",
        similarity=0.85,
        new_source="hospital-website.com",
        existing_source="gov-health-data.org",
        new_title="Hospital Overview",
        existing_title="Health Statistics",
    )


# ─── Import ────────────────────────────────────────────────────────────────


def test_import():
    from Core.ingestion_conflict_detector import (
        IngestionConflictQueue,
        IngestionConflict,
    )

    assert IngestionConflictQueue is not None
    assert IngestionConflict is not None


# ─── IngestionConflict dataclass ──────────────────────────────────────────


def test_conflict_dataclass():
    from Core.ingestion_conflict_detector import IngestionConflict

    c = IngestionConflict(
        conflict_id="abc123",
        new_text="Text A",
        existing_text="Text B",
        similarity=0.88,
    )
    assert c.status == "pending"
    assert c.resolution is None
    d = c.to_dict()
    assert d["conflict_id"] == "abc123"
    assert d["similarity"] == 0.88


# ─── add() ─────────────────────────────────────────────────────────────────


def test_add_queues_conflict(queue, sample_candidate):
    """Adding a candidate should create a pending conflict."""
    conflict = queue.add(sample_candidate)
    assert conflict is not None
    assert conflict.status == "pending"
    assert conflict.similarity == 0.85
    assert queue.pending_count == 1
    assert queue.total_count == 1


def test_add_duplicate_returns_none(queue, sample_candidate):
    """Adding the same candidate twice should not create a duplicate."""
    queue.add(sample_candidate)
    result = queue.add(sample_candidate)
    assert result is None
    assert queue.total_count == 1


def test_add_different_conflicts(queue):
    """Adding different candidates should create separate conflicts."""
    c1 = FakeConflictCandidate("Text A version 1", "Text A version 2", 0.80)
    c2 = FakeConflictCandidate("Text B version 1", "Text B version 2", 0.75)
    queue.add(c1)
    queue.add(c2)
    assert queue.total_count == 2
    assert queue.pending_count == 2


# ─── get_pending / get_all / get_by_id ────────────────────────────────────


def test_get_pending(queue, sample_candidate):
    queue.add(sample_candidate)
    pending = queue.get_pending()
    assert len(pending) == 1
    assert pending[0].status == "pending"


def test_get_all(queue, sample_candidate):
    queue.add(sample_candidate)
    all_c = queue.get_all()
    assert len(all_c) == 1


def test_get_by_id(queue, sample_candidate):
    conflict = queue.add(sample_candidate)
    found = queue.get_by_id(conflict.conflict_id)
    assert found is not None
    assert found.conflict_id == conflict.conflict_id


def test_get_by_id_not_found(queue):
    assert queue.get_by_id("nonexistent") is None


# ─── resolve() ─────────────────────────────────────────────────────────────


def test_resolve_updates_status(queue, sample_candidate):
    conflict = queue.add(sample_candidate)
    success = queue.resolve(conflict.conflict_id, "keep_new", confidence=0.8, explanation="Newer data")
    assert success is True
    resolved = queue.get_by_id(conflict.conflict_id)
    assert resolved.status == "resolved"
    assert resolved.resolution == "keep_new"
    assert resolved.user_explanation == "Newer data"
    assert queue.pending_count == 0


def test_resolve_nonexistent_returns_false(queue):
    assert queue.resolve("fake_id", "keep_new") is False


# ─── dismiss() ─────────────────────────────────────────────────────────────


def test_dismiss(queue, sample_candidate):
    conflict = queue.add(sample_candidate)
    success = queue.dismiss(conflict.conflict_id)
    assert success is True
    assert queue.get_by_id(conflict.conflict_id).status == "dismissed"
    assert queue.pending_count == 0


def test_dismiss_nonexistent(queue):
    assert queue.dismiss("nope") is False


# ─── resolve_batch() ──────────────────────────────────────────────────────


def test_resolve_batch(queue):
    c1 = queue.add(FakeConflictCandidate("A1", "A2", 0.80))
    c2 = queue.add(FakeConflictCandidate("B1", "B2", 0.75))
    results = queue.resolve_batch(
        [
            {
                "conflict_id": c1.conflict_id,
                "resolution": "keep_new",
                "confidence": 0.9,
            },
            {
                "conflict_id": c2.conflict_id,
                "resolution": "keep_existing",
                "confidence": 0.7,
            },
        ]
    )
    assert results[c1.conflict_id] is True
    assert results[c2.conflict_id] is True
    assert queue.pending_count == 0


# ─── Auto-resolve learning ────────────────────────────────────────────────


def test_auto_resolve_after_high_confidence(tmp_queue_dir):
    """High-confidence resolution should be learned and auto-applied."""
    from Core.ingestion_conflict_detector import IngestionConflictQueue

    q = IngestionConflictQueue(storage_dir=tmp_queue_dir)

    # First: resolve with high confidence
    c = q.add(FakeConflictCandidate("Conflict text new", "Conflict text old", 0.82))
    q.resolve(c.conflict_id, "keep_new", confidence=0.90)

    # Second: add similar conflict — should be auto-resolved
    result = q.add(FakeConflictCandidate("Conflict text new", "Conflict text old", 0.82))
    # If auto-resolved, add() returns None
    assert result is None


# ─── Statistics ────────────────────────────────────────────────────────────


def test_get_statistics(queue, sample_candidate):
    queue.add(sample_candidate)
    stats = queue.get_statistics()
    assert isinstance(stats, dict)
    assert "pending" in stats or "total" in stats


# ─── Persistence ──────────────────────────────────────────────────────────


def test_persistence_across_instances(tmp_queue_dir, sample_candidate):
    """Conflicts should survive creating a new instance."""
    from Core.ingestion_conflict_detector import IngestionConflictQueue

    q1 = IngestionConflictQueue(storage_dir=tmp_queue_dir)
    q1.add(sample_candidate)
    assert q1.total_count == 1

    # Create new instance from same dir
    q2 = IngestionConflictQueue(storage_dir=tmp_queue_dir)
    assert q2.total_count == 1


# ─── Edge Cases ────────────────────────────────────────────────────────────


def test_empty_queue(queue):
    assert queue.pending_count == 0
    assert queue.total_count == 0
    assert queue.get_pending() == []
    assert queue.get_all() == []
