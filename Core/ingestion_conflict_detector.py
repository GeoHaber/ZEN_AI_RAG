"""
Core/ingestion_conflict_detector.py — HITL Conflict Queue for RAG Ingestion

When the SmartDeduplicator finds chunks that are semantically similar but
textually different (potential conflicts), this module:
  1. Queues them for human review
  2. Provides a batch review API for the Streamlit UI
  3. Records user decisions and updates chunk metadata in Qdrant
  4. Learns from past decisions to auto-resolve trivial conflicts

Integrates with:
  - Core/smart_deduplicator.py (ConflictCandidate input)
  - Core/human_loop_resolver.py (HumanLoopConflictResolver)
  - ui/human_conflict_ui.py (Streamlit display)
  - zena_mode/rag_pipeline.py (Qdrant metadata updates)

Usage (in rag_pipeline.py build_index):
    conflict_queue = IngestionConflictQueue()

    for chunk in chunks:
        result = dedup.should_skip_chunk(text, embedding)
        if result.conflict:
            conflict_queue.add(result.conflict)

    # After ingestion, present conflicts in UI
    pending = conflict_queue.get_pending()
"""

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class IngestionConflict:
    """
    A pair of chunks flagged during ingestion as semantically similar
    but containing potentially conflicting information.
    """

    conflict_id: str
    new_text: str
    existing_text: str
    similarity: float
    new_source: Optional[str] = None
    existing_source: Optional[str] = None
    new_title: Optional[str] = None
    existing_title: Optional[str] = None
    detected_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending | resolved | auto_resolved | dismissed
    resolution: Optional[str] = None  # keep_new | keep_existing | keep_both | discard_both
    user_confidence: float = 0.0
    user_explanation: Optional[str] = None
    resolved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IngestionConflictQueue:
    """
    Manages a queue of conflicts detected during RAG ingestion.

    Persists to disk so conflicts survive app restarts.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path("data/conflict_queue")
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(
                "[ConflictQueue] Could not create storage dir %s: %s",
                self.storage_dir,
                e,
            )
        self._queue: List[IngestionConflict] = []
        self._auto_resolve_cache: Dict[str, str] = {}  # fingerprint → resolution
        self._load()

    # =====================================================================
    # ADDING CONFLICTS
    # =====================================================================

    def add(self, conflict_candidate) -> Optional[IngestionConflict]:
        """
        Add a ConflictCandidate from SmartDeduplicator to the queue.

        Args:
            conflict_candidate: ConflictCandidate dataclass from smart_deduplicator.py

        Returns:
            IngestionConflict if queued, None if auto-resolved.
        """
        # Generate stable ID
        cid = hashlib.md5(
            f"{conflict_candidate.new_text[:100]}|{conflict_candidate.existing_text[:100]}".encode()
        ).hexdigest()[:12]

        # Check for duplicate conflict
        if any(c.conflict_id == cid for c in self._queue):
            return None

        # Check auto-resolve cache (learned from past decisions)
        fingerprint = self._fingerprint(conflict_candidate.new_text, conflict_candidate.existing_text)
        if fingerprint in self._auto_resolve_cache:
            resolution = self._auto_resolve_cache[fingerprint]
            logger.info(f"[ConflictQueue] Auto-resolved conflict {cid} → {resolution}")
            conflict = IngestionConflict(
                conflict_id=cid,
                new_text=conflict_candidate.new_text,
                existing_text=conflict_candidate.existing_text,
                similarity=conflict_candidate.similarity,
                new_source=conflict_candidate.new_source,
                existing_source=conflict_candidate.existing_source,
                new_title=conflict_candidate.new_title,
                existing_title=conflict_candidate.existing_title,
                detected_at=getattr(conflict_candidate, "detected_at", time.time()),
                status="auto_resolved",
                resolution=resolution,
                resolved_at=time.time(),
            )
            self._queue.append(conflict)
            self._save_one(conflict)
            return None

        # Queue for human review
        conflict = IngestionConflict(
            conflict_id=cid,
            new_text=conflict_candidate.new_text,
            existing_text=conflict_candidate.existing_text,
            similarity=conflict_candidate.similarity,
            new_source=conflict_candidate.new_source,
            existing_source=conflict_candidate.existing_source,
            new_title=conflict_candidate.new_title,
            existing_title=conflict_candidate.existing_title,
            detected_at=getattr(conflict_candidate, "detected_at", time.time()),
        )
        self._queue.append(conflict)
        self._save_one(conflict)

        logger.info(f"[ConflictQueue] Queued conflict {cid} (sim={conflict_candidate.similarity:.2f})")
        return conflict

    # =====================================================================
    # RETRIEVING CONFLICTS
    # =====================================================================

    def get_pending(self) -> List[IngestionConflict]:
        """Get all unresolved conflicts."""
        return [c for c in self._queue if c.status == "pending"]

    def get_all(self) -> List[IngestionConflict]:
        """Get all conflicts (pending + resolved)."""
        return list(self._queue)

    def get_by_id(self, conflict_id: str) -> Optional[IngestionConflict]:
        """Get a specific conflict by ID."""
        for c in self._queue:
            if c.conflict_id == conflict_id:
                return c
        return None

    @property
    def pending_count(self) -> int:
        return sum(1 for c in self._queue if c.status == "pending")

    @property
    def total_count(self) -> int:
        return len(self._queue)

    # =====================================================================
    # RESOLVING CONFLICTS
    # =====================================================================

    def resolve(
        self,
        conflict_id: str,
        resolution: str,
        confidence: float = 0.7,
        explanation: Optional[str] = None,
    ) -> bool:
        """
        Record user's resolution for a conflict.

        Args:
            conflict_id: ID of the conflict to resolve.
            resolution: One of "keep_new", "keep_existing", "keep_both", "discard_both".
            confidence: User confidence in the decision (0–1).
            explanation: Optional free-text explanation.

        Returns:
            True if conflict was found and resolved.
        """
        conflict = self.get_by_id(conflict_id)
        if not conflict:
            return False

        conflict.status = "resolved"
        conflict.resolution = resolution
        conflict.user_confidence = confidence
        conflict.user_explanation = explanation
        conflict.resolved_at = time.time()

        self._save_one(conflict)

        # Learn from high-confidence decisions for auto-resolution
        if confidence >= 0.85:
            fingerprint = self._fingerprint(conflict.new_text, conflict.existing_text)
            self._auto_resolve_cache[fingerprint] = resolution
            self._save_auto_resolve()

        logger.info(f"[ConflictQueue] Resolved {conflict_id} → {resolution} (confidence={confidence:.0%})")
        return True

    def dismiss(self, conflict_id: str) -> bool:
        """Dismiss a conflict without resolution."""
        conflict = self.get_by_id(conflict_id)
        if not conflict:
            return False
        conflict.status = "dismissed"
        conflict.resolved_at = time.time()
        self._save_one(conflict)
        return True

    def resolve_batch(self, resolutions: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Resolve multiple conflicts at once.

        Args:
            resolutions: List of {conflict_id, resolution, confidence?, explanation?}

        Returns:
            {conflict_id: success_bool}
        """
        results = {}
        for r in resolutions:
            cid = r["conflict_id"]
            results[cid] = self.resolve(
                cid,
                r["resolution"],
                r.get("confidence", 0.7),
                r.get("explanation"),
            )
        return results

    # =====================================================================
    # STATISTICS
    # =====================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get queue statistics."""
        pending = [c for c in self._queue if c.status == "pending"]
        resolved = [c for c in self._queue if c.status == "resolved"]
        auto_resolved = [c for c in self._queue if c.status == "auto_resolved"]
        dismissed = [c for c in self._queue if c.status == "dismissed"]

        return {
            "total": len(self._queue),
            "pending": len(pending),
            "resolved": len(resolved),
            "auto_resolved": len(auto_resolved),
            "dismissed": len(dismissed),
            "avg_similarity": (sum(c.similarity for c in self._queue) / len(self._queue) if self._queue else 0.0),
            "avg_confidence": (sum(c.user_confidence for c in resolved) / len(resolved) if resolved else 0.0),
            "auto_resolve_patterns": len(self._auto_resolve_cache),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Alias for get_statistics() for UI compatibility (e.g. conflict_queue_panel)."""
        return self.get_statistics()

    # =====================================================================
    # PERSISTENCE
    # =====================================================================

    def _save_one(self, conflict: IngestionConflict):
        """Persist one conflict to disk."""
        path = self.storage_dir / f"{conflict.conflict_id}.json"
        try:
            path.write_text(json.dumps(conflict.to_dict(), indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[ConflictQueue] Save failed for {conflict.conflict_id}: {e}")

    def _load(self):
        """Load all conflicts from disk."""
        self._queue.clear()
        for path in sorted(self.storage_dir.glob("*.json")):
            if path.name == "_auto_resolve.json":
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                conflict = IngestionConflict(**data)
                self._queue.append(conflict)
            except Exception as e:
                logger.warning(f"[ConflictQueue] Load failed for {path.name}: {e}")

        # Load auto-resolve cache
        ar_path = self.storage_dir / "_auto_resolve.json"
        if ar_path.exists():
            try:
                self._auto_resolve_cache = json.loads(ar_path.read_text(encoding="utf-8"))
            except Exception:
                self._auto_resolve_cache = {}

        if self._queue:
            pending = sum(1 for c in self._queue if c.status == "pending")
            logger.info(f"[ConflictQueue] Loaded {len(self._queue)} conflicts ({pending} pending)")

    def _save_auto_resolve(self):
        """Persist auto-resolve cache."""
        path = self.storage_dir / "_auto_resolve.json"
        try:
            path.write_text(json.dumps(self._auto_resolve_cache, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug("%s", exc)

    def _fingerprint(self, text_a: str, text_b: str) -> str:
        """
        Create a content-level fingerprint for auto-resolution learning.
        Uses sorted content-word sets so order doesn't matter.
        """
        stopwords = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
        }
        a_words = sorted(set(text_a.lower().split()) - stopwords)[:15]
        b_words = sorted(set(text_b.lower().split()) - stopwords)[:15]
        combined = "|".join(a_words) + "||" + "|".join(b_words)
        return hashlib.md5(combined.encode()).hexdigest()[:12]

    def clear_resolved(self):
        """Remove resolved/dismissed conflicts from queue and disk."""
        to_remove = [c for c in self._queue if c.status in ("resolved", "dismissed", "auto_resolved")]
        for c in to_remove:
            path = self.storage_dir / f"{c.conflict_id}.json"
            try:
                path.unlink(missing_ok=True)
            except Exception as exc:
                logger.debug("%s", exc)
        self._queue = [c for c in self._queue if c.status == "pending"]
