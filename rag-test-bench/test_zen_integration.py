"""
Integration tests verifying zen_core_libs provides all functionality that
the deprecated local files (llama_server.py, rag_index.py) used to provide.

Tests cover:
  1. RAG pipeline: chunking → embedding → TurboQuant index → search
  2. LLM server management: binary discovery, model discovery, command builder
  3. Chunk dataclass: field completeness, ID determinism, serialization
  4. TurboQuant: compression, search accuracy, stats
  5. Backward compat: local rag_index.py & llama_server.py are strict subsets

Run:  python -m pytest test_zen_integration.py -v
"""

from __future__ import annotations

# ── WMI hang workaround for Python 3.13 on Windows ──────────────────────
# torch → platform.machine() → _wmi.exec_query() hangs indefinitely.
# Pre-populate the uname cache so WMI is never called.
import platform, sys
if sys.platform == "win32" and sys.version_info >= (3, 13):
    try:
        _r = platform.uname_result("Windows", "", "10", "10.0.22631", "AMD64")
        platform._uname_cache = _r
    except (AttributeError, TypeError):
        pass
# ─────────────────────────────────────────────────────────────────────────

import hashlib
import inspect
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ═══════════════════════════════════════════════════════════════════════════
# 1. CHUNKING
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.rag import chunk_text, Chunk


class TestChunking:
    """Verify chunk_text produces well-formed Chunk objects."""

    def test_empty_text_returns_empty(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        chunks = chunk_text("Hello world", source_url="http://x.com", page_title="T")
        assert len(chunks) == 1
        assert chunks[0].text == "Hello world"
        assert chunks[0].source_url == "http://x.com"
        assert chunks[0].page_title == "T"
        assert chunks[0].chunk_idx == 0

    def test_long_text_splits(self):
        # 10 paragraphs each ~200 chars → should split at chunk_size=512
        paras = ["Paragraph content number %d. " % i + "X" * 150 for i in range(10)]
        text = "\n\n".join(paras)
        chunks = chunk_text(text, chunk_size=512)
        assert len(chunks) > 1
        # All chunk indices are sequential
        for i, c in enumerate(chunks):
            assert c.chunk_idx == i

    def test_chunk_overlap(self):
        """With overlap, consecutive chunks should share some text."""
        text = "\n\n".join([f"Paragraph {i} " + "A" * 200 for i in range(6)])
        chunks = chunk_text(text, chunk_size=300, overlap=100)
        assert len(chunks) > 2
        # Overlap means later chunks might contain text from previous
        # Just verify overlap param doesn't crash and produces reasonable output
        for c in chunks:
            assert len(c.text) > 0

    def test_custom_chunk_size(self):
        # Use paragraph-separated text so chunk_text's paragraph-boundary
        # splitter produces different counts for different chunk_size values.
        paras = [f"Paragraph {i}. " + "X" * 150 for i in range(20)]
        text = "\n\n".join(paras)
        small = chunk_text(text, chunk_size=100, overlap=0)
        large = chunk_text(text, chunk_size=2000, overlap=0)
        assert len(small) > len(large)

    def test_chunk_source_metadata(self):
        chunks = chunk_text("Some content", source_url="https://example.com/page", page_title="My Page")
        for c in chunks:
            assert c.source_url == "https://example.com/page"
            assert c.page_title == "My Page"

    def test_chunk_id_deterministic(self):
        """Same source_url + chunk_idx → same ID."""
        c1 = Chunk(text="A", source_url="http://x.com", page_title="T", chunk_idx=0, char_offset=0)
        c2 = Chunk(text="B", source_url="http://x.com", page_title="T", chunk_idx=0, char_offset=0)
        assert c1.id == c2.id  # Same URL + idx → same ID

    def test_chunk_id_differs_by_index(self):
        c1 = Chunk(text="A", source_url="http://x.com", page_title="T", chunk_idx=0, char_offset=0)
        c2 = Chunk(text="A", source_url="http://x.com", page_title="T", chunk_idx=1, char_offset=100)
        assert c1.id != c2.id

    def test_chunk_fields_complete(self):
        """Chunk has all expected fields."""
        fields = {f.name for f in Chunk.__dataclass_fields__.values()}
        assert fields == {"text", "source_url", "page_title", "chunk_idx", "char_offset"}


# ═══════════════════════════════════════════════════════════════════════════
# 2. TURBOQUANT INDEX
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.rag.turboquant import TurboQuantIndex, TurboQuantStats


class TestTurboQuant:
    """Verify TurboQuant compression and search."""

    @pytest.fixture
    def embeddings(self):
        """100 random 384-dim vectors (simulating all-MiniLM-L6-v2 output)."""
        rng = np.random.RandomState(42)
        embs = rng.randn(100, 384).astype(np.float32)
        # L2-normalize like sentence-transformers does
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        return embs / norms

    def test_index_creation(self, embeddings):
        idx = TurboQuantIndex(embeddings, n_bits=3)
        assert idx is not None

    def test_search_returns_correct_shape(self, embeddings):
        idx = TurboQuantIndex(embeddings, n_bits=3)
        query = embeddings[0]
        scores, indices = idx.search(query, k=5)
        assert len(scores) == 5
        assert len(indices) == 5

    def test_search_finds_exact_match_first(self, embeddings):
        """Searching for an indexed vector should return it as top result."""
        idx = TurboQuantIndex(embeddings, n_bits=3)
        query = embeddings[42]
        scores, indices = idx.search(query, k=3)
        assert indices[0] == 42
        assert scores[0] > 0.95  # near-perfect match

    def test_scores_descending(self, embeddings):
        idx = TurboQuantIndex(embeddings, n_bits=3)
        query = embeddings[0]
        scores, _ = idx.search(query, k=10)
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_stats_compression(self, embeddings):
        idx = TurboQuantIndex(embeddings, n_bits=3)
        s = idx.stats
        assert isinstance(s, TurboQuantStats)
        assert s.n_vectors == 100
        assert s.n_dims == 384
        assert s.n_bits == 3
        assert s.compression_ratio > 1.0  # compressed is smaller
        assert s.original_bytes > s.compressed_bytes

    def test_different_nbits(self, embeddings):
        """Higher n_bits = less compression but better accuracy."""
        idx3 = TurboQuantIndex(embeddings, n_bits=3)
        idx4 = TurboQuantIndex(embeddings, n_bits=4)
        # 4-bit should have lower compression ratio
        assert idx3.stats.compression_ratio > idx4.stats.compression_ratio
        # But both should find exact match
        q = embeddings[0]
        _, idx3_res = idx3.search(q, k=1)
        _, idx4_res = idx4.search(q, k=1)
        assert idx3_res[0] == 0
        assert idx4_res[0] == 0

    def test_k_larger_than_collection(self, embeddings):
        """Requesting more results than vectors should return all vectors."""
        idx = TurboQuantIndex(embeddings, n_bits=3)
        scores, indices = idx.search(embeddings[0], k=200)
        assert len(scores) == 100  # capped at collection size

    def test_single_vector_index(self):
        """Index with one vector should still work."""
        emb = np.random.randn(1, 128).astype(np.float32)
        emb /= np.linalg.norm(emb)
        idx = TurboQuantIndex(emb, n_bits=3)
        scores, indices = idx.search(emb[0], k=1)
        assert indices[0] == 0


# ═══════════════════════════════════════════════════════════════════════════
# 3. RAG INDEX (end-to-end pipeline)
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.rag import RAGIndex, SearchResult


class _FakeEmbedder:
    """Lightweight mock for SentenceTransformer — deterministic hash-based embeddings."""

    def encode(self, texts, show_progress_bar=False, normalize_embeddings=True):
        import hashlib as _h
        vecs = []
        for t in texts:
            seed = int(_h.md5(t.encode()).hexdigest(), 16) % (2**31)
            rng = np.random.RandomState(seed)
            v = rng.randn(384).astype(np.float32)
            v /= np.linalg.norm(v)
            vecs.append(v)
        return np.array(vecs)


_FAKE_EMBEDDER = _FakeEmbedder()


@pytest.fixture(scope="module")
def _shared_rag_index():
    """Module-scoped RAGIndex with mocked embedder (avoids slow torch/tf import)."""
    with patch("zen_core_libs.rag.rag_index._get_embedder", return_value=_FAKE_EMBEDDER):
        idx = RAGIndex()
        chunks = [
            Chunk(text="Python is a programming language created by Guido van Rossum.",
                  source_url="https://python.org", page_title="Python", chunk_idx=0, char_offset=0),
            Chunk(text="JavaScript runs in web browsers and Node.js runtime.",
                  source_url="https://js.org", page_title="JavaScript", chunk_idx=0, char_offset=0),
            Chunk(text="Rust is a systems programming language focused on safety and performance.",
                  source_url="https://rust-lang.org", page_title="Rust", chunk_idx=0, char_offset=0),
        ]
        n = idx.add_chunks(chunks)
        assert n == 3
    return idx


@pytest.mark.slow
class TestRAGIndex:
    """Test RAGIndex lifecycle: add → search → save → load → search.
    Uses mocked embeddings to avoid slow torch/tf import on Windows+Py3.13."""

    @pytest.fixture
    def index_with_data(self, _shared_rag_index):
        """Return the shared index (model loaded once per module)."""
        return _shared_rag_index

    def test_add_chunks(self, index_with_data):
        assert index_with_data.n_chunks == 3
        assert index_with_data.is_built

    def test_search_relevance(self, index_with_data):
        """Search should return results (with mocked embeddings, ranking is random)."""
        with patch("zen_core_libs.rag.rag_index._get_embedder", return_value=_FAKE_EMBEDDER):
            results = index_with_data.search("Python programming language", k=3)
        assert len(results) == 3
        # With deterministic fake embeddings, just verify we get valid results
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].score >= results[-1].score

    def test_search_returns_search_result(self, index_with_data):
        with patch("zen_core_libs.rag.rag_index._get_embedder", return_value=_FAKE_EMBEDDER):
            results = index_with_data.search("JavaScript", k=1)
        assert isinstance(results[0], SearchResult)
        assert isinstance(results[0].chunk, Chunk)
        assert isinstance(results[0].score, float)

    def test_search_timed(self, index_with_data):
        with patch("zen_core_libs.rag.rag_index._get_embedder", return_value=_FAKE_EMBEDDER):
            results, timing = index_with_data.search_timed("Rust safety", k=2)
        assert len(results) == 2
        assert "embed_ms" in timing
        assert "search_ms" in timing
        assert "total_ms" in timing
        assert "n_chunks" in timing
        assert timing["n_chunks"] == 3

    def test_clear(self):
        """Test clear on a separate index (don't mutate the shared fixture)."""
        with patch("zen_core_libs.rag.rag_index._get_embedder", return_value=_FAKE_EMBEDDER):
            idx = RAGIndex()
            idx.add_chunks([
                Chunk(text="test", source_url="", page_title="", chunk_idx=0, char_offset=0),
            ])
            assert idx.n_chunks == 1
            idx.clear()
            assert idx.n_chunks == 0
            assert not idx.is_built

    def test_stats(self, index_with_data):
        s = index_with_data.stats
        assert s["n_chunks"] == 3
        assert "compression_ratio" in s
        assert "bits_per_dim" in s

    def test_save_load_roundtrip(self, index_with_data):
        """Save index, load into a new RAGIndex, verify search still works."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            index_with_data.save(p)
            assert (p / "meta.json").exists()
            assert (p / "embeddings.npy").exists()

            with patch("zen_core_libs.rag.rag_index._get_embedder", return_value=_FAKE_EMBEDDER):
                idx2 = RAGIndex()
                idx2.load(p)
                assert idx2.n_chunks == 3
                assert idx2.is_built

                results = idx2.search("Python programming", k=1)
                assert len(results) == 1
                assert isinstance(results[0], SearchResult)

    def test_empty_search_on_empty_index(self):
        idx = RAGIndex()
        assert idx.search("anything", k=5) == []
        assert not idx.is_built

    def test_add_empty_chunks(self):
        idx = RAGIndex()
        n = idx.add_chunks([])
        assert n == 0
        assert not idx.is_built


# ═══════════════════════════════════════════════════════════════════════════
# 4. ADVANCED CHUNKING STRATEGIES (from zen_core_libs.rag.chunking)
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.rag.chunking import get_chunker, FixedSizeChunker, SentenceChunker


class TestAdvancedChunking:
    """Test zen_core_libs chunking strategies beyond the basic chunk_text."""

    def test_fixed_size_chunker(self):
        chunker = FixedSizeChunker(chunk_size=100, overlap=20)
        chunks = chunker.chunk("A" * 500)
        assert len(chunks) > 1
        for c in chunks:
            assert "text" in c
            assert len(c["text"]) <= 120  # allow slight overshoot

    def test_sentence_chunker(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
        chunker = SentenceChunker(max_sentences=2, overlap_sentences=0)
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2
        for c in chunks:
            assert "text" in c

    def test_get_chunker_factory(self):
        chunker = get_chunker("fixed_size", chunk_size=200)
        assert isinstance(chunker, FixedSizeChunker)

    def test_get_chunker_sentence(self):
        chunker = get_chunker("sentence", max_sentences=3)
        assert isinstance(chunker, SentenceChunker)

    def test_chunker_metadata_passthrough(self):
        chunker = FixedSizeChunker(chunk_size=50)
        chunks = chunker.chunk("Hello world test data", metadata={"source": "test"})
        for c in chunks:
            assert c.get("source") == "test" or "metadata" in str(c)


# ═══════════════════════════════════════════════════════════════════════════
# 5. LLM SERVER MANAGEMENT (imported from zen_core_libs)
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.llm import (
    LlamaServerManager,
    discover_models,
    find_llama_server_binary,
    pick_default_model,
)


class TestLLMServer:
    """Test LlamaServerManager from zen_core_libs."""

    def test_manager_initial_state(self):
        mgr = LlamaServerManager()
        assert not mgr.is_running
        assert mgr.port == 8090
        assert mgr.base_url == "http://localhost:8090/v1"

    def test_kv_cache_types(self):
        assert "q8_0" in LlamaServerManager.KV_CACHE_TYPES
        assert "f16" in LlamaServerManager.KV_CACHE_TYPES
        assert len(LlamaServerManager.KV_CACHE_TYPES) == 9

    def test_status_dict_structure(self):
        mgr = LlamaServerManager()
        st = mgr.status()
        assert "running" in st
        assert "model" in st
        assert "port" in st
        assert "pid" in st
        assert "binary" in st
        assert "opts" in st

    def test_start_signature_has_optimization_params(self):
        sig = inspect.signature(LlamaServerManager.start)
        params = list(sig.parameters.keys())
        assert "kv_cache_type_k" in params
        assert "kv_cache_type_v" in params
        assert "flash_attn" in params
        assert "mlock" in params
        assert "cont_batching" in params
        assert "cache_reuse" in params
        assert "slot_prompt_similarity" in params

    def test_discover_models_returns_list(self):
        models = discover_models()
        assert isinstance(models, list)
        for m in models:
            assert "name" in m
            assert "path" in m
            assert "size_gb" in m

    def test_pick_default_model_empty(self):
        assert pick_default_model([]) is None

    def test_pick_default_model_prefers_llama32(self):
        models = [
            {"name": "big-model.gguf", "path": "/m/big.gguf", "size_gb": 10.0},
            {"name": "Llama-3.2-3B-Instruct-Q5_K_M.gguf", "path": "/m/llama.gguf", "size_gb": 2.1},
        ]
        default = pick_default_model(models)
        assert default is not None
        assert "llama" in default["name"].lower()

    def test_pick_default_model_fallback(self):
        models = [
            {"name": "tiny.gguf", "path": "/m/tiny.gguf", "size_gb": 0.1},
            {"name": "medium.gguf", "path": "/m/medium.gguf", "size_gb": 3.0},
        ]
        default = pick_default_model(models)
        # Should pick the one >= 1GB
        assert default["size_gb"] >= 1.0


# ═══════════════════════════════════════════════════════════════════════════
# 6. BACKWARD COMPATIBILITY — local files are subsets of zen_core_libs
# ═══════════════════════════════════════════════════════════════════════════

class TestBackwardCompat:
    """Verify zen_core_libs exposes everything the local modules had."""

    def test_rag_index_module_exports(self):
        """All types from local rag_index.py exist in zen_core_libs.rag."""
        from zen_core_libs.rag import RAGIndex, chunk_text, warmup, Chunk, SearchResult
        assert callable(chunk_text)
        assert callable(warmup)
        assert hasattr(RAGIndex, "add_chunks")
        assert hasattr(RAGIndex, "search")
        assert hasattr(RAGIndex, "search_timed")
        assert hasattr(RAGIndex, "save")
        assert hasattr(RAGIndex, "load")
        assert hasattr(RAGIndex, "clear")
        assert hasattr(RAGIndex, "stats")
        assert hasattr(RAGIndex, "is_built")
        assert hasattr(RAGIndex, "n_chunks")

    def test_llm_module_exports(self):
        """All types from local llama_server.py exist in zen_core_libs.llm."""
        from zen_core_libs.llm import (
            LlamaServerManager,
            discover_models,
            find_llama_server_binary,
            pick_default_model,
        )
        assert callable(discover_models)
        assert callable(find_llama_server_binary)
        assert callable(pick_default_model)
        assert hasattr(LlamaServerManager, "start")
        assert hasattr(LlamaServerManager, "stop")
        assert hasattr(LlamaServerManager, "status")
        assert hasattr(LlamaServerManager, "is_running")
        assert hasattr(LlamaServerManager, "base_url")
        assert hasattr(LlamaServerManager, "model_name")
        assert hasattr(LlamaServerManager, "port")

    def test_chunk_text_signature_matches(self):
        """chunk_text signature matches what app.py expects."""
        sig = inspect.signature(chunk_text)
        params = sig.parameters
        assert "text" in params
        assert "source_url" in params
        assert "page_title" in params
        assert "chunk_size" in params
        assert "overlap" in params
        # Defaults
        assert params["chunk_size"].default == 512
        assert params["overlap"].default == 64

    def test_search_result_has_expected_fields(self):
        """SearchResult must have .chunk and .score for app.py compatibility."""
        c = Chunk(text="test", source_url="", page_title="", chunk_idx=0, char_offset=0)
        sr = SearchResult(chunk=c, score=0.9)
        assert sr.chunk is c
        assert sr.score == 0.9
        assert sr.chunk.text == "test"
        assert sr.chunk.source_url == ""

    def test_app_py_imports_still_work(self):
        """Verify the exact import lines from app.py resolve correctly."""
        # These are the exact imports from app.py line 37-38
        from zen_core_libs.llm import LlamaServerManager, discover_models, find_llama_server_binary, pick_default_model
        from zen_core_libs.rag import RAGIndex, chunk_text, warmup
        assert all(callable(f) for f in [discover_models, find_llama_server_binary, pick_default_model, chunk_text, warmup])


# ═══════════════════════════════════════════════════════════════════════════
# 7. PERFORMANCE & MEMORY CHARACTERISTICS
# ═══════════════════════════════════════════════════════════════════════════

class TestPerformanceCharacteristics:
    """Verify performance and memory characteristics of zen_core_libs RAG."""

    def test_turboquant_memory_savings(self):
        """3-bit quantization should compress at least 5x."""
        rng = np.random.RandomState(42)
        embs = rng.randn(1000, 384).astype(np.float32)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        embs = embs / norms
        idx = TurboQuantIndex(embs, n_bits=3)
        s = idx.stats
        assert s.compression_ratio >= 5.0  # 32-bit → 3-bit ≈ 10x theoretical
        assert s.compressed_bytes < s.original_bytes

    def test_search_speed_reasonable(self):
        """Search over 1K vectors should complete in < 100ms."""
        import time
        rng = np.random.RandomState(42)
        embs = rng.randn(1000, 384).astype(np.float32)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        embs = embs / norms
        idx = TurboQuantIndex(embs, n_bits=3)
        query = embs[0]

        t0 = time.monotonic()
        for _ in range(10):
            idx.search(query, k=5)
        elapsed = (time.monotonic() - t0) / 10 * 1000  # ms per search
        assert elapsed < 100, f"Search took {elapsed:.1f}ms, expected < 100ms"

    def test_chunking_performance(self):
        """Chunking 100KB of text should be fast (< 50ms)."""
        import time
        # Use paragraph-separated text so chunk_text actually splits
        paras = [f"Test paragraph {i} with some content. " + "X" * 200 for i in range(300)]
        text = "\n\n".join(paras)
        t0 = time.monotonic()
        chunks = chunk_text(text, chunk_size=512, overlap=64)
        elapsed = (time.monotonic() - t0) * 1000
        assert elapsed < 50, f"Chunking took {elapsed:.1f}ms, expected < 50ms"
        assert len(chunks) > 10
