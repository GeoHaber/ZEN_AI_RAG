"""
Core/contextual_compressor.py — Sentence-Level Context Compression.

Extracts only the sentences from retrieved chunks that are relevant
to the query, reducing noise before LLM generation.

Ported from ZEN_RAG.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from Core.constants import STOP_WORDS, split_sentences, estimate_tokens

logger = logging.getLogger(__name__)


class ContextualCompressor:
    """Compress retrieved chunks to only query-relevant sentences.

    Usage:
        compressor = ContextualCompressor(max_tokens=2000)
        compressed = compressor.compress(query, chunks)
    """

    def __init__(
        self,
        max_tokens: int = 2000,
        min_keyword_overlap: int = 1,
        min_sentence_len: int = 10,
    ):
        """
        Args:
            max_tokens: max tokens in compressed output
            min_keyword_overlap: minimum keywords a sentence must share with query
            min_sentence_len: minimum character length for a sentence to be kept
        """
        self.max_tokens = max_tokens
        self.min_keyword_overlap = min_keyword_overlap
        self.min_sentence_len = min_sentence_len

    def compress(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract query-relevant sentences from chunks.

        Returns a new list of chunks with compressed text.
        """
        if not chunks or not query:
            return chunks

        query_keywords = self._extract_keywords(query)
        if not query_keywords:
            return chunks  # Can't determine relevance without keywords

        compressed = []
        total_tokens = 0

        for chunk in chunks:
            text = chunk.get("text", "")
            if not text:
                continue

            sentences = split_sentences(text)
            relevant_sentences = []

            for sent in sentences:
                if len(sent) < self.min_sentence_len:
                    continue

                sent_keywords = set(
                    w.lower() for w in sent.split()
                    if w.lower() not in STOP_WORDS and len(w) > 2
                )
                overlap = len(query_keywords & sent_keywords)

                if overlap >= self.min_keyword_overlap:
                    relevant_sentences.append(sent)

            if relevant_sentences:
                compressed_text = " ".join(relevant_sentences)
                token_count = estimate_tokens(compressed_text)

                if total_tokens + token_count > self.max_tokens:
                    # Trim to fit budget
                    remaining = self.max_tokens - total_tokens
                    if remaining > 50:
                        # Approximate: take proportional sentences
                        ratio = remaining / token_count
                        n_keep = max(1, int(len(relevant_sentences) * ratio))
                        compressed_text = " ".join(relevant_sentences[:n_keep])
                        token_count = estimate_tokens(compressed_text)
                    else:
                        break

                compressed.append({
                    **chunk,
                    "text": compressed_text,
                    "_compressed": True,
                    "_original_len": len(text),
                    "_compressed_len": len(compressed_text),
                })
                total_tokens += token_count

        logger.debug(
            f"[Compressor] {len(chunks)} chunks → {len(compressed)} compressed, "
            f"~{total_tokens} tokens"
        )
        return compressed if compressed else chunks  # Fallback to original

    @staticmethod
    def _extract_keywords(text: str) -> set:
        """Extract meaningful keywords from text."""
        words = text.lower().split()
        return {w for w in words if w not in STOP_WORDS and len(w) > 2}
