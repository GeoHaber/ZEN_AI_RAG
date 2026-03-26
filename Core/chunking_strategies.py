"""
Core/chunking_strategies.py - Advanced chunking for better retrieval

Strategies:
- Semantic chunking (split by topic changes)
- Recursive chunking (preserve context hierarchy)
- Sliding window (overlap for continuity)
- Document-aware (respect structure: paragraphs, sections)
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ChunkingStrategy(ABC):
    """Base class for chunking strategies"""

    @abstractmethod
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Chunk text into smaller pieces

        Args:
            text: Text to chunk
            metadata: Optional metadata to include with chunks

        Returns:
            List of chunk dicts with text and metadata
        """
        pass


class FixedSizeChunker(ChunkingStrategy):
    """Simple fixed-size chunking (baseline)"""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        Initialize fixed-size chunker

        Args:
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters
        """
        self.chunk_size = max(1, chunk_size)
        # Guard: overlap must be strictly less than chunk_size to prevent infinite loop
        self.overlap = min(overlap, self.chunk_size - 1)

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """Chunk text into fixed-size pieces with overlap"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            if chunk_text.strip():
                chunks.append(
                    {
                        "text": chunk_text,
                        "metadata": {
                            **(metadata or {}),
                            "chunk_index": len(chunks),
                            "start_char": start,
                            "end_char": end,
                            "strategy": "fixed_size",
                        },
                    }
                )

            start += self.chunk_size - self.overlap

        logger.info(f"Fixed-size chunking: {len(chunks)} chunks created")
        return chunks


class SentenceChunker(ChunkingStrategy):
    """Chunk by sentences (respects sentence boundaries)"""

    def __init__(self, max_sentences: int = 5, overlap_sentences: int = 1):
        """
        Initialize sentence chunker

        Args:
            max_sentences: Maximum sentences per chunk
            overlap_sentences: Number of sentences to overlap (must be < max_sentences)
        """
        self.max_sentences = max(1, max_sentences)
        # Guard against infinite loop: overlap must be strictly less than max
        self.overlap_sentences = min(overlap_sentences, self.max_sentences - 1)

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """Chunk text by sentences"""
        if not text or not text.strip():
            return []

        # Split into sentences
        sentences = self._split_sentences(text)

        if not sentences:
            return []

        chunks = []
        step = max(1, self.max_sentences - self.overlap_sentences)
        i = 0

        while i < len(sentences):
            # Take max_sentences
            chunk_sentences = sentences[i : i + self.max_sentences]
            chunk_text = " ".join(chunk_sentences)

            if chunk_text.strip():
                chunks.append(
                    {
                        "text": chunk_text,
                        "metadata": {
                            **(metadata or {}),
                            "chunk_index": len(chunks),
                            "sentence_count": len(chunk_sentences),
                            "strategy": "sentence",
                        },
                    }
                )

            # Move forward with overlap (safe step >= 1)
            i += step

        logger.info(f"Sentence chunking: {len(chunks)} chunks from {len(sentences)} sentences")
        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences (preserves punctuation)"""
        # Use lookbehind to keep the sentence-ending punctuation attached
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]


class ParagraphChunker(ChunkingStrategy):
    """Chunk by paragraphs (respects paragraph boundaries)"""

    def __init__(self, max_paragraphs: int = 3, min_chunk_size: int = 100):
        """
        Initialize paragraph chunker

        Args:
            max_paragraphs: Maximum paragraphs per chunk
            min_chunk_size: Minimum chunk size in characters
        """
        self.max_paragraphs = max_paragraphs
        self.min_chunk_size = min_chunk_size

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """Chunk text by paragraphs"""
        # Split into paragraphs
        paragraphs = self._split_paragraphs(text)

        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            current_chunk.append(para)
            current_size += len(para)

            # Create chunk if we hit max paragraphs or good size
            if len(current_chunk) >= self.max_paragraphs or current_size >= self.min_chunk_size * 3:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(
                    {
                        "text": chunk_text,
                        "metadata": {
                            **(metadata or {}),
                            "chunk_index": len(chunks),
                            "paragraph_count": len(current_chunk),
                            "strategy": "paragraph",
                        },
                    }
                )

                current_chunk = []
                current_size = 0

        # Add remaining — merge into last chunk if below min_chunk_size
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(
                    {
                        "text": chunk_text,
                        "metadata": {
                            **(metadata or {}),
                            "chunk_index": len(chunks),
                            "paragraph_count": len(current_chunk),
                            "strategy": "paragraph",
                        },
                    }
                )
            elif chunks:
                # Merge small remainder into the previous chunk to prevent content loss
                prev_text = chunks[-1]["text"]
                chunks[-1]["text"] = prev_text + "\n\n" + chunk_text
                chunks[-1]["metadata"]["paragraph_count"] += len(current_chunk)
            else:
                # Only chunk and it's small — include it anyway
                chunks.append(
                    {
                        "text": chunk_text,
                        "metadata": {
                            **(metadata or {}),
                            "chunk_index": 0,
                            "paragraph_count": len(current_chunk),
                            "strategy": "paragraph",
                        },
                    }
                )

        logger.info(f"Paragraph chunking: {len(chunks)} chunks from {len(paragraphs)} paragraphs")
        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]


class SlidingWindowChunker(ChunkingStrategy):
    """Sliding window chunking with configurable overlap"""

    def __init__(self, window_size: int = 500, step_size: int = 250):
        """
        Initialize sliding window chunker

        Args:
            window_size: Size of each window in characters
            step_size: Step size (window_size - overlap)
        """
        self.window_size = window_size
        self.step_size = step_size
        self.overlap = window_size - step_size

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """Chunk text using sliding window"""
        chunks = []

        for start in range(0, len(text), self.step_size):
            end = start + self.window_size
            chunk_text = text[start:end]

            if chunk_text.strip() and len(chunk_text) >= self.window_size // 2:
                chunks.append(
                    {
                        "text": chunk_text,
                        "metadata": {
                            **(metadata or {}),
                            "chunk_index": len(chunks),
                            "start_char": start,
                            "end_char": end,
                            "overlap": self.overlap,
                            "strategy": "sliding_window",
                        },
                    }
                )

        logger.info(
            f"Sliding window chunking: {len(chunks)} chunks (window={self.window_size}, overlap={self.overlap})"
        )
        return chunks


class RecursiveChunker(ChunkingStrategy):
    """Recursive chunking that preserves hierarchy"""

    def __init__(self, max_chunk_size: int = 1000, min_chunk_size: int = 100):
        """
        Initialize recursive chunker

        Args:
            max_chunk_size: Maximum chunk size
            min_chunk_size: Minimum chunk size
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size

        # Separators in order of preference
        self.separators = [
            "\n\n\n",  # Multiple newlines
            "\n\n",  # Paragraphs
            "\n",  # Lines
            ". ",  # Sentences
            " ",  # Words
        ]

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """Recursively chunk text preserving structure"""
        chunks = self._recursive_split(text, 0)

        # Add metadata
        result = []
        for i, chunk_text in enumerate(chunks):
            if chunk_text.strip():
                result.append(
                    {
                        "text": chunk_text,
                        "metadata": {
                            **(metadata or {}),
                            "chunk_index": i,
                            "strategy": "recursive",
                        },
                    }
                )

        logger.info(f"Recursive chunking: {len(result)} chunks")
        return result

    def _recursive_split(self, text: str, separator_index: int) -> List[str]:
        """Recursively split text using separators"""
        # Base case: text is small enough
        if len(text) <= self.max_chunk_size:
            # Keep text even if below min_chunk_size to prevent content loss
            return [text] if text.strip() else []

        # Try current separator
        if separator_index >= len(self.separators):
            # No more separators, force split
            return [text[i : i + self.max_chunk_size] for i in range(0, len(text), self.max_chunk_size)]

        separator = self.separators[separator_index]
        splits = text.split(separator)

        # Combine splits into chunks
        chunks = []
        current_chunk = []
        current_size = 0

        for split in splits:
            # Separator only appears between parts in joined text, not after each part
            if current_chunk:
                split_size = len(separator) + len(split)
            else:
                split_size = len(split)

            if current_size + split_size > self.max_chunk_size and current_chunk:
                # Current chunk is full, save it
                chunk_text = separator.join(current_chunk)
                chunks.append(chunk_text)
                current_chunk = [split]
                current_size = len(split)
            else:
                current_chunk.append(split)
                current_size += split_size

        # Add remaining
        if current_chunk:
            chunks.append(separator.join(current_chunk))

        # Recursively split chunks that are still too large
        result = []
        for chunk in chunks:
            if len(chunk) > self.max_chunk_size:
                result.extend(self._recursive_split(chunk, separator_index + 1))
            else:
                result.append(chunk)

        return result


class MarkdownChunker(ChunkingStrategy):
    """Chunk markdown documents by sections"""

    def __init__(self, max_section_size: int = 1500):
        """
        Initialize markdown chunker

        Args:
            max_section_size: Maximum section size in characters
        """
        self.max_section_size = max_section_size

    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """Chunk markdown by sections (headers)"""
        # Find all headers
        sections = self._split_by_headers(text)

        chunks = []
        for section_title, section_text in sections:
            # If section is too large, split it further
            if len(section_text) > self.max_section_size:
                # Use paragraph chunker for large sections
                para_chunker = ParagraphChunker(max_paragraphs=2)
                sub_chunks = para_chunker.chunk(section_text)

                for sub_chunk in sub_chunks:
                    chunks.append(
                        {
                            "text": sub_chunk["text"],
                            "metadata": {
                                **(metadata or {}),
                                "chunk_index": len(chunks),
                                "section": section_title,
                                "strategy": "markdown",
                            },
                        }
                    )
            else:
                chunks.append(
                    {
                        "text": section_text,
                        "metadata": {
                            **(metadata or {}),
                            "chunk_index": len(chunks),
                            "section": section_title,
                            "strategy": "markdown",
                        },
                    }
                )

        logger.info(f"Markdown chunking: {len(chunks)} chunks from {len(sections)} sections")
        return chunks

    def _split_by_headers(self, text: str) -> List[Tuple[str, str]]:
        """Split markdown by headers"""
        # Find all headers (# Header)
        header_pattern = r"^(#{1,6})\s+(.+)$"

        sections = []
        current_title = "Introduction"
        current_content = []

        for line in text.split("\n"):
            match = re.match(header_pattern, line)

            if match:
                # Save previous section
                if current_content:
                    sections.append((current_title, "\n".join(current_content)))

                # Start new section
                current_title = match.group(2).strip()
                current_content = []
            else:
                current_content.append(line)

        # Add last section
        if current_content:
            sections.append((current_title, "\n".join(current_content)))

        return sections


# Factory function
def get_chunker(strategy: str = "sentence", **kwargs) -> ChunkingStrategy:
    """
    Get chunking strategy by name

    Args:
        strategy: Strategy name (fixed_size, sentence, paragraph, sliding_window, recursive, markdown)
        **kwargs: Strategy-specific parameters

    Returns:
        ChunkingStrategy instance
    """
    strategies = {
        "fixed_size": FixedSizeChunker,
        "sentence": SentenceChunker,
        "paragraph": ParagraphChunker,
        "sliding_window": SlidingWindowChunker,
        "recursive": RecursiveChunker,
        "markdown": MarkdownChunker,
    }

    if strategy not in strategies:
        raise ValueError(f"Unknown strategy: {strategy}. Available: {list(strategies.keys())}")

    return strategies[strategy](**kwargs)
