"""
rag_core.dedup — Deduplication Manager
========================================

Hash-based and vector-based near-duplicate detection for indexed content.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


class DeduplicationManager:
    """
    Handles deduplication of chunks/documents before indexing.

    Two tiers:
    1. **Exact** — SHA-256 content hash
    2. **Near-duplicate** — cosine similarity above threshold
    """

    def __init__(self, similarity_threshold: float = 0.95):
        self.similarity_threshold = similarity_threshold
        self._seen_hashes: Set[str] = set()

    @property
    def seen_count(self) -> int:
        return len(self._seen_hashes)

    def content_hash(self, text: str) -> str:
        """SHA-256 hash of text content."""
        return hashlib.sha256(text.strip().encode()).hexdigest()

    def is_duplicate_hash(self, text: str) -> bool:
        """Check if text has been seen before (exact match)."""
        h = self.content_hash(text)
        if h in self._seen_hashes:
            return True
        self._seen_hashes.add(h)
        return False

    def find_near_duplicates(
        self,
        embedding,
        existing_embeddings,
    ) -> bool:
        """Check if a vector is near-duplicate of any existing vector.

        Args:
            embedding: numpy array of shape (dim,).
            existing_embeddings: numpy array of shape (n, dim).

        Returns:
            True if a near-duplicate is found.
        """
        if existing_embeddings is None or len(existing_embeddings) == 0:
            return False

        import numpy as np

        sims = existing_embeddings @ embedding
        return bool(np.max(sims) >= self.similarity_threshold)

    def deduplicate_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Remove exact-duplicate chunks from a list."""
        unique: List[Dict[str, Any]] = []
        for chunk in chunks:
            text = chunk.get("text", "")
            if not self.is_duplicate_hash(text):
                unique.append(chunk)
        return unique

    def reset(self):
        """Clear the dedup state."""
        self._seen_hashes.clear()
