# -*- coding: utf-8 -*-
"""
zena_mode/contextual_compressor.py — Smart Context Compression
===============================================================

Adapted from RAG_RAT Core/contextual_compressor.py for ZEN_AI_RAG.

Compresses retrieved chunks so only the most query-relevant sentences
are forwarded to the LLM, reducing token usage while preserving accuracy.

Strategy: keyword-overlap sentence scoring with order-preserving selection.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import extract_key_words, split_sentences, estimate_tokens

logger = logging.getLogger(__name__)


@dataclass
class CompressionStats:
    """Track compression performance metrics."""
    total_chars_in: int = 0
    total_chars_out: int = 0
    total_chunks_in: int = 0
    total_chunks_out: int = 0
    calls: int = 0

    @property
    def ratio(self) -> float:
        """Return the compression ratio (output / input characters)."""
        return self.total_chars_out / self.total_chars_in if self.total_chars_in else 1.0


@dataclass
class CompressedChunk:
    """One compressed chunk with metadata."""
    text: str
    score: float = 0.0
    source: str = ""
    original_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextualCompressor:
    """Compresses RAG context to only the most relevant sentences."""

    def __init__(
        self,
        *,
        max_tokens: int = 3000,
        min_score: float = 0.10,
        keep_top_k: int = 20,
    ) -> None:
        """Initialize the compressor with token budget and relevance thresholds."""
        self.max_tokens = max_tokens
        self.min_score = min_score
        self.keep_top_k = keep_top_k
        self.stats = CompressionStats()

    # ── public API ────────────────────────────────────────────────────────

    def compress_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
    ) -> List[CompressedChunk]:
        """Compress a list of chunks to the most query-relevant sentences.

        Parameters
        ----------
        query : str
            The user query.
        chunks : list[dict]
            Each dict should have at least ``"text"`` (str).
            Optional keys: ``"source"`` (str), ``"metadata"`` (dict).

        Returns
        -------
        list[CompressedChunk]
            Order-preserved, token-limited selection of relevant sentences.
        """
        if not chunks or not query.strip():
            return []

        self.stats.calls += 1
        self.stats.total_chunks_in += len(chunks)

        # Keyword extraction from query
        keywords = extract_key_words(query)
        if not keywords:
            # Fallback: just truncate
            return self._truncate_fallback(chunks)

        # Score every sentence across all chunks
        return self._compress_chunks_part2(keywords)

    def _compress_chunks_part2(self, keywords):
        """Continue compress_chunks logic."""
        scored: List[Dict[str, Any]] = []
        for idx, chunk in enumerate(chunks):
            text = chunk.get("text", "")
            source = chunk.get("source", "")
            meta = chunk.get("metadata", {})
            self.stats.total_chars_in += len(text)

            for sentence in split_sentences(text):
                s_lower = sentence.lower()
                s_words = set(s_lower.split())
                overlap = len(keywords & s_words)
                if not overlap:
                    continue
                score = overlap / max(len(keywords), 1)
                scored.append({
                    "sentence": sentence,
                    "score": score,
                    "source": source,
                    "chunk_idx": idx,
                    "metadata": meta,
                })

        if not scored:
            return self._truncate_fallback(chunks)

        # Sort by score descending, then by original position (stability)
        scored.sort(key=lambda x: (-x["score"], x["chunk_idx"]))

        # Apply min_score filter
        scored = [s for s in scored if s["score"] >= self.min_score]

        # Select top-k, respecting token budget
        return self._compress_chunks_part2(scored)

    def _compress_chunks_part2(self, scored):
        """Continue compress_chunks logic."""
        selected: List[Dict[str, Any]] = []
        token_budget = self.max_tokens
        for item in scored[: self.keep_top_k]:
            est = estimate_tokens(item["sentence"])
            if est > token_budget:
                break
            selected.append(item)
            token_budget -= est

        if not selected:
            return self._truncate_fallback(chunks)

        # Restore original order (by chunk_idx, then appearance)
        selected.sort(key=lambda x: x["chunk_idx"])

        results: List[CompressedChunk] = []
        for item in selected:
            cc = CompressedChunk(
                text=item["sentence"],
                score=item["score"],
                source=item["source"],
                original_index=item["chunk_idx"],
                metadata=item["metadata"],
            )
            results.append(cc)
            self.stats.total_chars_out += len(cc.text)

        self.stats.total_chunks_out += len(results)
        ratio_pct = f"{self.stats.ratio:.0%}"
        logger.info(
            "Compressed %d chunks → %d sentences (ratio %s, budget remaining %d tokens)",
            len(chunks), len(results), ratio_pct, token_budget,
        )
        return results

    # ── helpers ───────────────────────────────────────────────────────────

    def _truncate_fallback(self, chunks: List[Dict[str, Any]]) -> List[CompressedChunk]:
        """Fallback: return chunks truncated to token budget."""
        results: List[CompressedChunk] = []
        budget = self.max_tokens
        for idx, chunk in enumerate(chunks):
            text = chunk.get("text", "")
            est = estimate_tokens(text)
            if est > budget:
                # Rough char trim
                char_limit = budget * 4
                text = text[:char_limit]
                est = estimate_tokens(text)
            results.append(CompressedChunk(
                text=text,
                score=0.0,
                source=chunk.get("source", ""),
                original_index=idx,
            ))
            budget -= est
            if budget <= 0:
                break
        return results


# ── singleton ─────────────────────────────────────────────────────────────

_instance: Optional[ContextualCompressor] = None


def get_compressor(*, max_tokens: int = 3000) -> ContextualCompressor:
    """Return the global :class:`ContextualCompressor` singleton."""
    global _instance
    if _instance is None:
        _instance = ContextualCompressor(max_tokens=max_tokens)
    return _instance
