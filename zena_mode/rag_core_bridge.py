"""
rag_core_bridge.py — Bridge between ZEN_AI_RAG and the shared rag_core library.

This adapter wraps rag_core components while preserving ZEN_AI_RAG's
Qdrant-based persistent storage, metadata propagation, and rag_db.py
SQLite layer.

It exposes the same interface as ``LocalRAG`` so existing code
can use it as a drop-in replacement.

Pipeline::

    Documents → rag_core.TextChunker → Embed (rag_core) → Dedup (rag_core)
                        ↓                       ↓
                   rag_db.py (SQLite)    Qdrant vector store
                        ↓
    Query → Dense + BM25 (rag_core) → RRF (rag_core) → Rerank (rag_core)
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Generator, List, Optional, Set

from config_system import config

# rag_core components (installed as editable package)
from rag_core.bm25_index import BM25Index
from rag_core.cache import SemanticCache
from rag_core.chunker import ChunkerConfig, TextChunker
from rag_core.dedup import DeduplicationManager
from rag_core.embeddings import EmbeddingManager
from rag_core.fusion import reciprocal_rank_fusion
from rag_core.reranker import RerankerManager

# Local modules
try:
    from .profiler import profile_execution
except ImportError:

    def profile_execution(name):
        def decorator(fn):
            return fn

        return decorator


try:
    from .rag_db import RAGDatabase
except ImportError:
    RAGDatabase = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-loaded Qdrant
# ---------------------------------------------------------------------------
QdrantClient = None
Distance = VectorParams = PointStruct = None


def _lazy_load_qdrant():
    global QdrantClient, Distance, VectorParams, PointStruct
    if QdrantClient is not None:
        return
    from qdrant_client import QdrantClient as _QC
    from qdrant_client.models import Distance as _D, VectorParams as _VP, PointStruct as _PS

    QdrantClient, Distance, VectorParams, PointStruct = _QC, _D, _VP, _PS


# ---------------------------------------------------------------------------
#  LocalRAGv2  (ZEN_AI_RAG edition — with metadata + rag_db)
# ---------------------------------------------------------------------------
class LocalRAGv2:
    """
    Production-grade RAG with **rag_core** algorithms, Qdrant storage,
    metadata propagation, and optional SQLite (rag_db.py) persistence.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or config.BASE_DIR / "rag_storage"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()

        # ── Resolve embedding model from config ──
        profile = config.rag.embedding_model
        model_name = config.embedding_config.MODELS.get(profile)
        if not model_name:
            logger.warning(f"[RAG] Unknown profile '{profile}', falling back to 'fast'")
            model_name = config.embedding_config.MODELS["fast"]

        use_gpu = getattr(config.rag, "use_gpu", False)

        # ── rag_core: Embedding manager ──
        device = "cuda" if use_gpu else "cpu"
        self._embed_mgr = EmbeddingManager(model_name=model_name, prefer_code=False, device=device)
        self._embed_mgr.load()

        self.embedding_dim = self._embed_mgr.dimension
        self.model = self._embed_mgr._model  # SentenceTransformer for compat

        # ── rag_core: BM25 ──
        self._bm25 = BM25Index(code_aware=False)

        # ── rag_core: Reranker ──
        reranker_model = getattr(config.rag, "reranker_model", None)
        self._reranker = RerankerManager(model_name=reranker_model)

        # ── rag_core: Cache ──
        self._cache = SemanticCache(ttl=3600.0, encoder=self._embed_mgr)

        # ── rag_core: Chunker ──
        self.chunker = TextChunker(ChunkerConfig(CHUNK_SIZE=800, CHUNK_OVERLAP=100))

        # ── rag_core: Dedup ──
        self._dedup = DeduplicationManager(similarity_threshold=0.95)

        # ── SQLite layer (ZEN_AI_RAG specific) ──
        self.db: Optional[RAGDatabase] = None
        if RAGDatabase is not None:
            try:
                db_path = self.cache_dir / "rag_documents.db"
                self.db = RAGDatabase(db_path)
                logger.info(f"[RAG] SQLite database: {db_path}")
            except Exception as e:
                logger.warning(f"[RAG] SQLite init failed: {e}")

        # ── Qdrant (persistent) ──
        self.collection_name = f"zenai_knowledge_{self.embedding_dim}"
        _lazy_load_qdrant()
        try:
            self.qdrant = QdrantClient(path=str(self.cache_dir))
            self._init_collection()
            self.read_only = False
        except Exception as e:
            if "already accessed by another instance" in str(e):
                logger.warning("[RAG] Storage LOCKED — running in degraded mode")
                self.qdrant = None
                self.read_only = True
            else:
                raise

        # In-memory buffers
        self.chunks: List[Dict] = []
        self.chunk_hashes: Set[str] = set()

        self._load_metadata()

        self.index = self  # compat shim
        self.cross_encoder = None

        try:
            from .universal_extractor import UniversalExtractor

            self.extractor = UniversalExtractor()
        except ImportError:
            self.extractor = None

    # ---- Qdrant helpers ----------------------------------------------------

    def _init_collection(self):
        try:
            collections = self.qdrant.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if exists:
                info = self.qdrant.get_collection(self.collection_name)
                if info.config.params.vectors.size != self.embedding_dim:
                    logger.warning("[RAG] Dimension mismatch — recreating collection")
                    self.qdrant.delete_collection(self.collection_name)
                    exists = False
            if not exists:
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.embedding_dim, distance=Distance.COSINE),
                )
                logger.info(f"[RAG] Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"[RAG] Qdrant init failed: {e}")

    def _load_metadata(self):
        if not self.qdrant:
            return
        try:
            points, _ = self.qdrant.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False,
            )
            self.chunks = []
            self.chunk_hashes = set()
            for p in points:
                text = p.payload.get("text", "")
                text_hash = hashlib.sha256(text.encode()).hexdigest()
                self.chunks.append(
                    {
                        "text": text,
                        "url": p.payload.get("url"),
                        "title": p.payload.get("title"),
                        "metadata": p.payload.get("metadata", {}),
                        "hash": text_hash,
                        "qdrant_id": p.id,
                    }
                )
                self.chunk_hashes.add(text_hash)
            if self.chunks:
                self._bm25.build([c["text"] for c in self.chunks])
                logger.info(f"[RAG] Loaded {len(self.chunks)} chunks into search buffers")
        except Exception as e:
            logger.warning(f"[RAG] Metadata load failed: {e}")

    # ---- Public API --------------------------------------------------------

    def warmup(self):
        logger.info("[RAG] Warming up models...")
        self._embed_mgr.encode_single("warmup", normalize=True)
        self._reranker.load()
        if self._reranker.is_loaded:
            self._reranker.rerank("warmup", ["warmup doc"], top_k=1)
        logger.info("[RAG] Models warmed up and ready.")

    @property
    def ntotal(self) -> int:
        try:
            return self.qdrant.get_collection(self.collection_name).points_count
        except Exception:
            return 0

    def chunk_documents(
        self, documents: List[Dict], chunk_size: int = 800, overlap: int = 50, filter_junk: bool = True
    ) -> List[Dict]:
        self.chunker.config.CHUNK_SIZE = chunk_size
        self.chunker.config.CHUNK_OVERLAP = overlap
        all_chunks = []
        for doc in documents:
            content = doc.get("content", "")
            if not content or not content.strip():
                continue
            meta = {"url": doc.get("url"), "title": doc.get("title")}
            strategy = getattr(config.rag, "chunk_strategy", "sentence")
            doc_chunks = self.chunker.chunk_document(
                content,
                metadata=meta,
                strategy=strategy,
                filter_junk=filter_junk,
            )
            for c in doc_chunks:
                chunk_text = c.text.strip()
                if len(chunk_text) > 20:
                    all_chunks.append(
                        {
                            "url": c.metadata.get("url"),
                            "title": c.metadata.get("title"),
                            "text": chunk_text,
                            "chunk_index": c.chunk_index,
                            "metadata": doc.get("metadata", {}),  # ZEN: metadata propagation
                        }
                    )
        return all_chunks

    @profile_execution("RAG Indexing")
    def build_index(self, documents: List[Dict], dedup_threshold: Optional[float] = None, filter_junk: bool = True):
        if not self.qdrant:
            logger.warning("[RAG] Skipping indexing: Storage not available")
            return
        with self._lock:
            self._cache.clear()
            start_time = time.time()
            threshold = dedup_threshold or 0.95
            chunks_added = 0

            for doc in documents:
                # Store document in SQLite if available
                doc_id = None
                if self.db:
                    try:
                        doc_id = self.db.add_document(
                            url=doc.get("url", ""),
                            title=doc.get("title", ""),
                            content=doc.get("content", ""),
                        )
                    except Exception as e:
                        logger.warning(f"[RAG] SQLite insert failed: {e}")

                doc_chunks = self.chunk_documents([doc], filter_junk=filter_junk)
                if not doc_chunks:
                    continue
                doc_chunks = self._dedup.deduplicate_chunks(doc_chunks)

                BATCH_SIZE = 32
                for i in range(0, len(doc_chunks), BATCH_SIZE):
                    batch = doc_chunks[i : i + BATCH_SIZE]
                    texts = [c["text"] for c in batch]
                    embeddings = self._embed_mgr.encode(texts, batch_size=BATCH_SIZE)

                    points = []
                    db_chunks = []
                    for chunk, embedding in zip(batch, embeddings):
                        text = chunk["text"]
                        text_hash = hashlib.sha256(text.encode()).hexdigest()
                        if text_hash in self.chunk_hashes:
                            continue
                        # Near-dup via Qdrant
                        try:
                            hits = self.qdrant.query_points(
                                collection_name=self.collection_name,
                                query=embedding.tolist(),
                                limit=1,
                                score_threshold=threshold,
                            ).points
                            if hits:
                                continue
                        except Exception:
                            pass

                        point_id = int(hashlib.md5(text_hash.encode()).hexdigest()[:16], 16)
                        payload = {
                            "text": text,
                            "url": chunk.get("url"),
                            "title": chunk.get("title"),
                            "metadata": chunk.get("metadata", {}),
                        }
                        points.append(PointStruct(id=point_id, vector=embedding.tolist(), payload=payload))

                        self.chunk_hashes.add(text_hash)
                        self.chunks.append(
                            {
                                "text": text,
                                "url": chunk.get("url"),
                                "title": chunk.get("title"),
                                "metadata": chunk.get("metadata", {}),
                                "hash": text_hash,
                                "qdrant_id": point_id,
                            }
                        )

                        # Prepare for SQLite batch insert
                        if self.db and doc_id is not None:
                            db_chunks.append(
                                {
                                    "doc_id": doc_id,
                                    "chunk_index": chunk.get("chunk_index", 0),
                                    "text": text,
                                    "vector": embedding,
                                    "metadata": chunk.get("metadata", {}),
                                }
                            )

                    if points:
                        self.qdrant.upsert(collection_name=self.collection_name, points=points)
                        chunks_added += len(points)

                    # Store chunks in SQLite
                    if db_chunks and self.db:
                        try:
                            self.db.add_chunks(db_chunks)
                        except Exception as e:
                            logger.warning(f"[RAG] SQLite chunk insert failed: {e}")

            if self.chunks:
                self._bm25.build([c["text"] for c in self.chunks])

            elapsed = time.time() - start_time
            logger.info(f"[RAG] Ingested {chunks_added} chunks in {elapsed:.2f}s")

    def add_chunks(self, chunks: List[Dict], dedup_threshold: Optional[float] = None):
        if not self.qdrant:
            return
        with self._lock:
            threshold = dedup_threshold or 0.95
            points = []
            for chunk in chunks:
                text = chunk.get("text", "")
                if not text:
                    continue
                text_hash = hashlib.sha256(text.encode()).hexdigest()
                if text_hash in self.chunk_hashes:
                    continue
                embedding = self._embed_mgr.encode_single(text, normalize=True)
                try:
                    hits = self.qdrant.query_points(
                        collection_name=self.collection_name,
                        query=embedding.tolist(),
                        limit=1,
                        score_threshold=threshold,
                    ).points
                    if hits:
                        continue
                except Exception:
                    pass
                point_id = int(hashlib.md5(text_hash.encode()).hexdigest()[:16], 16)
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding.tolist(),
                        payload={
                            "text": text,
                            "url": chunk.get("url"),
                            "title": chunk.get("title"),
                            "metadata": chunk.get("metadata", {}),
                        },
                    )
                )
                self.chunk_hashes.add(text_hash)
                self.chunks.append(
                    {
                        "text": text,
                        "url": chunk.get("url"),
                        "title": chunk.get("title"),
                        "metadata": chunk.get("metadata", {}),
                        "hash": text_hash,
                        "qdrant_id": point_id,
                    }
                )
            if points:
                self.qdrant.upsert(collection_name=self.collection_name, points=points)
                self._bm25.build([c["text"] for c in self.chunks])
                logger.info(f"[RAG] Added {len(points)} chunks")

    @profile_execution("RAG Semantic Search")
    def search(self, query: str, k: int = 5, rerank: bool = True) -> List[Dict]:
        if not self.qdrant:
            if self._bm25 and self._bm25.indexed:
                return self.hybrid_search(query, k, alpha=0.0, rerank=rerank)
            return []

        cached = self._cache.get(query)
        if cached is not None:
            for r in cached:
                r["_is_cached"] = True
            return cached

        limit = k * 3 if rerank else k
        q_vec = self._embed_mgr.encode_single(query, normalize=True)
        hits = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=q_vec.tolist(),
            limit=limit,
        ).points

        results = [
            {
                "text": h.payload.get("text"),
                "url": h.payload.get("url"),
                "title": h.payload.get("title"),
                "metadata": h.payload.get("metadata", {}),
                "score": h.score,
            }
            for h in hits
        ]

        if rerank:
            results = self.rerank(query, results, top_k=k)

        self._cache.set(query, [r for r in results])
        return results

    def hybrid_search(self, query: str, k: int = 5, alpha: float = 0.5, rerank: bool = True) -> List[Dict]:
        if not self.chunks:
            return []

        k_search = max(k * 5, 50)

        # Stage 1: Dense via Qdrant
        dense_scores: Dict[int, float] = {}
        if self.qdrant:
            q_vec = self._embed_mgr.encode_single(query, normalize=True)
            hits = self.qdrant.query_points(
                collection_name=self.collection_name,
                query=q_vec.tolist(),
                limit=k_search,
            ).points
            id_to_idx = {c["qdrant_id"]: i for i, c in enumerate(self.chunks)}
            for rank, hit in enumerate(hits):
                if hit.id in id_to_idx:
                    dense_scores[id_to_idx[hit.id]] = 1.0 / (60 + rank + 1)
        else:
            alpha = 0.0

        # Stage 2: BM25 via rag_core
        bm25_scores: Dict[int, float] = {}
        if self._bm25 and self._bm25.indexed:
            raw = self._bm25.search(query, k=k_search)
            for rank, (idx, _) in enumerate(sorted(raw.items(), key=lambda x: x[1], reverse=True)):
                bm25_scores[idx] = 1.0 / (60 + rank + 1)

        # Stage 3: RRF Fusion via rag_core
        if dense_scores and bm25_scores:
            fused = reciprocal_rank_fusion(
                dense_scores,
                bm25_scores,
                k=60,
                weights=[alpha, 1.0 - alpha],
            )
        elif dense_scores:
            fused = dense_scores
        elif bm25_scores:
            fused = bm25_scores
        else:
            return []

        k_candidates = k * 3 if rerank else k
        sorted_indices = sorted(fused, key=lambda x: fused[x], reverse=True)[:k_candidates]

        results = [self.chunks[idx].copy() for idx in sorted_indices]
        for i, res in enumerate(results):
            res["fusion_score"] = fused[sorted_indices[i]]

        # Stage 4: Rerank via rag_core
        if rerank:
            results = self.rerank(query, results, top_k=k)
        return results

    def rerank(self, query: str, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
        if not chunks:
            return []
        try:
            if not self._reranker.is_loaded:
                self._reranker.load()
            if not self._reranker.is_loaded:
                return chunks[:top_k]
            texts = [c["text"] for c in chunks]
            reranked = self._reranker.rerank(query, texts, top_k=top_k)
            results = []
            for orig_idx, score in reranked:
                chunk = chunks[orig_idx].copy()
                chunk["rerank_score"] = score
                results.append(chunk)
            return results
        except Exception as e:
            logger.error(f"[RAG] Reranking failed: {e}")
            return chunks[:top_k]

    def save(self, path=None):
        pass

    def load(self, path=None) -> bool:
        self._load_metadata()
        return True

    def get_stats(self) -> Dict:
        stats = {
            "total_chunks": len(self.chunks),
            "collection": self.collection_name,
            "bm25_indexed": self._bm25.indexed,
            "embedding_model": self._embed_mgr.model_type if self._embed_mgr.is_loaded else "none",
            "embedding_dim": self.embedding_dim,
            "reranker": self._reranker.model_name if self._reranker.is_loaded else "not loaded",
            "cache_size": self._cache.size if self._cache else 0,
            "read_only": getattr(self, "read_only", False),
        }
        if self.qdrant:
            try:
                info = self.qdrant.get_collection(self.collection_name)
                stats["qdrant_points"] = info.points_count
            except Exception:
                pass
        if self.db:
            try:
                stats["sqlite_chunks"] = self.db.count_chunks()
            except Exception:
                pass
        return stats

    def close(self):
        try:
            if hasattr(self, "qdrant") and self.qdrant is not None:
                if hasattr(self.qdrant, "close"):
                    self.qdrant.close()
                del self.qdrant
                self.qdrant = None
        except Exception:
            pass
        try:
            if self.db:
                self.db.close()
        except Exception:
            pass

    def __del__(self):
        self.close()


# ── Async wrapper ──────────────────────────────────────────────────────────
import asyncio


class AsyncLocalRAGv2(LocalRAGv2):
    async def search_async(self, query, k=5):
        return await asyncio.to_thread(self.search, query, k)

    async def hybrid_search_async(self, query, k=5, alpha=0.5):
        return await asyncio.to_thread(self.hybrid_search, query, k, alpha)

    async def rerank_async(self, query, chunks, top_k=5):
        return await asyncio.to_thread(self.rerank, query, chunks, top_k)

    async def build_index_async(self, documents, dedup_threshold=None):
        return await asyncio.to_thread(self.build_index, documents, dedup_threshold)

    async def add_chunks_async(self, chunks, dedup_threshold=None):
        return await asyncio.to_thread(self.add_chunks, chunks, dedup_threshold)


# ── Standalone helper ──────────────────────────────────────────────────────


@profile_execution("RAG Retrieval Logic")
def generate_rag_response(
    query: str,
    rag: LocalRAGv2,
    llm_backend,
    use_hybrid: bool = True,
    k: int = 5,
    alpha: float = 0.6,
) -> Generator[str, None, None]:
    if use_hybrid:
        candidates = rag.hybrid_search(query, k=k * 3, alpha=alpha)
    else:
        candidates = rag.search(query, k=k * 3)
    context_chunks = rag.rerank(query, candidates, top_k=k)
    if not context_chunks:
        yield "I don't have enough information in my knowledge base."
        return
    MAX_CTX_CHARS = 12000
    context_text = ""
    for i, c in enumerate(context_chunks):
        chunk_text = f"Source [{i + 1}]: {c['text']}\n\n"
        if len(context_text) + len(chunk_text) > MAX_CTX_CHARS:
            break
        context_text += chunk_text
    prompt = f"Context:\n{context_text}\n\nQuestion: {query}\n\nAnswer mentioning sources:"
    for chunk in llm_backend.send_message(prompt):
        yield chunk
