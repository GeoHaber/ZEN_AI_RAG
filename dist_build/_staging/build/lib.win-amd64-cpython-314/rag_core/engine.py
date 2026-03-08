"""
rag_core.engine — Unified RAG Engine
======================================

Single entry point for all RAG operations: index, search, groups.
Combines chunker, embeddings, BM25, RRF fusion, reranker, cache, and dedup
into one coherent async-friendly API.

Usage::

    from rag_core import RAGEngine

    rag = RAGEngine(collection="my_project", prefer_code=True)
    await rag.initialize()
    n = await rag.build_index(documents)
    results = await rag.search("parse config file", top_k=10)
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from rag_core.bm25_index import BM25Index
from rag_core.cache import SemanticCache
from rag_core.chunker import ChunkerConfig, TextChunker
from rag_core.dedup import DeduplicationManager
from rag_core.embeddings import EmbeddingManager
from rag_core.reranker import RerankerManager
from rag_core.search import HybridSearcher, SearchResult

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Unified RAG engine — the standard pipeline for all projects.

    Tier 1 — Full pipeline (recommended)::

        Documents → Chunker → Embed → Dedup → BM25 Index
                                                    ↓
        Query → Dense + BM25 → RRF → Rerank → Results

    Tier 2 — Qdrant bridge (when available)::

        Delegates to existing Qdrant-backed LocalRAG for persistent storage.

    Tier 3 — BM25-only fallback::

        No neural models — pure keyword search.

    Args:
        collection: Name for this RAG collection (e.g. "function_catalog").
        storage_dir: Directory for persistent caches.
        prefer_code: Prefer code embedding models (GraphCodeBERT).
        embedding_model: Override specific embedding model name.
        reranker_model: Override specific reranker model name.
        chunk_strategy: "sentence" | "fixed" | "code".
        chunk_size: Characters per chunk.
        chunk_overlap: Overlap between chunks.
        rrf_k: RRF fusion constant.
        dense_weight: Weight for dense vs BM25 (0-1).
        cache_ttl: Semantic cache TTL in seconds.
        dedup_threshold: Near-duplicate similarity threshold.
    """

    def __init__(
        self,
        collection: str = "default",
        storage_dir: Optional[Path] = None,
        prefer_code: bool = False,
        embedding_model: Optional[str] = None,
        reranker_model: Optional[str] = None,
        chunk_strategy: str = "sentence",
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        rrf_k: int = 60,
        dense_weight: float = 0.6,
        cache_ttl: float = 600.0,
        dedup_threshold: float = 0.95,
    ):
        self.collection = collection
        self.storage_dir = Path(storage_dir) if storage_dir else Path.cwd() / "rag_storage"

        # Components (created on initialize)
        self._embeddings = EmbeddingManager(
            model_name=embedding_model,
            prefer_code=prefer_code,
        )
        self._reranker = RerankerManager(model_name=reranker_model)
        self._bm25 = BM25Index(code_aware=prefer_code)
        self._chunker = TextChunker(
            ChunkerConfig(
                CHUNK_SIZE=chunk_size,
                CHUNK_OVERLAP=chunk_overlap,
            )
        )
        self._dedup = DeduplicationManager(similarity_threshold=dedup_threshold)
        self._cache: Optional[SemanticCache] = None
        self._searcher: Optional[HybridSearcher] = None

        # Config
        self._chunk_strategy = chunk_strategy
        self._rrf_k = rrf_k
        self._dense_weight = dense_weight
        self._cache_ttl = cache_ttl

        # State
        self._initialised = False
        self._backend: str = "none"  # "full" | "bm25_only"

    # ----- Properties -------------------------------------------------------

    @property
    def initialised(self) -> bool:
        return self._initialised

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def embedding_model(self) -> str:
        if self._embeddings.is_loaded:
            return self._embeddings.model_type
        return "none"

    @property
    def doc_count(self) -> int:
        if self._searcher:
            return self._searcher.doc_count
        return 0

    # ----- Lifecycle --------------------------------------------------------

    async def initialize(
        self,
        progress: Optional[Callable[[str, float], None]] = None,
    ) -> bool:
        """Initialise the RAG pipeline (load models).

        Returns True if at least BM25 is available.
        """

        def _p(msg: str, pct: float = 0.0):
            if progress:
                progress(msg, pct)
            logger.info("[RAGEngine] %s", msg)

        _p("Initialising RAG engine ...", 0.0)

        # Load embedding model
        _p("Loading embedding model ...", 0.1)
        has_embeddings = self._embeddings.load()

        if has_embeddings:
            _p(f"Embeddings: {self._embeddings.model_type} (dim={self._embeddings.dimension})", 0.3)
            self._backend = "full"
        else:
            _p("No embedding model — BM25-only mode", 0.3)
            self._backend = "bm25_only"

        # Load reranker
        _p("Loading reranker ...", 0.4)
        has_reranker = self._reranker.load()
        if has_reranker:
            _p(f"Reranker: {self._reranker.model_name}", 0.5)
        else:
            _p("No reranker available — skipping reranking", 0.5)

        # Build searcher
        self._searcher = HybridSearcher(
            embeddings=self._embeddings if has_embeddings else None,
            bm25=self._bm25,
            reranker=self._reranker if has_reranker else None,
            rrf_k=self._rrf_k,
            dense_weight=self._dense_weight,
        )

        # Build cache
        self._cache = SemanticCache(
            ttl=self._cache_ttl,
            encoder=self._embeddings if has_embeddings else None,
        )

        self._initialised = True
        _p("RAG engine ready", 0.6)
        return True

    # ----- Indexing ----------------------------------------------------------

    async def build_index(
        self,
        documents: List[Dict[str, Any]],
        *,
        progress: Optional[Callable[[str, float], None]] = None,
        chunk: bool = True,
        filter_junk: bool = True,
    ) -> int:
        """Index documents.

        Args:
            documents: List of ``{"text": "...", "url": "...", "title": "...", "metadata": {}}``
            progress: ``(message, 0-1) -> None`` callback.
            chunk: Whether to chunk documents first.
            filter_junk: Remove low-quality chunks.

        Returns:
            Number of documents/chunks indexed.
        """
        if not self._initialised:
            await self.initialize(progress=progress)

        def _p(msg: str, pct: float = 0.0):
            if progress:
                progress(msg, pct)

        # Chunk
        if chunk:
            _p(f"Chunking {len(documents)} documents ...", 0.1)
            chunks = self._chunker.chunk_documents(
                documents,
                strategy=self._chunk_strategy,
                filter_junk=filter_junk,
            )
        else:
            chunks = documents

        # Deduplicate
        before = len(chunks)
        chunks = self._dedup.deduplicate_chunks(chunks)
        removed = before - len(chunks)
        if removed:
            _p(f"Removed {removed} duplicate chunks", 0.2)

        if not chunks:
            _p("No chunks to index", 0.0)
            return 0

        _p(f"Indexing {len(chunks)} chunks ...", 0.25)

        # Index via searcher
        n = self._searcher.index_documents(chunks, progress=_p)

        # Save embedding cache for persistence
        if self._embeddings.is_loaded and self._searcher._doc_embeddings is not None:
            cache_path = self.storage_dir / f"{self.collection}_embeddings.npy"
            self._embeddings.save_embeddings(self._searcher._doc_embeddings, cache_path)
            # Save document metadata alongside
            meta_path = self.storage_dir / f"{self.collection}_docs.json"
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            meta_path.write_text(
                json.dumps(
                    [{"text": d["text"][:500], **{k: v for k, v in d.items() if k != "text"}} for d in chunks],
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

        # Clear cache on re-index
        if self._cache:
            self._cache.clear()

        _p(f"Indexed {n} chunks", 1.0)
        return n

    async def index_text(
        self,
        text: str,
        *,
        url: str = "",
        title: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        chunk: bool = True,
    ) -> int:
        """Convenience: index a single block of text."""
        return await self.build_index(
            [{"text": text, "url": url, "title": title, "metadata": metadata or {}}],
            chunk=chunk,
        )

    # ----- Search ------------------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        use_reranking: bool = True,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Hybrid search: Dense + BM25 → RRF → Rerank.

        Args:
            query: Natural language or code query.
            top_k: Number of results.
            use_reranking: Enable cross-encoder reranking.
            min_score: Minimum score threshold.
            filters: Metadata filters.

        Returns:
            List of :class:`SearchResult` sorted by relevance.
        """
        if not self._initialised:
            await self.initialize()

        if not self._searcher or self._searcher.doc_count == 0:
            return []

        # Check cache
        if self._cache:
            cached = self._cache.get(query)
            if cached is not None:
                restored: List[SearchResult] = []
                for r in cached:
                    if isinstance(r, dict):
                        # to_dict() flattens metadata into the dict —
                        # extract known fields and put the rest back into metadata.
                        meta = {k: v for k, v in r.items() if k not in ("text", "score", "index")}
                        restored.append(
                            SearchResult(
                                text=r["text"],
                                score=r.get("score", 0.0),
                                index=r.get("index", 0),
                                metadata=meta,
                            )
                        )
                    else:
                        restored.append(r)
                return restored

        results = self._searcher.search(
            query,
            top_k=top_k,
            use_reranking=use_reranking,
            min_score=min_score,
            filters=filters,
        )

        # Populate cache
        if self._cache and results:
            self._cache.set(query, [r.to_dict() for r in results])

        return results

    async def search_text(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Convenience: search and return plain dicts."""
        results = await self.search(query, top_k=top_k)
        return [r.to_dict() for r in results]

    # ----- Context Formatting -----------------------------------------------

    def format_context(
        self,
        results: List[SearchResult],
        *,
        max_tokens: int = 3000,
        include_scores: bool = True,
    ) -> str:
        """Format search results as context for an LLM prompt.

        Args:
            results: Search results from :meth:`search`.
            max_tokens: Approximate max tokens (chars / 4).
            include_scores: Include relevance scores.

        Returns:
            Formatted context string.
        """
        parts: List[str] = []
        budget = max_tokens * 4  # rough char estimate

        for i, r in enumerate(results, 1):
            header = f"[Source {i}]"
            if r.url:
                header += f" ({r.url})"
            if include_scores:
                header += f" [score: {r.score:.3f}]"

            entry = f"{header}\n{r.text}"
            if sum(len(p) for p in parts) + len(entry) > budget:
                break
            parts.append(entry)

        return "\n\n".join(parts)

    # ----- Stats & Info ------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return engine status info."""
        return {
            "initialised": self._initialised,
            "backend": self._backend,
            "collection": self.collection,
            "embedding_model": self._embeddings.model_type if self._embeddings.is_loaded else "none",
            "embedding_dim": self._embeddings.dimension,
            "reranker": self._reranker.model_name if self._reranker.is_loaded else "none",
            "doc_count": self.doc_count,
            "bm25_indexed": self._bm25.indexed,
            "cache_size": self._cache.size if self._cache else 0,
            "dedup_seen": self._dedup.seen_count,
        }

    # ----- Sync helpers (for Streamlit / non-async code) --------------------

    def sync_initialize(self, progress=None) -> bool:
        """Sync wrapper for initialize()."""
        return self._run_sync(self.initialize(progress=progress))

    def sync_build_index(self, documents, **kwargs) -> int:
        """Sync wrapper for build_index()."""
        return self._run_sync(self.build_index(documents, **kwargs))

    def sync_search(self, query, **kwargs) -> List[SearchResult]:
        """Sync wrapper for search()."""
        return self._run_sync(self.search(query, **kwargs))

    @staticmethod
    def _run_sync(coro):
        """Run a coroutine synchronously, handling nested event loops."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            return asyncio.run(coro)
