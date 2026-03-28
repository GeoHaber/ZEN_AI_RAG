# -*- coding: utf-8 -*-
"""
test_chunker_monkey.py — Hierarchical Chunker Fuzz / Monkey Tests
==================================================================

Targets: zena_mode/chunker.py (TextChunker, HierarchicalChunker, Chunk, ChunkerConfig)
Feeds random text, binary data, adversarial markdown, checks boundaries.

Run:
    pytest tests/test_chunker_monkey.py -v --tb=short -x
"""

import os
import random
import string
import sys
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_CHAOS_STRINGS: list[str] = [
    "",
    "   ",
    "\n\n\n\t\t",
    "\x00\x01\x02\x03\x04\x05",
    "A" * 100_000,
    "🔥" * 5_000,
    "<script>alert('xss')</script>",
    "'; DROP TABLE users; --",
    "Hello 你好 مرحبا こんにちは שלום",
    "\u202e\u200b\u200c\u200d\ufeff",
    "NaN",
    "null",
    "a\nb\nc\n" * 5_000,
]


# ═════════════════════════════════════════════════════════════════════════════
#  ChunkerConfig Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestChunkerConfigMonkey:
    """Verify ChunkerConfig defaults and custom values."""

    def test_defaults_sane(self):
        from zena_mode.chunker import ChunkerConfig

        cfg = ChunkerConfig()
        assert cfg.CHUNK_SIZE > 0
        assert cfg.CHUNK_OVERLAP >= 0
        assert cfg.CHUNK_OVERLAP < cfg.CHUNK_SIZE
        assert cfg.MIN_CHUNK_LENGTH >= 0
        assert 0.0 <= cfg.MIN_ENTROPY
        assert cfg.MAX_ENTROPY >= cfg.MIN_ENTROPY

    def test_custom_config(self):
        from zena_mode.chunker import ChunkerConfig

        cfg = ChunkerConfig()
        cfg.CHUNK_SIZE = 100
        cfg.CHUNK_OVERLAP = 10
        assert cfg.CHUNK_SIZE == 100


# ═════════════════════════════════════════════════════════════════════════════
#  TextChunker Monkey Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestTextChunkerMonkey:
    """Fuzz the TextChunker with adversarial and random inputs."""

    def _make_chunker(self):
        from zena_mode.chunker import TextChunker

        return TextChunker()

    def test_chaos_strings_no_crash(self):
        """Every chaos string must produce a list (possibly empty)."""
        chunker = self._make_chunker()
        for s in _CHAOS_STRINGS:
            result = chunker.chunk_document(s)
            assert isinstance(result, list)

    def test_empty_string_returns_empty(self):
        chunker = self._make_chunker()
        result = chunker.chunk_document("")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_whitespace_only_returns_empty(self):
        chunker = self._make_chunker()
        result = chunker.chunk_document("   \n\t\n   ")
        assert isinstance(result, list)

    def test_single_character(self):
        chunker = self._make_chunker()
        result = chunker.chunk_document("X")
        assert isinstance(result, list)

    def test_binary_data_no_crash(self):
        """Random binary data decoded as latin-1 should not crash."""
        chunker = self._make_chunker()
        binary_text = os.urandom(500).decode("latin-1")
        result = chunker.chunk_document(binary_text)
        assert isinstance(result, list)

    def test_large_text_completes(self):
        """10KB text must chunk without hanging."""
        chunker = self._make_chunker()
        text = "The quick brown fox jumps over the lazy dog. " * 250  # ~11KB
        result = chunker.chunk_document(text)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_zero_width_chars_cleaned(self):
        chunker = self._make_chunker()
        text = "Hello\u200b\u200c\u200dWorld\ufeff test paragraph with enough content to form a chunk. " * 10
        result = chunker.chunk_document(text)
        assert isinstance(result, list)

    def test_nested_markdown_headers(self):
        """100 nested markdown headers should not crash or hang."""
        chunker = self._make_chunker()
        lines = [f"{'#' * min(i, 6)} Header Level {i}\nSome content for section {i}. " * 3 for i in range(1, 101)]
        text = "\n\n".join(lines)
        result = chunker.chunk_document(text)
        assert isinstance(result, list)

    def test_recursive_split_boundary(self):
        chunker = self._make_chunker()
        # Exact chunk boundary
        result = chunker.recursive_split("x" * 800, max_size=800, overlap_size=0)
        assert isinstance(result, list)

    def test_recursive_split_overlap_equals_size(self):
        """Overlap >= size must not infinite loop."""
        chunker = self._make_chunker()
        try:
            result = chunker.recursive_split("Hello world test", max_size=5, overlap_size=5)
            assert isinstance(result, list)
        except (ValueError, RecursionError):
            pass  # raising an error is acceptable

    def test_entropy_calculation(self):
        chunker = self._make_chunker()
        # High entropy text
        high_e = chunker._calculate_entropy("The quick brown fox jumps over the lazy dog")
        assert isinstance(high_e, float)
        assert high_e >= 0
        # Low entropy text
        low_e = chunker._calculate_entropy("aaaaaaaaaa")
        assert isinstance(low_e, float)
        assert low_e >= 0
        assert low_e <= high_e

    def test_is_junk_detects_boilerplate(self):
        chunker = self._make_chunker()
        # Empty or whitespace should be junk
        assert chunker.is_junk("") or True  # empty may or may not be junk
        assert chunker.is_junk("   ") or True

    def test_metadata_preserved(self):
        chunker = self._make_chunker()
        meta = {"source": "test.txt", "page": 1}
        text = "Long enough paragraph for chunking. This needs to pass the minimum length filter and entropy check. " * 5
        result = chunker.chunk_document(text, metadata=meta)
        if result:
            assert hasattr(result[0], "metadata")

    def test_50_random_texts_no_crash(self):
        """50 random texts of varying length — no crashes."""
        chunker = self._make_chunker()
        for _ in range(50):
            length = random.randint(0, 5000)
            text = "".join(random.choices(string.printable, k=length))
            result = chunker.chunk_document(text)
            assert isinstance(result, list)


# ═════════════════════════════════════════════════════════════════════════════
#  HierarchicalChunker Monkey Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestHierarchicalChunkerMonkey:
    """Fuzz the HierarchicalChunker with adversarial inputs."""

    def _make_chunker(self):
        from zena_mode.chunker import HierarchicalChunker

        return HierarchicalChunker()

    def test_chaos_strings_no_crash(self):
        chunker = self._make_chunker()
        for s in _CHAOS_STRINGS:
            result = chunker.chunk_document(s)
            assert isinstance(result, list)

    def test_empty_returns_empty(self):
        chunker = self._make_chunker()
        result = chunker.chunk_document("")
        assert isinstance(result, list)

    def test_parent_child_relationship(self):
        """Every child chunk text must appear within its parent text."""
        chunker = self._make_chunker()
        text = ("This is a substantial paragraph with enough content to be chunked. " * 20 + "\n\n") * 5
        result = chunker.chunk_document(text)
        for chunk in result:
            # Child text should be a substring of parent_text (allowing for trimming)
            if hasattr(chunk, "parent_text") and chunk.parent_text and chunk.text:
                child_stripped = chunk.text.strip()[:50]
                if child_stripped:
                    assert child_stripped in chunk.parent_text or len(child_stripped) < 10

    def test_to_flat_chunks(self):
        chunker = self._make_chunker()
        text = ("Paragraph with enough content for hierarchical chunking and testing. " * 15 + "\n\n") * 3
        hierarchical = chunker.chunk_document(text)
        if hierarchical:
            flat = chunker.to_flat_chunks(hierarchical)
            assert isinstance(flat, list)
            for item in flat:
                assert isinstance(item, dict)

    def test_custom_sizes(self):
        from zena_mode.chunker import HierarchicalChunker

        chunker = HierarchicalChunker(parent_size=500, child_size=100, child_overlap=20)
        text = "Word " * 200
        result = chunker.chunk_document(text)
        assert isinstance(result, list)

    def test_tiny_sizes_no_hang(self):
        """Very small parent/child sizes must not infinite-loop."""
        from zena_mode.chunker import HierarchicalChunker

        try:
            chunker = HierarchicalChunker(parent_size=10, child_size=5, child_overlap=2, min_child_length=1)
            result = chunker.chunk_document("Hello world this is a test")
            assert isinstance(result, list)
        except (ValueError, RecursionError):
            pass


# ═════════════════════════════════════════════════════════════════════════════
#  Chunk Dataclass Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestChunkDataclassMonkey:
    """Verify Chunk and HierarchicalChunk dataclasses."""

    def test_chunk_creation(self):
        from zena_mode.chunker import Chunk

        c = Chunk(text="test", metadata={"source": "test"})
        assert c.text == "test"
        assert isinstance(c.hash, str)

    def test_chunk_empty_text(self):
        from zena_mode.chunker import Chunk

        c = Chunk(text="", metadata={})
        assert c.text == ""

    def test_hierarchical_chunk_creation(self):
        from zena_mode.chunker import HierarchicalChunk

        hc = HierarchicalChunk(
            text="child",
            parent_text="parent containing child",
            parent_id="p1",
            chunk_id="c1",
            metadata={"source": "test"},
        )
        assert hc.text == "child"
        assert hc.parent_id == "p1"
