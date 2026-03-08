"""
rag_core.search — Unified Search Result + Hybrid Searcher
==========================================================

Combines dense retrieval, BM25, RRF fusion, and cross-encoder reranking
into a single, composable search pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from rag_core.bm25_index import BM25Index
from rag_core.embeddings import EmbeddingManager
from rag_core.fusion import reciprocal_rank_fusion
from rag_core.reranker import RerankerManager

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Standard search result across all projects."""

    text: str
    score: float
    index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Convenience accessors
    @property
    def key(self) -> str:
        return self.metadata.get("key", self.metadata.get("func_key", ""))

    @property
    def name(self) -> str:
        return self.metadata.get("name", self.metadata.get("title", ""))

    @property
    def url(self) -> str:
        return self.metadata.get("url", self.metadata.get("file_path", ""))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "score": self.score,
            "index": self.index,
            **self.metadata,
        }


class HybridSearcher:
    """
    Composable hybrid search pipeline.

    Uses whichever components are available::

        Query  ─┬─► Dense (embedding)  ──► top-N ─┐
                │                                   │
                └─► BM25 (keyword)     ──► top-N ─┤
                                                   │
                                            RRF Fusion ──► top-M
                                                   │
                                        Cross-Encoder ──► top-K

    All components are optional:
    - No embeddings? BM25-only mode.
    - No BM25? Dense-only mode.
    - No reranker? Skip reranking.
    """

    def __init__(
        self,
        embeddings: Optional[EmbeddingManager] = None,
        bm25: Optional[BM25Index] = None,
        reranker: Optional[RerankerManager] = None,
        rrf_k: int = 60,
        dense_weight: float = 0.6,
    ):
        self.embeddings = embeddings
        self.bm25 = bm25
        self.reranker = reranker
        self.rrf_k = rrf_k
        self.dense_weight = dense_weight

        # In-memory document store
        self._documents: List[Dict[str, Any]] = []
        self._doc_embeddings = None  # numpy array

    @property
    def doc_count(self) -> int:
        return len(self._documents)

    def index_documents(
        self,
        documents: List[Dict[str, Any]],
        *,
        progress: Optional[Callable[[str, float], None]] = None,
    ) -> int:
        """Index documents for searching.

        Each document should have at least ``{"text": "..."}``.
        Additional keys become metadata.

        Returns the number of documents indexed.
        """
        self._documents = documents
        texts = [d["text"] for d in documents]

        # Build dense embeddings
        if self.embeddings and self.embeddings.is_loaded:
            import numpy as np

            if progress:
                progress("Encoding embeddings ...", 0.3)

            all_embs = []
            batch = 32
            total = len(texts)
            for i in range(0, total, batch):
                chunk = texts[i : i + batch]
                emb = self.embeddings.encode(chunk, batch_size=batch)
                all_embs.append(emb)
                if progress:
                    pct = 0.3 + 0.4 * min(i + batch, total) / total
                    progress(f"Embedding [{min(i + batch, total)}/{total}]", pct)

            self._doc_embeddings = np.vstack(all_embs) if all_embs else None

        # Build BM25 index
        if self.bm25:
            if progress:
                progress("Building BM25 index ...", 0.75)
            self.bm25.build(texts)

        if progress:
            progress(f"Indexed {len(documents)} documents", 1.0)

        return len(documents)

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        use_reranking: bool = True,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Run the full hybrid search pipeline.

        Args:
            query: Search query (natural language or code).
            top_k: Number of final results.
            use_reranking: Enable cross-encoder reranking.
            min_score: Minimum score threshold.
            filters: Metadata filters (exact match).

        Returns:
            List of :class:`SearchResult` sorted by relevance.
        """
        if not self._documents:
            return []

        retrieve_k = max(top_k * 5, 50)
        rankings: list = []
        weights: list = []

        # -- Dense retrieval -----------------------------------------------
        if self._doc_embeddings is not None and self.embeddings:
            q_vec = self.embeddings.encode_single(query, normalize=True)
            sims = self.embeddings.cosine_similarity(q_vec, self._doc_embeddings)

            import numpy as np

            top_idx = np.argsort(sims)[::-1][:retrieve_k]
            dense_scores = {int(i): float(sims[i]) for i in top_idx if sims[i] > 0}
            rankings.append(dense_scores)
            weights.append(self.dense_weight)

        # -- BM25 retrieval ------------------------------------------------
        if self.bm25 and self.bm25.indexed:
            bm25_scores = self.bm25.search(query, k=retrieve_k)
            rankings.append(bm25_scores)
            weights.append(1.0 - self.dense_weight)

        if not rankings:
            return []

        # -- RRF Fusion ----------------------------------------------------
        if len(rankings) > 1:
            fused = reciprocal_rank_fusion(*rankings, k=self.rrf_k, weights=weights)
        else:
            fused = rankings[0]

        # -- Apply metadata filters ----------------------------------------
        if filters:
            fused = self._apply_filters(fused, filters)

        # -- Select candidates for reranking -------------------------------
        candidates_k = min(top_k * 3, 20) if use_reranking else top_k
        top_indices = sorted(fused, key=lambda idx: fused[idx], reverse=True)[:candidates_k]

        # -- Cross-encoder reranking ---------------------------------------
        if use_reranking and self.reranker and self.reranker.is_loaded and len(top_indices) > top_k:
            docs_to_rerank = [self._documents[i]["text"] for i in top_indices]
            reranked = self.reranker.rerank(query, docs_to_rerank, top_k=top_k)
            top_indices = [top_indices[orig_idx] for orig_idx, _ in reranked]

        # -- Build results -------------------------------------------------
        results: List[SearchResult] = []
        for idx in top_indices[:top_k]:
            score = fused.get(idx, 0.0)
            if score < min_score:
                continue
            doc = self._documents[idx]
            meta = {k: v for k, v in doc.items() if k != "text"}
            results.append(
                SearchResult(
                    text=doc["text"],
                    score=round(score, 4),
                    index=idx,
                    metadata=meta,
                )
            )

        return results

    def _apply_filters(self, scores: Dict[int, float], filters: Dict[str, Any]) -> Dict[int, float]:
        """Apply exact-match metadata filters."""
        filtered: Dict[int, float] = {}
        for idx, score in scores.items():
            doc = self._documents[idx]
            meta = doc.get("metadata", doc)
            match = True
            for key, value in filters.items():
                if key in meta:
                    if isinstance(meta[key], list):
                        if value not in meta[key]:
                            match = False
                    elif meta[key] != value:
                        match = False
                elif key in doc:
                    if doc[key] != value:
                        match = False
            if match:
                filtered[idx] = score
        return filtered
