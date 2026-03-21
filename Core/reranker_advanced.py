"""
Core/reranker_advanced.py — 5-Factor Advanced Reranker for RAG Pipeline.

Scoring factors:
  1. Semantic relevance (40%) — CrossEncoder semantic similarity
  2. Position boost (10%) — original retrieval position
  3. Keyword density (15%) — query keyword concentration
  4. Answer-type alignment (25%) — does chunk match expected answer type
  5. Source credibility (10%) — TLD and domain reputation

Ported from ZEN_RAG.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AdvancedReranker:
    """5-factor reranker for RAG search results.

    Uses CrossEncoder for semantic scoring + heuristic signals
    for position, density, answer-type, and source credibility.

    Usage:
        reranker = AdvancedReranker()
        reranked = reranker.rerank(query, chunks, top_k=5)
    """

    # Factor weights
    W_SEMANTIC = 0.40
    W_POSITION = 0.10
    W_DENSITY = 0.15
    W_ANSWER_TYPE = 0.25
    W_SOURCE = 0.10

    # Source credibility scores
    SOURCE_CREDIBILITY = {
        "wikipedia.org": 0.85,
        "arxiv.org": 0.90,
        "nature.com": 0.95,
        "science.org": 0.95,
        "pubmed": 0.92,
        "nih.gov": 0.93,
        "springer.com": 0.88,
        "ieee.org": 0.90,
        "acm.org": 0.88,
        "reuters.com": 0.82,
        "bbc.com": 0.80,
        "nytimes.com": 0.80,
    }

    # Answer type patterns
    ANSWER_TYPE_PATTERNS = {
        "definition": re.compile(r"\b(what\s+is|define|meaning\s+of|definition)\b", re.I),
        "list": re.compile(r"\b(list|enumerate|what\s+are|name\s+the|types\s+of)\b", re.I),
        "number": re.compile(r"\b(how\s+many|how\s+much|number\s+of|count|percentage)\b", re.I),
        "person": re.compile(r"\b(who\s+(is|was|are|were)|author|creator|founder)\b", re.I),
        "date": re.compile(r"\b(when|what\s+(year|date|time)|since\s+when)\b", re.I),
        "location": re.compile(r"\b(where|location|country|city|region)\b", re.I),
        "comparison": re.compile(r"\b(compare|versus|vs\.?|differ|difference|better)\b", re.I),
        "process": re.compile(r"\b(how\s+to|steps|process|procedure|method)\b", re.I),
        "reason": re.compile(r"\b(why|reason|cause|because|purpose)\b", re.I),
    }

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self._model = None
        self._model_name = model_name

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self._model_name)
                logger.info(f"[Reranker] Loaded CrossEncoder: {self._model_name}")
            except Exception as e:
                logger.warning(f"[Reranker] CrossEncoder not available: {e}")
        return self._model

    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Rerank chunks using 5-factor scoring."""
        if not chunks:
            return []

        if len(chunks) == 1:
            chunks[0]["rerank_score"] = 1.0
            return chunks

        try:
            import numpy as np
        except ImportError:
            logger.warning("[Reranker] numpy not available — returning original order")
            return chunks[:top_k]

        n = len(chunks)
        texts = [c.get("text", "") for c in chunks]

        # Factor 1: Semantic scores
        semantic_scores = self._score_semantic(query, texts)

        # Factor 2: Position scores
        position_scores = np.array([1.0 / (i + 1) for i in range(n)])
        if position_scores.max() > 0:
            position_scores /= position_scores.max()

        # Factor 3: Keyword density
        density_scores = self._score_density(query, texts)

        # Factor 4: Answer-type alignment
        answer_type = self._detect_answer_type(query)
        type_scores = self._score_answer_type(answer_type, texts)

        # Factor 5: Source credibility
        source_scores = self._score_source(chunks)

        # Combine
        final_scores = (
            self.W_SEMANTIC * semantic_scores
            + self.W_POSITION * position_scores
            + self.W_DENSITY * density_scores
            + self.W_ANSWER_TYPE * type_scores
            + self.W_SOURCE * source_scores
        )

        # Sort by final score descending
        ranked_indices = np.argsort(final_scores)[::-1][:top_k]

        result = []
        for idx in ranked_indices:
            chunk = dict(chunks[idx])
            chunk["rerank_score"] = float(final_scores[idx])
            chunk["_rerank_detail"] = {
                "semantic": float(semantic_scores[idx]),
                "position": float(position_scores[idx]),
                "density": float(density_scores[idx]),
                "answer_type": float(type_scores[idx]),
                "source": float(source_scores[idx]),
            }
            result.append(chunk)

        logger.debug(f"[Reranker] Reranked {n} → {len(result)} chunks, "
                      f"top score: {result[0]['rerank_score']:.3f}")
        return result

    # ─── Factor 1: Semantic ────────────────────────────────────────────────

    def _score_semantic(self, query: str, texts: List[str]) -> "np.ndarray":
        import numpy as np

        if self.model:
            try:
                pairs = [(query, t) for t in texts]
                scores = self.model.predict(pairs)
                scores = np.array(scores, dtype=float)
                # Normalize to [0, 1]
                if scores.max() > scores.min():
                    scores = (scores - scores.min()) / (scores.max() - scores.min())
                return scores
            except Exception as e:
                logger.warning(f"[Reranker] CrossEncoder scoring failed: {e}")

        # Fallback: keyword overlap
        query_words = set(re.findall(r"\w+", query.lower()))
        scores = []
        for t in texts:
            t_words = set(re.findall(r"\w+", t.lower()))
            if query_words:
                scores.append(len(query_words & t_words) / len(query_words))
            else:
                scores.append(0.5)
        return np.array(scores)

    # ─── Factor 3: Keyword Density ─────────────────────────────────────────

    @staticmethod
    def _score_density(query: str, texts: List[str]) -> "np.ndarray":
        import numpy as np

        from Core.constants import STOP_WORDS
        query_keywords = [w for w in re.findall(r"\w+", query.lower()) if w not in STOP_WORDS and len(w) > 2]

        if not query_keywords:
            return np.full(len(texts), 0.5)

        scores = []
        for t in texts:
            t_lower = t.lower()
            hits = sum(t_lower.count(kw) for kw in query_keywords)
            word_count = max(len(t.split()), 1)
            density = hits / word_count
            scores.append(min(density * 10, 1.0))  # Scale and cap

        arr = np.array(scores)
        if arr.max() > 0:
            arr /= arr.max()
        return arr

    # ─── Factor 4: Answer Type ─────────────────────────────────────────────

    def _detect_answer_type(self, query: str) -> str:
        """Detect expected answer type from query."""
        for atype, pattern in self.ANSWER_TYPE_PATTERNS.items():
            if pattern.search(query):
                return atype
        return "general"

    def _score_answer_type(self, answer_type: str, texts: List[str]) -> "np.ndarray":
        """Score chunks by how well they match the expected answer type."""
        import numpy as np

        scores = []
        for t in texts:
            score = 0.5  # Default neutral
            t_lower = t.lower()

            if answer_type == "definition":
                if re.search(r"\bis\s+(a|an|the|defined\s+as)\b", t_lower):
                    score = 0.9
            elif answer_type == "list":
                bullets = len(re.findall(r"(?:^|\n)\s*[-•*\d.]+\s", t))
                if bullets >= 2:
                    score = 0.9
                elif bullets >= 1:
                    score = 0.7
            elif answer_type == "number":
                if re.search(r"\b\d+\.?\d*\s*(%|percent|million|billion|thousand)?\b", t):
                    score = 0.85
            elif answer_type == "person":
                # Simple person name heuristic
                if re.search(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", t):
                    score = 0.8
            elif answer_type == "date":
                if re.search(r"\b\d{4}\b|\b(january|february|march|april|may|june|july|august|september|october|november|december)\b", t_lower):
                    score = 0.85
            elif answer_type == "location":
                if re.search(r"\b(city|country|state|region|located|situated)\b", t_lower):
                    score = 0.8
            elif answer_type == "comparison":
                if re.search(r"\b(while|whereas|compared|unlike|however|but)\b", t_lower):
                    score = 0.85
            elif answer_type == "process":
                if re.search(r"\b(step|first|then|next|finally|process)\b", t_lower):
                    score = 0.85
            elif answer_type == "reason":
                if re.search(r"\b(because|due\s+to|caused|reason|result)\b", t_lower):
                    score = 0.85

            scores.append(score)

        return np.array(scores)

    # ─── Factor 5: Source Credibility ──────────────────────────────────────

    def _score_source(self, chunks: List[Dict]) -> "np.ndarray":
        """Score chunks by source domain credibility."""
        import numpy as np

        scores = []
        for chunk in chunks:
            url = (chunk.get("url") or chunk.get("source") or "").lower()
            title = (chunk.get("title") or "").lower()
            combined = url + " " + title

            best = 0.50
            for key, cred in self.SOURCE_CREDIBILITY.items():
                if key in combined:
                    best = max(best, cred)

            # TLD-based boost
            if ".gov" in url:
                best = max(best, 0.93)
            elif ".edu" in url:
                best = max(best, 0.90)
            elif ".org" in url:
                best = max(best, 0.70)

            scores.append(best)

        return np.array(scores) if scores else np.array([])
