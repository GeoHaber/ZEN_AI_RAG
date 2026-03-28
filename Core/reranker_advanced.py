"""
Core/reranker_advanced.py — 5-Factor Advanced Re-ranking Engine

Replaces simple keyword-overlap ranking with a multi-signal reranker:
  Factor 1: Semantic relevance (CrossEncoder or cosine)    — 40%
  Factor 2: Position / structure importance                 — 10%
  Factor 3: Information density (unique words, length)      — 15%
  Factor 4: Answer-type matching (what/how/compare/where)   — 25%
  Factor 5: Source credibility (official > academic > web)   — 10%

Drop-in replacement for the existing reranker in rag_pipeline.py.

Usage:
    reranker = AdvancedReranker(model=sentence_transformer)
    ranked, scores = reranker.rerank(query, chunks, top_k=5)
"""

import os
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _reranker_model_path():
    """Local path from env; when set, load from disk only (no HuggingFace hub)."""
    p = os.environ.get("RAG_RERANKER_MODEL_PATH", "").strip()
    if not p:
        return None
    path = Path(p).expanduser().resolve()
    return str(path) if path.exists() else None


try:
    import numpy as np
except ImportError:
    np = None


class AdvancedReranker:
    """5-factor re-ranking combining semantic, structural, and quality signals."""

    # ── Source credibility table ──────────────────────────────────────────
    SOURCE_CREDIBILITY = {
        "official": 0.95,
        "gov": 0.93,
        "edu": 0.90,
        "academic": 0.90,
        "research": 0.88,
        "pubmed": 0.88,
        "nih": 0.88,
        "news": 0.75,
        "bbc": 0.78,
        "reuters": 0.80,
        "wiki": 0.70,
        "wikipedia": 0.70,
        "github": 0.75,
        "stackoverflow": 0.72,
        "pdf": 0.65,
        "medium": 0.55,
        "blog": 0.50,
        "reddit": 0.45,
        "forum": 0.40,
        "web": 0.50,
    }

    # ── Query-type detection patterns ────────────────────────────────────
    QUERY_TYPE_PATTERNS = {
        "definition": re.compile(r"\b(what|define|meaning|explain|describe|who)\b", re.I),
        "procedure": re.compile(r"\b(how|steps?|process|procedure|guide|tutorial|instructions?)\b", re.I),
        "comparison": re.compile(
            r"\b(compare|difference|vs|versus|better|worse|advantage|disadvantage)\b",
            re.I,
        ),
        "location": re.compile(r"\b(where|location|place|country|city|address|situated)\b", re.I),
        "temporal": re.compile(r"\b(when|date|year|time|history|timeline|era)\b", re.I),
        "quantitative": re.compile(r"\b(how\s+many|how\s+much|number|count|percentage|ratio|amount)\b", re.I),
        "causal": re.compile(r"\b(why|cause|reason|because|effect|result|consequence)\b", re.I),
    }

    # ── Answer-type indicators per query-type ────────────────────────────
    ANSWER_INDICATORS = {
        "definition": [
            (r"\bis\s+(a|an|the|defined\s+as)\b", 0.95),
            (r"\brefers?\s+to\b", 0.90),
            (r"\bmeans?\b", 0.85),
            (r"\b(definition|concept|term)\b", 0.80),
        ],
        "procedure": [
            (r"(?:^|\n)\s*\d+[\.\)]\s", 0.95),  # Numbered lists
            (r"\b(step|first|second|then|next|finally)\b", 0.90),
            (r"\b(process|procedure|method|technique)\b", 0.80),
            (r"\b(install|configure|setup|run|execute)\b", 0.75),
        ],
        "comparison": [
            (r"\b(unlike|whereas|however|on\s+the\s+other\s+hand)\b", 0.95),
            (r"\b(vs|versus|compared?\s+to)\b", 0.90),
            (r"\b(advantage|disadvantage|pro|con)\b", 0.85),
            (r"\b(similar|different|differ)\b", 0.80),
        ],
        "location": [
            (r"\b(located|situated|found\s+in)\b", 0.95),
            (r"\b(north|south|east|west)\s+of\b", 0.90),
            (r"\b(region|province|state|district)\b", 0.80),
            (r"\b(lat|long|coordinates?)\b", 0.85),
        ],
        "temporal": [
            (r"\b(in\s+)?\d{4}\b", 0.90),
            (r"\b(century|decade|era|period)\b", 0.85),
            (r"\b(before|after|during|between)\b", 0.75),
            (r"\b(founded|established|created|born|died)\b", 0.90),
        ],
        "quantitative": [
            (r"\d+(?:\.\d+)?(?:\s*%|\s*percent)", 0.95),
            (r"\b\d+(?:,\d{3})*\b", 0.85),
            (r"\b(total|average|median|approximately)\b", 0.80),
            (r"\b(statistics?|data|figure|number)\b", 0.75),
        ],
        "causal": [
            (r"\b(because|due\s+to|caused?\s+by)\b", 0.95),
            (r"\b(result(?:s|ed)?\s+in|lead(?:s|ing)?\s+to)\b", 0.90),
            (r"\b(reason|cause|effect|consequence)\b", 0.85),
            (r"\b(therefore|thus|hence|so)\b", 0.80),
        ],
    }

    def __init__(self, model=None, cross_encoder=None):
        """
        Args:
            model: SentenceTransformer for embedding-based scoring.
            cross_encoder: Optional CrossEncoder for precise semantic scoring.
                           If None, falls back to cosine similarity.
        """
        self.model = model
        self.cross_encoder = cross_encoder

        # Try to load CrossEncoder if not provided (prefer local path for offline use)
        if self.cross_encoder is None:
            try:
                from sentence_transformers import CrossEncoder

                default_name = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
                load_name = _reranker_model_path() or default_name
                if load_name != default_name:
                    logger.info(f"[Reranker] CrossEncoder from local path (no hub): {load_name}")
                self.cross_encoder = CrossEncoder(load_name)
                logger.info("[Reranker] CrossEncoder loaded")
            except Exception as e:
                logger.info(f"[Reranker] CrossEncoder not available ({e}), using cosine fallback")
                self.cross_encoder = None

    # =====================================================================
    # PUBLIC API
    # =====================================================================

    def rerank(
        self,
        query: str,
        chunks: List[Dict],
        top_k: int = 5,
        weights: Optional[Dict[str, float]] = None,
    ) -> Tuple[List[Dict], List[float]]:
        """
        Rerank chunks using 5-factor scoring.

        Args:
            query: User query.
            chunks: List of chunk dicts (must have 'text', optionally 'url', 'source', 'title').
            top_k: Number of results to return.
            weights: Override default factor weights. Keys:
                     semantic, position, density, answer_type, source

        Returns:
            (ranked_chunks, ranked_scores)
        """
        if not chunks or np is None:
            return chunks[:top_k], [0.0] * min(len(chunks), top_k)

        w = {
            "semantic": 0.40,
            "position": 0.10,
            "density": 0.15,
            "answer_type": 0.25,
            "source": 0.10,
        }
        if weights:
            w.update(weights)

        n = len(chunks)
        scores = np.zeros((n, 5))

        # Factor 1: Semantic relevance
        scores[:, 0] = self._score_semantic(query, chunks) * w["semantic"]

        # Factor 2: Position importance
        scores[:, 1] = self._score_position(chunks) * w["position"]

        # Factor 3: Information density
        scores[:, 2] = self._score_density(chunks) * w["density"]

        # Factor 4: Answer-type match
        scores[:, 3] = self._score_answer_type(query, chunks) * w["answer_type"]

        # Factor 5: Source credibility
        scores[:, 4] = self._score_source(chunks) * w["source"]

        final = np.sum(scores, axis=1)
        ranked_idx = np.argsort(final)[::-1][:top_k]

        ranked_chunks = [chunks[i] for i in ranked_idx]
        ranked_scores = [float(final[i]) for i in ranked_idx]

        # Inject scores into chunk metadata for debugging
        for chunk, score, idx in zip(ranked_chunks, ranked_scores, ranked_idx):
            chunk["_rerank_score"] = score
            chunk["_rerank_factors"] = {
                "semantic": float(scores[idx, 0]),
                "position": float(scores[idx, 1]),
                "density": float(scores[idx, 2]),
                "answer_type": float(scores[idx, 3]),
                "source": float(scores[idx, 4]),
            }

        return ranked_chunks, ranked_scores

    # =====================================================================
    # FACTOR 1: SEMANTIC RELEVANCE (40%)
    # =====================================================================

    def _score_semantic(self, query: str, chunks: List[Dict]) -> np.ndarray:
        """Score each chunk by semantic relevance to the query."""
        texts = [c.get("text", "") for c in chunks]

        # Prefer CrossEncoder (more accurate pairwise scoring)
        if self.cross_encoder is not None:
            try:
                pairs = [(query, t) for t in texts]
                raw_scores = self.cross_encoder.predict(pairs)
                # Sigmoid to [0, 1]
                scores = 1.0 / (1.0 + np.exp(-np.array(raw_scores)))
                return scores
            except Exception as e:
                logger.debug(f"[Reranker] CrossEncoder failed, falling back: {e}")

        # Fallback: cosine similarity with SentenceTransformer
        if self.model is not None:
            try:
                q_emb = self.model.encode([query], normalize_embeddings=True)[0]
                c_embs = self.model.encode(texts, normalize_embeddings=True)
                sims = np.array([np.dot(q_emb, c) for c in c_embs])
                return (sims + 1.0) / 2.0  # Map [-1, 1] → [0, 1]
            except Exception as e:
                logger.debug(f"[Reranker] Embedding scoring failed: {e}")

        # Last resort: keyword overlap
        return self._keyword_overlap(query, texts)

    def _keyword_overlap(self, query: str, texts: List[str]) -> np.ndarray:
        """Simple keyword overlap as ultimate fallback."""
        q_words = set(query.lower().split())
        scores = []
        for text in texts:
            t_words = set(text.lower().split())
            if not q_words:
                scores.append(0.0)
            else:
                scores.append(len(q_words & t_words) / len(q_words))
        return np.array(scores)

    # =====================================================================
    # FACTOR 2: POSITION IMPORTANCE (10%)
    # =====================================================================

    def _score_position(self, chunks: List[Dict]) -> np.ndarray:
        """
        Position-based scoring: beginning and end of documents tend to
        contain introductions and summaries (more information-rich).
        """
        n = len(chunks)
        if n == 0:
            return np.array([])

        scores = np.full(n, 0.65)

        # Score by chunk_index if available, else by list position
        for i, chunk in enumerate(chunks):
            idx = chunk.get("chunk_index", i)
            if idx == 0:
                scores[i] = 0.95
            elif idx == 1:
                scores[i] = 0.85
            elif idx <= 3:
                scores[i] = 0.75

        # Last chunks also tend to be summaries
        if n > 2:
            scores[-1] = max(scores[-1], 0.85)
            if n > 3:
                scores[-2] = max(scores[-2], 0.75)

        return scores

    # =====================================================================
    # FACTOR 3: INFORMATION DENSITY (15%)
    # =====================================================================

    def _score_density(self, chunks: List[Dict]) -> np.ndarray:
        """
        Higher information density = better chunk quality.
        Measures: unique-word ratio, sentence richness, length penalty.
        """
        scores = []
        for chunk in chunks:
            text = chunk.get("text", "")
            words = text.lower().split()
            if len(words) < 3:
                scores.append(0.1)
                continue

            # Unique word ratio (vocabulary richness)
            unique_ratio = len(set(words)) / len(words)

            # Sentence count (richer = better)
            sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
            sent_score = min(len(sentences) / 5.0, 1.0)

            # Length penalty: too short or too long
            char_len = len(text)
            if char_len < 80:
                length_factor = 0.4
            elif char_len < 200:
                length_factor = 0.7
            elif char_len > 3000:
                length_factor = 0.75
            else:
                length_factor = 1.0

            # Presence of structured content (lists, numbers, proper nouns)
            structure_bonus = 0.0
            if re.search(r"(?:^|\n)\s*[\-\*\d]+[\.\)]\s", text):
                structure_bonus = 0.1  # Has lists
            if re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text):
                structure_bonus += 0.05  # Has proper nouns

            density = (
                unique_ratio * 0.40 + sent_score * 0.25 + length_factor * 0.25 + structure_bonus
            ) * 0.10 + 0.50  # Shift to 0.5-1.0 range

            scores.append(min(density, 1.0))

        return np.array(scores) if scores else np.array([])

    # =====================================================================
    # FACTOR 4: ANSWER-TYPE MATCHING (25%)
    # =====================================================================

    def _score_answer_type(self, query: str, chunks: List[Dict]) -> np.ndarray:
        """
        Match chunk content type to what the query needs.
        E.g., "What is X?" needs definition chunks; "How to Y?" needs step-by-step.
        """
        # Detect query type
        query_type = "general"
        for qtype, pattern in self.QUERY_TYPE_PATTERNS.items():
            if pattern.search(query):
                query_type = qtype
                break

        indicators = self.ANSWER_INDICATORS.get(query_type, [])
        compiled = [(re.compile(p, re.I | re.MULTILINE), s) for p, s in indicators]

        scores = []
        for chunk in chunks:
            text = chunk.get("text", "")
            best = 0.50  # Default for general queries

            for pat, indicator_score in compiled:
                if pat.search(text):
                    best = max(best, indicator_score)

            scores.append(best)

        return np.array(scores) if scores else np.array([])

    # =====================================================================
    # FACTOR 5: SOURCE CREDIBILITY (10%)
    # =====================================================================

    def _score_source(self, chunks: List[Dict]) -> np.ndarray:
        """Score based on source credibility/authority."""
        scores = []
        for chunk in chunks:
            url = (chunk.get("url") or chunk.get("source") or "").lower()
            title = (chunk.get("title") or "").lower()
            combined = url + " " + title

            best = 0.50  # Default
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
