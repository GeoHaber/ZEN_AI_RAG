"""
Core/contextual_retrieval.py — Anthropic-Style Contextual Retrieval.

Industry best practice: Before embedding, each chunk receives a short
contextual preamble that situates it within its parent document.
This dramatically improves retrieval recall (up to 49% reduction in
failed retrievals per Anthropic's research).

Pipeline:
  1. For each chunk, generate a 1-2 sentence context using the full document
  2. Prepend context to chunk text before embedding
  3. Store both raw chunk and contextualized version

References:
  - Anthropic "Contextual Retrieval" (2024)
  - Microsoft "Lost in the Middle" findings
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContextualizedChunk:
    """A chunk enriched with document-level context."""

    original_text: str
    context_prefix: str
    contextualized_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0
    document_title: str = ""
    context_hash: str = ""

    def __post_init__(self):
        if not self.context_hash:
            self.context_hash = hashlib.sha256(
                self.contextualized_text.encode()
            ).hexdigest()[:16]


class ContextualRetrieval:
    """Enrich chunks with document-level context before embedding.

    This implements Anthropic's Contextual Retrieval pattern:
    each chunk gets a short preamble explaining where it sits
    within the overall document, dramatically improving retrieval
    for ambiguous or context-dependent passages.

    Usage:
        cr = ContextualRetrieval(llm_fn=my_generate)
        enriched = cr.contextualize_chunks(chunks, document_text)
    """

    _CONTEXT_PROMPT = (
        "Here is the full document:\n<document>\n{document}\n</document>\n\n"
        "Here is a chunk from that document:\n<chunk>\n{chunk}\n</chunk>\n\n"
        "Give a short succinct context (1-2 sentences) to situate this chunk "
        "within the overall document. The context should help a search engine "
        "understand what this chunk is about. Only output the context, nothing else."
    )

    _BATCH_PROMPT = (
        "Here is a document title: {title}\n\n"
        "Here is a summary of the document:\n{summary}\n\n"
        "Here is a specific chunk (chunk {index} of {total}):\n"
        "<chunk>\n{chunk}\n</chunk>\n\n"
        "Give a short context (1-2 sentences) to situate this chunk. "
        "Only output the context."
    )

    def __init__(
        self,
        llm_fn: Optional[Callable] = None,
        max_document_chars: int = 8000,
        enable_caching: bool = True,
    ):
        """
        Args:
            llm_fn: function(prompt) -> str for context generation
            max_document_chars: max chars of document to include in prompt
            enable_caching: cache generated contexts by chunk hash
        """
        self.llm_fn = llm_fn
        self.max_document_chars = max_document_chars
        self._cache: Dict[str, str] = {} if enable_caching else None

    def contextualize_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_text: str,
        document_title: str = "",
    ) -> List[ContextualizedChunk]:
        """Add document-level context to each chunk.

        If LLM is unavailable, falls back to a heuristic preamble
        using the document title and chunk position.
        """
        if not chunks:
            return []

        doc_truncated = document_text[:self.max_document_chars]
        total = len(chunks)
        results = []

        for i, chunk in enumerate(chunks):
            text = chunk.get("text", "")
            if not text.strip():
                continue

            cache_key = hashlib.sha256(
                f"{document_title}:{text[:200]}".encode()
            ).hexdigest()[:16]

            # Check cache
            if self._cache is not None and cache_key in self._cache:
                context_prefix = self._cache[cache_key]
            elif self.llm_fn:
                context_prefix = self._generate_context(
                    doc_truncated, text, document_title, i, total
                )
                if self._cache is not None:
                    self._cache[cache_key] = context_prefix
            else:
                context_prefix = self._heuristic_context(
                    document_title, text, i, total
                )

            contextualized = f"{context_prefix}\n\n{text}" if context_prefix else text

            results.append(ContextualizedChunk(
                original_text=text,
                context_prefix=context_prefix,
                contextualized_text=contextualized,
                metadata=chunk.get("metadata", {}),
                chunk_index=i,
                document_title=document_title,
            ))

        logger.info(
            f"[ContextualRetrieval] Enriched {len(results)}/{len(chunks)} chunks "
            f"from '{document_title[:50]}'"
        )
        return results

    def contextualize_single(
        self,
        chunk_text: str,
        document_text: str,
        document_title: str = "",
        chunk_index: int = 0,
        total_chunks: int = 1,
    ) -> str:
        """Generate context prefix for a single chunk. Returns enriched text."""
        if self.llm_fn:
            prefix = self._generate_context(
                document_text[:self.max_document_chars],
                chunk_text, document_title, chunk_index, total_chunks,
            )
        else:
            prefix = self._heuristic_context(
                document_title, chunk_text, chunk_index, total_chunks,
            )
        return f"{prefix}\n\n{chunk_text}" if prefix else chunk_text

    def _generate_context(
        self,
        document_text: str,
        chunk_text: str,
        title: str,
        index: int,
        total: int,
    ) -> str:
        """Use LLM to generate a situating context for the chunk."""
        try:
            if len(document_text) > 2000:
                prompt = self._BATCH_PROMPT.format(
                    title=title or "Untitled",
                    summary=document_text[:2000],
                    index=index + 1,
                    total=total,
                    chunk=chunk_text[:1000],
                )
            else:
                prompt = self._CONTEXT_PROMPT.format(
                    document=document_text,
                    chunk=chunk_text[:1000],
                )
            result = self.llm_fn(prompt)
            if result and len(result.strip()) > 10:
                return result.strip()[:300]
        except Exception as e:
            logger.debug(f"[ContextualRetrieval] LLM context generation failed: {e}")
        return self._heuristic_context(title, chunk_text, index, total)

    @staticmethod
    def _heuristic_context(
        title: str, chunk_text: str, index: int, total: int
    ) -> str:
        """Generate a simple positional context without LLM."""
        parts = []
        if title:
            parts.append(f"From document: {title}.")
        if total > 1:
            position = "beginning" if index < total * 0.25 else (
                "end" if index > total * 0.75 else "middle"
            )
            parts.append(f"This is from the {position} of the document (section {index + 1}/{total}).")
        return " ".join(parts)
