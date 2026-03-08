"""
rag_core.cache — Semantic Cache
=================================

Two-tier cache for RAG search results:
1. **Exact** — hash-based lookup
2. **Semantic** — cosine similarity of query embeddings
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SemanticCache:
    """
    Two-tier cache: exact match → semantic similarity.

    Used to avoid re-searching for identical or very similar queries.
    """

    def __init__(
        self,
        max_entries: int = 500,
        ttl: float = 600.0,
        similarity_threshold: float = 0.92,
        encoder=None,
    ):
        self.max_entries = max_entries
        self.ttl = ttl
        self.similarity_threshold = similarity_threshold
        self._encoder = encoder

        # Exact cache: {query_hash: (timestamp, results)}
        self._exact: Dict[str, tuple] = {}

        # Semantic cache: [(query_embedding, timestamp, results)]
        self._semantic: List[tuple] = []

    def _hash(self, query: str) -> str:
        return hashlib.sha256(query.strip().lower().encode()).hexdigest()

    def _now(self) -> float:
        return time.time()

    def _evict_expired(self):
        """Remove expired entries."""
        now = self._now()
        self._exact = {k: v for k, v in self._exact.items() if now - v[0] < self.ttl}
        self._semantic = [entry for entry in self._semantic if now - entry[1] < self.ttl]

    def get(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Look up cached results for a query.

        Returns None on cache miss.
        """
        self._evict_expired()

        # Tier 1: exact match
        h = self._hash(query)
        if h in self._exact:
            logger.debug("Cache HIT (exact): %s", query[:50])
            return self._exact[h][1]

        # Tier 2: semantic similarity
        if self._encoder is not None and self._semantic:
            try:
                import numpy as np

                q_emb = self._encoder.encode_single(query, normalize=True)
                for emb, ts, results in self._semantic:
                    sim = float(np.dot(q_emb, emb))
                    if sim >= self.similarity_threshold:
                        logger.debug("Cache HIT (semantic, %.3f): %s", sim, query[:50])
                        return results
            except Exception:
                pass

        return None

    def set(self, query: str, results: List[Dict[str, Any]]):
        """Store results in both cache tiers."""
        now = self._now()

        # Tier 1: exact
        h = self._hash(query)
        self._exact[h] = (now, results)

        # Tier 2: semantic
        if self._encoder is not None:
            try:
                emb = self._encoder.encode_single(query, normalize=True)
                self._semantic.append((emb, now, results))
            except Exception:
                pass

        # Evict oldest if over capacity
        while len(self._exact) > self.max_entries:
            oldest = min(self._exact, key=lambda k: self._exact[k][0])
            del self._exact[oldest]

        while len(self._semantic) > self.max_entries:
            self._semantic.pop(0)

    def clear(self):
        """Wipe all cached data."""
        self._exact.clear()
        self._semantic.clear()

    @property
    def size(self) -> int:
        return len(self._exact)
