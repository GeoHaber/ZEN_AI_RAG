"""
Core/contextual_compressor.py - LLM-based Contextual Compression

Reduces token usage by extracting only relevant sentences from retrieved chunks
while maintaining answer quality.

Features:
- LLM-based relevance scoring
- Sentence-level extraction
- Compression ratio tracking
- Token savings metrics
"""

import logging
from typing import List, Dict, Tuple
import re

logger = logging.getLogger(__name__)


class ContextualCompressor:
    """Compress retrieved chunks to only relevant information"""

    def __init__(self, llm_backend=None, max_tokens_per_chunk: int = 200):
        self.llm = llm_backend
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.stats = {
            "compressions": 0,
            "original_tokens": 0,
            "compressed_tokens": 0,
            "compression_ratio": 0.0,
        }

    def compress_chunks(self, query: str, chunks: List[str], use_llm: bool = True) -> Tuple[List[str], Dict]:
        """
        Compress chunks to only relevant sentences

        Args:
            query: User query
            chunks: Retrieved chunks to compress
            use_llm: Whether to use LLM for compression (slower but better)

        Returns:
            (compressed_chunks, compression_stats)
        """
        if not chunks:
            return [], self._get_stats()

        compressed = []
        original_tokens = 0
        compressed_tokens = 0

        for chunk in chunks:
            original_tokens += self._estimate_tokens(chunk)

            if use_llm and self.llm:
                compressed_chunk = self._llm_compress(query, chunk)
            else:
                compressed_chunk = self._heuristic_compress(query, chunk)

            compressed_tokens += self._estimate_tokens(compressed_chunk)
            compressed.append(compressed_chunk)

        # Update stats
        self.stats["compressions"] += 1
        self.stats["original_tokens"] += original_tokens
        self.stats["compressed_tokens"] += compressed_tokens

        if original_tokens > 0:
            compression_ratio = compressed_tokens / original_tokens
            self.stats["compression_ratio"] = compression_ratio

        return compressed, self._get_stats()

    def _llm_compress(self, query: str, chunk: str) -> str:
        """Use LLM to extract only relevant sentences"""
        if not self.llm:
            return self._heuristic_compress(query, chunk)

        try:
            # This would call the actual LLM
            # response = self.llm.generate(prompt, max_tokens=self.max_tokens_per_chunk)
            # For now, fallback to heuristic
            return self._heuristic_compress(query, chunk)
        except Exception as e:
            logger.warning(f"LLM compression failed: {e}, using heuristic")
            return self._heuristic_compress(query, chunk)

    def _heuristic_compress(self, query: str, chunk: str) -> str:
        """Fast heuristic compression based on keyword matching — preserves original order"""
        # Split into sentences
        sentences = self._split_sentences(chunk)

        if not sentences:
            return chunk

        # Extract query keywords
        query_lower = query.lower()
        from Core.constants import STOP_WORDS, _WORD_RE

        query_words = set(_WORD_RE.findall(query_lower)) - STOP_WORDS

        if not query_words:
            # No meaningful keywords, return first few sentences
            return " ".join(sentences[:3])

        # Score each sentence (keep original index for order preservation)
        scored_sentences = []
        for idx, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            sentence_words = set(re.findall(r"\b\w+\b", sentence_lower))

            # Calculate overlap
            overlap = len(query_words & sentence_words)
            score = overlap / max(len(query_words), 1)

            scored_sentences.append((score, idx, sentence))

        # Sort by score to pick the best ones
        scored_sentences.sort(reverse=True, key=lambda x: x[0])

        # Select top sentences until we hit token limit
        selected_indices = []
        total_tokens = 0

        for score, idx, sentence in scored_sentences:
            if score > 0:  # Only include sentences with some relevance
                sentence_tokens = self._estimate_tokens(sentence)
                if total_tokens + sentence_tokens <= self.max_tokens_per_chunk:
                    selected_indices.append(idx)
                    total_tokens += sentence_tokens
                else:
                    break

        # If no relevant sentences, take first few
        if not selected_indices:
            return " ".join(sentences[:2])

        # Re-sort by original position to preserve document flow
        selected_indices.sort()
        result_sentences = [sentences[i] for i in selected_indices]

        return " ".join(result_sentences)

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences"""
        from Core.constants import split_sentences

        return split_sentences(text)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count (rough approximation)"""
        from Core.constants import estimate_tokens

        return estimate_tokens(text)

    def _get_stats(self) -> Dict:
        """Get compression statistics"""
        savings = 0
        if self.stats["original_tokens"] > 0:
            savings = (1 - self.stats["compression_ratio"]) * 100

        return {
            "total_compressions": self.stats["compressions"],
            "total_original_tokens": self.stats["original_tokens"],
            "total_compressed_tokens": self.stats["compressed_tokens"],
            "compression_ratio": self.stats["compression_ratio"],
            "token_savings_percent": savings,
        }

    def reset_stats(self):
        """Reset compression statistics"""
        self.stats = {
            "compressions": 0,
            "original_tokens": 0,
            "compressed_tokens": 0,
            "compression_ratio": 0.0,
        }


# Global instance
_instance = None


def get_contextual_compressor(llm_backend=None) -> ContextualCompressor:
    """Get or create global contextual compressor instance"""
    global _instance
    if _instance is None:
        _instance = ContextualCompressor(llm_backend=llm_backend)
    return _instance
