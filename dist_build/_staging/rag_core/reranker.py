"""
rag_core.reranker — Cross-Encoder Reranking Manager
=====================================================

Provides 30-50% precision boost by scoring (query, document) pairs
through a cross-encoder model.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model registry — ordered by quality
# ---------------------------------------------------------------------------

RERANKER_MODELS: List[str] = [
    "cross-encoder/ms-marco-MiniLM-L-12-v2",  # Best English
    "BAAI/bge-reranker-base",  # Good multilingual
    "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",  # Multilingual
    "cross-encoder/ms-marco-MiniLM-L-6-v2",  # Smaller / faster
]


class RerankerManager:
    """
    Manages cross-encoder reranking models.

    Loads the best available model with automatic fallback.
    """

    def __init__(self, model_name: Optional[str] = None):
        self._model_name = model_name
        self._model = None
        self._loaded_name: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def model_name(self) -> str:
        return self._loaded_name or "none"

    def load(self) -> bool:
        """Load the best available cross-encoder model."""
        try:
            from sentence_transformers import CrossEncoder
        except ImportError:
            logger.warning("sentence-transformers not installed — no reranking")
            return False

        models = ([self._model_name] if self._model_name else []) + RERANKER_MODELS

        for name in models:
            try:
                self._model = CrossEncoder(name)
                self._loaded_name = name
                logger.info("Loaded reranker: %s", name)
                return True
            except Exception as e:
                logger.debug("Failed to load reranker %s: %s", name, e)

        return False

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None,
    ) -> List[Tuple[int, float]]:
        """Rerank documents by relevance to query.

        Args:
            query: The search query.
            documents: List of document texts to rerank.
            top_k: Return only top-k results (None = all).

        Returns:
            List of (original_index, score) tuples, sorted by score desc.
        """
        if self._model is None:
            # No reranker — return original order with dummy scores
            n = top_k or len(documents)
            return [(i, 1.0 - i * 0.01) for i in range(min(n, len(documents)))]

        pairs = [[query, doc] for doc in documents]
        scores = self._model.predict(pairs)

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

        if top_k:
            ranked = ranked[:top_k]

        return [(idx, float(score)) for idx, score in ranked]
