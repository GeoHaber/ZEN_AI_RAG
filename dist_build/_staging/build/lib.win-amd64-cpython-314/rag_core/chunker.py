"""
rag_core.chunker — Unified text chunking
==========================================

Text + code chunking with junk filtering and entropy checks.
Supports sentence-boundary, fixed-size, and AST-aligned (code) strategies.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from math import log2
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A single chunk of text with metadata."""

    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = hashlib.sha256(self.text.encode()).hexdigest()


class ChunkerConfig:
    """Configuration for the text chunker."""

    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    MIN_CHUNK_LENGTH: int = 50
    MIN_ENTROPY: float = 1.5
    MAX_ENTROPY: float = 6.0
    BLACKLIST_KEYWORDS: set = {
        "advertisement",
        "sponsored",
        "cookie policy",
        "privacy policy",
        "subscribe now",
        "sign up for",
        "click here to",
    }

    def __init__(self, **overrides):
        for k, v in overrides.items():
            if hasattr(self, k):
                setattr(self, k, v)


class TextChunker:
    """
    Unified text chunker with multiple strategies.

    Strategies:
    - ``"sentence"``  — split on sentence boundaries, then merge up to chunk_size
    - ``"fixed"``     — fixed-size windows with overlap
    - ``"code"``      — AST-aligned one-chunk-per-function (for Python)
    """

    SENTENCE_ENDINGS = r"(?<=[.!?])\s+"

    def __init__(self, config: Optional[ChunkerConfig] = None):
        self.config = config or ChunkerConfig()

    # -- Entropy & Junk Detection -------------------------------------------

    def calculate_entropy(self, text: str) -> float:
        """Shannon entropy of character distribution."""
        if not text:
            return 0.0
        counts = Counter(text)
        total = len(text)
        probs = [c / total for c in counts.values()]
        return -sum(p * log2(p) for p in probs if p > 0)

    def is_junk(self, text: str) -> bool:
        """Detect junk chunks (too short, wrong entropy, blacklisted)."""
        text = text.strip()
        if len(text) < self.config.MIN_CHUNK_LENGTH:
            return True
        entropy = self.calculate_entropy(text)
        if entropy < self.config.MIN_ENTROPY or entropy > self.config.MAX_ENTROPY:
            return True
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.config.BLACKLIST_KEYWORDS)

    # -- Chunking Strategies ------------------------------------------------

    def chunk_text(
        self,
        text: str,
        *,
        strategy: str = "sentence",
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        filter_junk: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Split text into chunks using the chosen strategy.

        Args:
            text: Input text.
            strategy: ``"sentence"`` | ``"fixed"`` | ``"code"``.
            chunk_size: Override config chunk size.
            overlap: Override config overlap.
            filter_junk: Remove low-quality chunks.
            metadata: Extra metadata to attach to every chunk.

        Returns:
            List of :class:`Chunk` objects.
        """
        size = chunk_size or self.config.CHUNK_SIZE
        olap = overlap or self.config.CHUNK_OVERLAP

        if strategy == "sentence":
            raw = self._chunk_sentence(text, size, olap)
        elif strategy == "fixed":
            raw = self._chunk_fixed(text, size, olap)
        elif strategy == "code":
            raw = self._chunk_code(text)
        else:
            raw = self._chunk_fixed(text, size, olap)

        chunks: List[Chunk] = []
        for i, t in enumerate(raw):
            if filter_junk and self.is_junk(t):
                continue
            meta = dict(metadata or {})
            chunks.append(Chunk(text=t, metadata=meta, chunk_index=i))

        return chunks

    def chunk_document(
        self,
        text: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        strategy: str = "sentence",
        filter_junk: bool = True,
        model: Any = None,
    ) -> List[Chunk]:
        """Convenience: chunk a single document text (backward compat).

        Same as :meth:`chunk_text` but with argument names matching the
        legacy ``zena_mode.chunker.TextChunker`` API.

        Args:
            text: Raw document text.
            metadata: Extra metadata to attach.
            strategy: Chunking strategy name.
            filter_junk: Remove junk chunks.
            model: Ignored (kept for legacy compat).

        Returns:
            List of :class:`Chunk` objects.
        """
        return self.chunk_text(
            text,
            strategy=strategy,
            filter_junk=filter_junk,
            metadata=metadata,
        )

    def _chunk_sentence(self, text: str, size: int, overlap: int) -> List[str]:
        """Split on sentence boundaries, merge up to *size* chars."""
        sentences = re.split(self.SENTENCE_ENDINGS, text)
        chunks: List[str] = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) + 1 > size and current:
                chunks.append(current.strip())
                # Keep overlap from end of current
                current = current[-overlap:] + " " + sent if overlap else sent
            else:
                current = (current + " " + sent).strip() if current else sent
        if current.strip():
            chunks.append(current.strip())
        return chunks

    def _chunk_fixed(self, text: str, size: int, overlap: int) -> List[str]:
        """Fixed-size windows with overlap."""
        if size <= 0:
            size = 1  # guard against zero/negative
        # Clamp overlap so the window always advances by at least 1 char
        effective_overlap = min(overlap, size - 1) if overlap else 0
        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = start + size
            chunks.append(text[start:end])
            start = end - effective_overlap
        return chunks

    def _chunk_code(self, text: str) -> List[str]:
        """AST-aligned chunking for Python code (one chunk per function/class)."""
        import ast

        chunks: List[str] = []
        lines = text.split("\n")
        try:
            tree = ast.parse(text)
        except (SyntaxError, MemoryError, ValueError):
            # Fall back to fixed chunking for unparseable / too-complex code
            return self._chunk_fixed(text, self.config.CHUNK_SIZE, self.config.CHUNK_OVERLAP)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.lineno - 1
                end = getattr(node, "end_lineno", start + 1) or start + 1
                chunk = "\n".join(lines[start:end])
                if chunk.strip():
                    chunks.append(chunk)

        if not chunks:
            return self._chunk_fixed(text, self.config.CHUNK_SIZE, self.config.CHUNK_OVERLAP)

        return chunks

    # -- Batch Processing ---------------------------------------------------

    def chunk_documents(
        self,
        documents: List[Dict[str, Any]],
        *,
        strategy: str = "sentence",
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        filter_junk: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Chunk a list of documents (each with ``"text"`` key).

        Each document dict should have at least ``{"text": "..."}`` and
        optionally ``"url"``, ``"title"``, ``"metadata"``.

        Returns flat list of chunk dicts compatible with Qdrant payloads.
        """
        all_chunks: List[Dict[str, Any]] = []
        for doc in documents:
            text = doc.get("text", "")
            if not text:
                continue

            meta = {
                "url": doc.get("url", ""),
                "title": doc.get("title", ""),
                **(doc.get("metadata", {})),
            }

            chunks = self.chunk_text(
                text,
                strategy=strategy,
                chunk_size=chunk_size,
                overlap=overlap,
                filter_junk=filter_junk,
                metadata=meta,
            )

            for chunk in chunks:
                all_chunks.append(
                    {
                        "text": chunk.text,
                        "hash": chunk.hash,
                        "chunk_index": chunk.chunk_index,
                        "url": meta.get("url", ""),
                        "title": meta.get("title", ""),
                        "metadata": chunk.metadata,
                    }
                )

        return all_chunks
