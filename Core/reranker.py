"""
Core/reranker.py - Cross-encoder Re-ranking for Improved Retrieval

Re-ranks retrieved chunks using a cross-encoder model for better relevance.
Supports local model path (RAG_RERANKER_MODEL_PATH) for offline/local-only use.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Tuple
import re

logger = logging.getLogger(__name__)

# Optional dependency
try:
    from sentence_transformers import CrossEncoder

    HAS_CROSS_ENCODER = True
except ImportError:
    HAS_CROSS_ENCODER = False
    logger.warning("sentence-transformers not installed - using fallback re-ranking")


def _reranker_model_path():
    """Local path from env; when set, load from disk only (no HuggingFace hub)."""
    p = os.environ.get("RAG_RERANKER_MODEL_PATH", "").strip()
    if not p:
        return None
    path = Path(p).expanduser().resolve()
    return str(path) if path.exists() else None


class Reranker:
    """Re-rank retrieved chunks for better relevance"""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_cross_encoder: bool = True,
    ):
        self.use_cross_encoder = use_cross_encoder and HAS_CROSS_ENCODER
        self.model = None
        local_path = _reranker_model_path()
        load_name = local_path if local_path else model_name

        if self.use_cross_encoder:
            try:
                if local_path:
                    logger.info(f"Loading cross-encoder from local path (no hub): {local_path}")
                else:
                    logger.info(f"Loading cross-encoder model: {model_name}")
                self.model = CrossEncoder(load_name)
                logger.info("✅ Cross-encoder model loaded")
            except Exception as e:
                logger.warning(f"Failed to load cross-encoder: {e}, using fallback")
                self.use_cross_encoder = False

        self.stats = {
            "rerankings": 0,
        }

    def rerank(
        self,
        query: str,
        chunks: List[str],
        top_k: int = None,
        return_scores: bool = False,
    ) -> List[str] | Tuple[List[str], List[float]]:
        """
        Re-rank chunks by relevance to query

        Args:
            query: User query
            chunks: Retrieved chunks to re-rank
            top_k: Return only top K chunks (None = all)
            return_scores: Whether to return scores along with chunks

        Returns:
            ranked_chunks or (ranked_chunks, scores)
        """
        if not chunks:
            return ([], []) if return_scores else []

        if self.use_cross_encoder and self.model:
            ranked, scores = self._cross_encoder_rerank(query, chunks, top_k)
        else:
            ranked, scores = self._heuristic_rerank(query, chunks, top_k)

        self.stats["rerankings"] += 1

        if return_scores:
            return ranked, scores
        return ranked

    def _cross_encoder_rerank(self, query: str, chunks: List[str], top_k: int = None) -> Tuple[List[str], List[float]]:
        """Re-rank using cross-encoder model"""
        try:
            # Create pairs of (query, chunk)
            pairs = [(query, chunk) for chunk in chunks]

            # Get scores
            scores = self.model.predict(pairs)

            # Sort by score
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

            if top_k:
                ranked_indices = ranked_indices[:top_k]

            ranked_chunks = [chunks[i] for i in ranked_indices]
            ranked_scores = [float(scores[i]) for i in ranked_indices]

            return ranked_chunks, ranked_scores

        except Exception as e:
            logger.warning(f"Cross-encoder reranking failed: {e}, using fallback")
            return self._heuristic_rerank(query, chunks, top_k)

    def _heuristic_rerank(self, query: str, chunks: List[str], top_k: int = None) -> Tuple[List[str], List[float]]:
        """Fast heuristic re-ranking based on keyword overlap and position"""
        # Extract query keywords
        query_lower = query.lower()
        from Core.constants import STOP_WORDS, _WORD_RE

        query_words = set(_WORD_RE.findall(query_lower)) - STOP_WORDS

        # If no meaningful query words remain (all stop words), return original order
        if not query_words:
            scores = [1.0 - (i / max(len(chunks), 1)) for i in range(len(chunks))]
            if top_k:
                return chunks[:top_k], scores[:top_k]
            return chunks, scores

        # Score each chunk
        chunk_scores = []
        for chunk in chunks:
            score = self._calculate_relevance_score(chunk, query_words, query_lower)
            chunk_scores.append(score)

        # Sort by score
        ranked_indices = sorted(range(len(chunk_scores)), key=lambda i: chunk_scores[i], reverse=True)

        if top_k:
            ranked_indices = ranked_indices[:top_k]

        ranked_chunks = [chunks[i] for i in ranked_indices]
        ranked_scores = [chunk_scores[i] for i in ranked_indices]

        return ranked_chunks, ranked_scores

    def _calculate_relevance_score(self, chunk: str, query_words: set, query_lower: str) -> float:
        """Calculate relevance score for a chunk"""
        chunk_lower = chunk.lower()
        chunk_words = set(re.findall(r"\b\w+\b", chunk_lower))

        # Keyword overlap score
        overlap = len(query_words & chunk_words)
        overlap_score = overlap / max(len(query_words), 1)

        # Exact phrase match bonus
        phrase_bonus = 1.0 if query_lower in chunk_lower else 0.0

        # Position bonus (earlier mentions score higher)
        position_bonus = 0.0
        for word in query_words:
            pos = chunk_lower.find(word)
            if pos != -1:
                # Normalize position (earlier = higher score)
                position_bonus += 1.0 - (pos / max(len(chunk_lower), 1))
        position_bonus /= max(len(query_words), 1)

        # Combine scores
        final_score = overlap_score * 0.5 + phrase_bonus * 0.3 + position_bonus * 0.2

        return final_score

    def get_stats(self) -> Dict:
        """Get re-ranking statistics"""
        return {
            "total_rerankings": self.stats["rerankings"],
            "model_type": "cross-encoder" if self.use_cross_encoder else "heuristic",
            "model_loaded": self.model is not None,
        }


# Global instance
_instance = None


def get_reranker(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> Reranker:
    """Get or create global reranker instance. Uses RAG_RERANKER_MODEL_PATH when set (local-only)."""
    global _instance
    if _instance is None:
        _instance = Reranker(model_name=model_name)
    return _instance
