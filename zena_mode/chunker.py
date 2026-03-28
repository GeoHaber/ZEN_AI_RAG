# -*- coding: utf-8 -*-
"""
chunker.py - Unified text chunking for ZenAI RAG.
Consolidates logic from rag_pipeline.py and universal_extractor.py.
"""

import re
import hashlib
import logging
from typing import List, Dict
from dataclasses import dataclass, field
from collections import Counter
from math import log2

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    text: str
    metadata: Dict = field(default_factory=dict)
    chunk_index: int = 0
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = hashlib.sha256(self.text.encode()).hexdigest()


class ChunkerConfig:
    """Default configuration for chunking."""

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
        "all rights reserved",
        "terms of service",
        "follow us on",
        "primary menu",
        "toggle navigation",
        "skip to content",
        "copyright ©",
        "developed by",
        "powered by",
    }


class TextChunker:
    """
    Unified text chunker with multiple strategies.
    """

    SENTENCE_ENDINGS = r"(?<=[.!?])\s+"

    def __init__(self, config: ChunkerConfig = None):
        self.config = config or ChunkerConfig()

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0
        counts = Counter(text)
        probs = [c / len(text) for c in counts.values()]
        return -sum(p * log2(p) for p in probs)

    def is_junk(self, text: str) -> bool:
        """Detect junk chunks based on length, entropy, and keywords."""
        text = text.strip()
        if len(text) < self.config.MIN_CHUNK_LENGTH:
            return True

        words = text.split()
        if len(words) < 5:  # Basic world filter
            return True

        entropy = self._calculate_entropy(text)
        if entropy < self.config.MIN_ENTROPY or entropy > self.config.MAX_ENTROPY:
            return True

        text_lower = text.lower()
        if any(kw in text_lower for kw in self.config.BLACKLIST_KEYWORDS):
            return True

        return False

    def recursive_split(self, text: str, max_size: int, overlap_size: int) -> List[str]:
        """Split text into chunks using semantic recursion."""
        if len(text) <= max_size:
            return [text]

        separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]
        split_at = -1
        for sep in separators:
            pos = text.rfind(sep, 0, max_size)
            if pos != -1:
                split_at = pos + len(sep)
                break

        if split_at == -1:
            split_at = max_size

        chunk = text[:split_at]
        remaining = text[split_at - overlap_size :] if split_at > overlap_size else text[split_at:]

        return [chunk] + self.recursive_split(remaining, max_size, overlap_size)

    def semantic_split(self, text: str, model, threshold: float = 0.75) -> List[Chunk]:
        """
        True semantic chunking using embedding similarity.

        Args:
            text: Content to chunk
            model: SentenceTransformer model instance (must have .encode method)
            threshold: Cosine similarity threshold to break chunks
        """
        import numpy as np

        # 1. Split into sentences
        sentences = re.split(self.SENTENCE_ENDINGS, text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 2:
            return [Chunk(text=text, chunk_index=0)]

        # 2. Embed all sentences (Batch)
        try:
            embeddings = model.encode(sentences, normalize_embeddings=True)
        except Exception:
            # Fallback if model fails or is None
            return self.chunk_document(text, strategy="recursive")

        chunks = []
        current_chunk = [sentences[0]]
        current_len = len(sentences[0])
        idx = 0

        # 3. Iterate and check similarity gaps
        for i in range(len(embeddings) - 1):
            sent = sentences[i + 1]
            sent_len = len(sent)

            # Calculate cosine sim
            score = np.dot(embeddings[i], embeddings[i + 1])

            # Break if:
            # A) Similarity drops below threshold (Topic Shift)
            # B) Chunk gets too big (Hard Limit)
            condition_topic_shift = score < threshold
            condition_max_size = (
                current_len + sent_len
            ) > self.config.CHUNK_SIZE * 2  # Allow semantic chunks to be larger

            if (condition_topic_shift or condition_max_size) and current_len >= self.config.MIN_CHUNK_LENGTH:
                # Commit Chunk
                chunk_text = " ".join(current_chunk)
                if not self.is_junk(chunk_text):
                    chunks.append(Chunk(text=chunk_text, chunk_index=idx))
                    idx += 1

                # Start new
                current_chunk = [sent]
                current_len = sent_len
            else:
                current_chunk.append(sent)
                current_len += sent_len

        # Final bit
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if not self.is_junk(chunk_text):
                chunks.append(Chunk(text=chunk_text, chunk_index=idx))

        return chunks

    def chunk_document(
        self,
        content: str,
        metadata: Dict = None,
        strategy: str = "recursive",
        filter_junk: bool = True,
        model=None,
    ) -> List[Chunk]:
        """
        Divide a document into chunks.

        Args:
            content: The text to chunk.
            metadata: Base metadata for all chunks.
            strategy: "recursive" or "semantic" (requires model).
            filter_junk: Whether to filter out junk chunks.
            model: Embedding model for semantic strategy.
        """
        if not content:
            return []

        metadata = metadata or {}

        if strategy == "semantic" and model:
            chunks = self.semantic_split(content, model)
            # Attach metadata
            for c in chunks:
                c.metadata = metadata.copy()
            return chunks

        # Fallback / Default recursive
        return self._recursive_chunk_wrapper(content, metadata, filter_junk)

    def _recursive_chunk_wrapper(self, content: str, metadata: Dict, filter_junk: bool) -> List[Chunk]:
        """Helper for standard recursive logic."""
        chunks = []
        texts = self.recursive_split(content, self.config.CHUNK_SIZE, self.config.CHUNK_OVERLAP)
        for i, text in enumerate(texts):
            text = text.strip()
            if not filter_junk or not self.is_junk(text):
                chunks.append(Chunk(text=text, metadata=metadata.copy(), chunk_index=i))
        return chunks


# =============================================================================
# Hierarchical Parent-Child Chunker (Phase 1.1 — matches WeKnora v0.3.3)
# =============================================================================


@dataclass
class HierarchicalChunk:
    """A chunk that knows its parent context."""

    text: str  # Child chunk text (small, ~400 chars) for precise retrieval
    parent_text: str  # Parent chunk text (large, ~2000 chars) for rich context
    parent_id: str  # SHA-256 of parent_text for dedup / joining
    chunk_id: str  # SHA-256 of child text
    chunk_index: int = 0
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.parent_id:
            self.parent_id = hashlib.sha256(self.parent_text.encode()).hexdigest()
        if not self.chunk_id:
            self.chunk_id = hashlib.sha256(self.text.encode()).hexdigest()


class HierarchicalChunker:
    """
    Parent-Child hierarchical chunking strategy.

    Produces two levels:
      - Parent chunks (~2000 chars): wide context window, stored as payload in Qdrant.
      - Child chunks (~400 chars):  what gets embedded + retrieved for precision.

    At search time, child embeddings are matched but the PARENT text is fed to the LLM,
    providing much richer context while maintaining retrieval precision.

    This mirrors WeKnora v0.3.3 and the RAPTOR / SiReRAG approach from ICLR '26.

    Usage:
        hc = HierarchicalChunker(parent_size=2000, child_size=400, overlap=50)
        chunks = hc.chunk_document(text, metadata={"url": "...", "title": "..."})
        # chunks[i].text → embed this
        # chunks[i].parent_text → feed to LLM
    """

    def __init__(
        self,
        parent_size: int = 2000,
        child_size: int = 400,
        child_overlap: int = 50,
        min_child_length: int = 80,
    ):
        self.parent_size = parent_size
        self.child_size = child_size
        self.child_overlap = child_overlap
        self.min_child_length = min_child_length
        self._base_chunker = TextChunker()

    def _split(self, text: str, max_size: int, overlap: int) -> List[str]:
        """Recursive split helper."""
        return self._base_chunker.recursive_split(text, max_size, overlap)

    def chunk_document(
        self,
        content: str,
        metadata: Dict = None,
        filter_junk: bool = True,
    ) -> List[HierarchicalChunk]:
        """
        Split document into hierarchical parent-child chunks.

        Args:
            content: Full document text.
            metadata: Shared metadata attached to all chunks.
            filter_junk: Skip low-quality child chunks.

        Returns:
            List of HierarchicalChunk objects.
        """
        if not content or not content.strip():
            return []

        metadata = metadata or {}

        # Step 1: Split into large parent windows
        parent_texts = self._split(content, self.parent_size, overlap=200)

        chunks: List[HierarchicalChunk] = []
        child_global_idx = 0

        for parent_text in parent_texts:
            parent_text = parent_text.strip()
            if not parent_text:
                continue

            parent_id = hashlib.sha256(parent_text.encode()).hexdigest()

            # Step 2: Split each parent into small child chunks
            child_texts = self._split(parent_text, self.child_size, self.child_overlap)

            for child_text in child_texts:
                child_text = child_text.strip()
                if len(child_text) < self.min_child_length:
                    continue
                if filter_junk and self._base_chunker.is_junk(child_text):
                    continue

                chunk = HierarchicalChunk(
                    text=child_text,
                    parent_text=parent_text,
                    parent_id=parent_id,
                    chunk_id=hashlib.sha256(child_text.encode()).hexdigest(),
                    chunk_index=child_global_idx,
                    metadata=metadata.copy(),
                )
                chunks.append(chunk)
                child_global_idx += 1

        return chunks

    def to_flat_chunks(self, hierarchical_chunks: List[HierarchicalChunk]) -> List[Dict]:
        """
        Convert HierarchicalChunks to flat dicts compatible with LocalRAG.build_index().

        The 'text' field is the child (embedded, retrieved).
        The 'parent_text' field is stored in Qdrant payload for LLM context injection.
        """
        result = []
        for hc in hierarchical_chunks:
            flat = {
                "text": hc.text,
                "parent_text": hc.parent_text,
                "parent_id": hc.parent_id,
                "chunk_index": hc.chunk_index,
            }
            flat.update(hc.metadata)
            result.append(flat)
        return result
