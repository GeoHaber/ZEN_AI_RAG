"""
rag_pipeline.py - RAG implementation with Qdrant + BM25 + Advanced Deduplication

Upgrades (v3.6):
  - 4-tier SmartDeduplicator: hash + boilerplate + structural + semantic
  - 5-factor AdvancedReranker: semantic + position + density + answer-type + source
  - Ingestion conflict queue: HITL for conflicting chunks

Upgrades (v3.7 — Zero-Waste Cache, from TDS article):
  - Tier 1 Answer Cache: cosine ≥0.95 → return cached results (zero LLM cost)
  - Tier 2 Context Cache: cosine ≥0.70 → reuse chunks, skip Qdrant, re-rank only
  - Temporal bypass: "latest"/"current" queries skip all cache
  - Source fingerprinting: SHA-256 validation before serving cached data
  - Collection version tracking: bump on write/delete for staleness detection
  - Context sufficiency: verify cached context covers the new query's intent
"""

import os
import time
import hashlib
import logging
import threading
import re
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
from .chunker import TextChunker, ChunkerConfig
from .profiler import profile_execution
from config_system import config

logger = logging.getLogger(__name__)

# Smart deduplication & conflict detection
try:
    from Core.smart_deduplicator import SmartDeduplicator

    SMART_DEDUP_AVAILABLE = True
except ImportError:
    SmartDeduplicator = None
    SMART_DEDUP_AVAILABLE = False

try:
    from Core.ingestion_conflict_detector import IngestionConflictQueue

    CONFLICT_QUEUE_AVAILABLE = True
except ImportError:
    IngestionConflictQueue = None
    CONFLICT_QUEUE_AVAILABLE = False

# Excel → Qdrant payload keys (single source of truth with content_extractor)
try:
    from content_extractor import EXCEL_ROW_PAYLOAD_KEYS
except ImportError:
    EXCEL_ROW_PAYLOAD_KEYS = (
        "file_id",
        "dataset",
        "sheet",
        "sheet_name",
        "date",
        "entity",
        "category",
        "dept_name",
        "dept_id",
        "beds_real",
        "beds_struct",
        "patients_present",
        "free_beds",
        "source_file",
        "source_sheet",
        "row_index",
        "unit",
    )

try:
    from Core.reranker_advanced import AdvancedReranker

    ADVANCED_RERANKER_AVAILABLE = True
except ImportError:
    AdvancedReranker = None
    ADVANCED_RERANKER_AVAILABLE = False

# Zero-Waste Two-Tier Validation-Aware Cache (article integration)
try:
    from Core.zero_waste_cache import ZeroWasteCache, ZeroWasteCacheAdapter

    ZERO_WASTE_AVAILABLE = True
except ImportError:
    ZeroWasteCache = None
    ZeroWasteCacheAdapter = None
    ZERO_WASTE_AVAILABLE = False

# Core dependencies - LAZY LOADED
# We define placeholders here to avoid NameErrors, actual import happens in init
SentenceTransformer = None
CrossEncoder = None
QdrantClient = None
Distance = None
VectorParams = None
PointStruct = None
Filter = None
FieldCondition = None
MatchValue = None
np = None
DEPS_AVAILABLE = True  # Assume true, check later or wrap in try/except during lazy load


# Optional: BM25 for hybrid search
try:
    from rank_bm25 import BM25Okapi

    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

# Optional: MetricsTracker for performance monitoring
try:
    from Core.metrics_tracker import MetricsTracker

    _metrics = MetricsTracker.get_instance()
    METRICS_AVAILABLE = True
except Exception:
    _metrics = None
    METRICS_AVAILABLE = False


# =============================================================================
# Configuration Constants
# =============================================================================
class DedupeConfig:
    """Deduplication configuration - adjust per use case."""

    SIMILARITY_THRESHOLD: float = 0.90  # Cosine similarity for near-duplicates (Lower = More aggressive dedup)
    # Compatibility aliases for tests
    MIN_ENTROPY: float = ChunkerConfig.MIN_ENTROPY
    MAX_ENTROPY: float = ChunkerConfig.MAX_ENTROPY
    MIN_CHUNK_LENGTH: int = ChunkerConfig.MIN_CHUNK_LENGTH
    BLACKLIST_KEYWORDS: Set[str] = ChunkerConfig.BLACKLIST_KEYWORDS


# =============================================================================
# Semantic Cache
# =============================================================================
class SemanticCache:
    """Multi-tier cache using both exact match and cosine similarity."""

    def __init__(self, model, max_entries: int = 1000, ttl: int = 3600, threshold: float = 0.95):
        self.model = model
        self.max_entries = max_entries
        self.ttl = ttl
        self.threshold = threshold

        # Tier 1: Exact Match (Fastest) O(1)
        # Use simple dict + separate eviction list for Python < 3.7 ordering safety,
        # though modern Python dicts are ordered. We use LRU approximation.
        self._exact_cache = {}  # key -> {results, timestamp}

        # Tier 2: Semantic (Slower but smart) O(N) but N is small (cache size)
        # List of (embedding, normal_query, results, timestamp)
        self._semantic_cache = []

        self._lock = threading.Lock()

    def get(self, query: str, query_vec: Any = None) -> Optional[List[Dict]]:
        """Retrieve results if query matches exact or semantic cache.
        If query_vec is provided, use it for Tier 2 to avoid encoding twice (faster)."""
        with self._lock:
            q_norm = query.strip().lower()
            now = time.time()

            # Tier 1: Exact (no encode)
            if q_norm in self._exact_cache:
                entry = self._exact_cache[q_norm]
                if now - entry["timestamp"] < self.ttl:
                    return entry["results"]
                del self._exact_cache[q_norm]

            if not self._semantic_cache:
                return None
            try:
                if query_vec is None:
                    query_vec = self.model.encode([query], normalize_embeddings=True)[0]
                for i, (emb, _, results, ts) in enumerate(self._semantic_cache):
                    if now - ts > self.ttl:
                        continue
                    score = np.dot(query_vec, emb)
                    if score >= self.threshold:
                        logger.debug(f"[Cache] Semantic Hit ({score:.2f}): '{query}' ~= '{_}'")
                        return results
            except Exception as e:
                logger.warning(f"[Cache] Semantic check failed: {e}")
            return None

    def set(self, query: str, results: List[Dict]):
        """Store results in cache."""
        with self._lock:
            q_norm = query.strip().lower()
            now = time.time()

            # 1. Exact
            self._exact_cache[q_norm] = {"results": results, "timestamp": now}

            # Prune Exact
            if len(self._exact_cache) > self.max_entries:
                # Remove random/oldest (iter is roughly oldest insertion order)
                del self._exact_cache[next(iter(self._exact_cache))]

            # 2. Semantic (Store embedding)
            try:
                q_vec = self.model.encode([query], normalize_embeddings=True)[0]
                self._semantic_cache.append((q_vec, q_norm, results, now))

                # Prune Semantic (Small buffer)
                if len(self._semantic_cache) > (self.max_entries // 5):
                    self._semantic_cache.pop(0)
            except Exception as exc:
                logger.debug("%s", exc)

    def clear(self):
        with self._lock:
            self._exact_cache.clear()
            self._semantic_cache.clear()


class LocalRAG:
    """
    Production-grade RAG system using Qdrant.
    Combines Qdrant's high-performance vector search with BM25 keyword search.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or config.BASE_DIR / "rag_storage"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()

        # Initialize Embedding Model
        self._lazy_load_deps()

        # Prefer local path when set (no HuggingFace hub; local-only)
        embedding_model_path = getattr(config.rag, "embedding_model_path", None)
        if embedding_model_path and Path(embedding_model_path).expanduser().exists():
            model_name = str(Path(embedding_model_path).expanduser().resolve())
            logger.info(f"[RAG] Loading embedding model from local path (no hub): {model_name}")
        else:
            # Resolve model name from config (with HF_HUB_OFFLINE=1 uses cache only)
            profile = config.rag.embedding_model
            model_name = config.embedding_config.MODELS.get(profile)
            if not model_name:
                if "/" in profile or len(profile) > 10:
                    model_name = profile
                else:
                    try:
                        logger.warning(f"[RAG] Unknown profile '{profile}', falling back to 'fast'")
                    except Exception as exc:
                        logger.debug("%s", exc)
                    model_name = config.embedding_config.MODELS["fast"]
            logger.info(f"[RAG] Loading transformer: {model_name}")

        device = "cuda" if config.rag.use_gpu and hasattr(config.rag, "use_gpu") else "cpu"
        try:
            import torch

            if device == "cuda" and not torch.cuda.is_available():
                logger.warning("[RAG] GPU requested but not available. Falling back to CPU.")
                device = "cpu"
            self.model = SentenceTransformer(model_name, device=device)
        except Exception as e:
            logger.error(f"[RAG] Failed to load {model_name}: {e}")
            if embedding_model_path:
                raise e
            fallback = config.embedding_config.fallback_model
            fallback_name = config.embedding_config.MODELS[fallback]
            if model_name != fallback_name:
                logger.info(f"[RAG] Attempting fallback to: {fallback_name}")
                try:
                    self.model = SentenceTransformer(fallback_name, device="cpu")
                except Exception as ex:
                    logger.critical(f"[RAG] Fallback failed: {ex}")
                    raise ex
            else:
                raise e

        # Enable Half Precision on GPU
        if device == "cuda":
            try:
                self.model.half()
                logger.info("[RAG] Enabled FP16 precision for embeddings.")
            except Exception as exc:
                logger.debug("%s", exc)

        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        # Dynamic Collection Name (prevents dimension mismatch crashes)
        self.collection_name = f"zenai_knowledge_{self.embedding_dim}"

        # Initialize Qdrant Client (100% Local) with retry to avoid persistent lock from crashed runs
        self.qdrant = self._open_qdrant_with_retry()
        self._qdrant_is_local = (
            True  # path= storage; payload indexes have no effect. Use server Qdrant for payload indexes.
        )
        if self.qdrant:
            try:
                self._init_collection()
                self.read_only = False
            except Exception as e:
                logger.error(f"[RAG] ❌ Failed to init collection: {e}")
                raise
        else:
            self.read_only = True
            logger.debug("[RAG] Storage unavailable (locked); running in read-only mode.")

        # Standard In-memory buffers for quick lookups and BM25
        self.chunks = []  # Metadata cache for BM25 mapping
        self.chunk_hashes = set()  # For O(1) exact duplicate check
        self.bm25 = None
        self.cross_encoder = None  # Lazy loaded
        self._tokenizer_pattern = re.compile(r"\w+")
        # Romanian diacritics → base Latin for BM25 so "pat" matches "paturi", "secți" matches "sectie"
        self._ro_normalize_table = str.maketrans("ăâîșțĂÂÎȘȚ", "aaistAAIST")

        # Initialize Cache — Zero-Waste two-tier if available, else legacy
        if ZERO_WASTE_AVAILABLE:
            _zw = ZeroWasteCache(
                model=self.model,
                max_entries=1000,
                tier1_ttl=3600,  # 1h for answer cache
                tier2_ttl=7200,  # 2h for context cache
                tier1_threshold=0.95,
                tier2_threshold=0.70,
            )
            self.cache = ZeroWasteCacheAdapter(_zw)
            self._zero_waste = _zw
            logger.info("[RAG] Zero-Waste Cache enabled (2-tier + validation + temporal bypass)")
        else:
            self.cache = SemanticCache(self.model, max_entries=1000, ttl=3600)
            self._zero_waste = None
            logger.info("[RAG] Legacy SemanticCache (upgrade: pip install to enable Zero-Waste)")

        # Loader
        self._load_metadata()

        # Initialize Chunker
        self.chunker = TextChunker()

        # --- Smart Deduplicator (replaces basic hash+cosine) ---
        self.smart_dedup = None
        if SMART_DEDUP_AVAILABLE:
            try:
                self.smart_dedup = SmartDeduplicator(
                    model=self.model,
                    semantic_threshold=DedupeConfig.SIMILARITY_THRESHOLD,
                    conflict_threshold=0.75,
                )
                logger.info("[RAG] SmartDeduplicator enabled (4-tier + conflict detection)")
            except Exception as e:
                logger.warning(f"[RAG] SmartDeduplicator init failed: {e}")

        # --- Ingestion Conflict Queue (HITL) ---
        self.conflict_queue = None
        if CONFLICT_QUEUE_AVAILABLE:
            try:
                self.conflict_queue = IngestionConflictQueue()
                pending = self.conflict_queue.pending_count
                if pending > 0:
                    logger.info(f"[RAG] Conflict queue: {pending} pending conflicts for review")
            except Exception as e:
                logger.warning(f"[RAG] ConflictQueue init failed: {e}")

        # --- Advanced Reranker (replaces CrossEncoder-only reranking) ---
        self.advanced_reranker = None
        if ADVANCED_RERANKER_AVAILABLE:
            try:
                self.advanced_reranker = AdvancedReranker(
                    model=self.model,
                    cross_encoder=self.cross_encoder,
                )
                logger.info("[RAG] AdvancedReranker enabled (5-factor scoring)")
            except Exception as e:
                logger.warning(f"[RAG] AdvancedReranker init failed: {e}")

        # --- COMPATIBILITY SHIM FOR LEGACY TESTS ---
        self.index = self  # Alias for old tests (allows rag.index.ntotal)

        # Initialize Advanced Extractor
        try:
            from .universal_extractor import UniversalExtractor

            self.extractor = UniversalExtractor()
        except ImportError:
            self.extractor = None

    def _lazy_load_deps(self):
        """Lazy load heavy dependencies to prevent startup freeze."""
        global \
            SentenceTransformer, \
            CrossEncoder, \
            QdrantClient, \
            Distance, \
            VectorParams, \
            PointStruct, \
            Filter, \
            FieldCondition, \
            MatchValue, \
            np, \
            DEPS_AVAILABLE

        if SentenceTransformer is not None:
            return

        try:
            logger.info("[RAG] Lazy loading heavy dependencies (SentenceTransformers, Qdrant)...")
            from sentence_transformers import SentenceTransformer, CrossEncoder
            from qdrant_client import QdrantClient
            from qdrant_client.models import (
                Distance,
                VectorParams,
                PointStruct,
                Filter,
                FieldCondition,
                MatchValue,
            )
            import numpy as np

            DEPS_AVAILABLE = True
            logger.info("[RAG] Dependencies loaded.")
        except ImportError as e:
            DEPS_AVAILABLE = False
            logger.warning(f"[RAG] Dependencies missing: {e}")
            raise ImportError(f"RAG dependencies missing: {e}")

    def warmup(self, include_reranker: bool = False):
        """Pre-load embedding model. Reranker is lazy-loaded on first rerank() to speed up startup.

        Args:
            include_reranker: If True, also load cross-encoder (adds ~5-15s). Default False for fast first response.
        """
        try:
            logger.info("[RAG] Warming up models...")
        except Exception as exc:
            logger.debug("%s", exc)

        # 1. Warmup Embedding Model (required for search)
        _ = self.model.encode(["warmup"], normalize_embeddings=True)

        # 2. Cross-Encoder: load only when requested (saves 5-15s on startup); prefer local path
        if include_reranker and self.cross_encoder is None:
            reranker_path = getattr(config.rag, "reranker_model_path", None)
            if reranker_path and Path(reranker_path).expanduser().exists():
                load_name = str(Path(reranker_path).expanduser().resolve())
                logger.info(f"[RAG] Loading reranker from local path (no hub): {load_name}")
            else:
                load_name = getattr(
                    config.rag,
                    "reranker_model",
                    "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
                )
            self.cross_encoder = CrossEncoder(load_name)
            _ = self.cross_encoder.predict([["warmup query", "warmup doc"]])

        logger.info("[RAG] Models warmed up and ready.")

    @property
    def ntotal(self) -> int:
        """Compatibility shim for legacy FAISS tests."""
        try:
            return self.qdrant.get_collection(self.collection_name).points_count
        except Exception:
            return 0

    def close(self):
        """Explicitly close the Qdrant client to release storage locks."""
        try:
            import sys

            if sys.meta_path is None:
                return  # Interpreter is shutting down, let it die

            if hasattr(self, "qdrant"):
                # In newer qdrant-client versions, the client has a close method
                if hasattr(self.qdrant, "close"):
                    self.qdrant.close()
                elif hasattr(self.qdrant, "_client") and hasattr(self.qdrant._client, "close"):
                    self.qdrant._client.close()
                del self.qdrant
        except Exception as exc:
            logger.debug("%s", exc)

    def __del__(self):
        self.close()

    def _open_qdrant_with_retry(self, max_retries: int = 3, retry_delay: float = 1.5):
        """Open Qdrant local storage with retries. Handles stale lock from crashed runs.
        Returns QdrantClient or None if storage stays locked."""
        path_str = str(self.cache_dir)
        for attempt in range(max_retries):
            try:
                return QdrantClient(path=path_str)
            except Exception as e:
                if "already accessed by another instance" not in str(e):
                    raise
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        # Last resort: remove stale .lock and try once more (e.g. previous process crashed)
        lock_file = self.cache_dir / ".lock"
        if lock_file.exists():
            try:
                lock_file.unlink()
                return QdrantClient(path=path_str)
            except Exception as exc:
                logger.debug("%s", exc)
        logger.warning(
            "[RAG] Storage LOCKED by another process; indexing disabled. Close other apps using RAG or restart."
        )
        return None

    def _get_hnsw_ef_search(self) -> Optional[Any]:
        """Return SearchParams(hnsw_ef=128 or 256) for better recall at search time, or None if not supported."""
        try:
            from qdrant_client.models import SearchParams

            _big = os.environ.get("RAG_RAT_QDRANT_HNSW_BIG", "").strip().lower() in (
                "1",
                "true",
                "yes",
            )
            return SearchParams(hnsw_ef=256 if _big else 128)
        except Exception:
            return None

    def _init_collection(self):
        """Initialize Qdrant collection if not exists."""
        try:
            collections = self.qdrant.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if exists:
                # Check for dimension mismatch
                info = self.qdrant.get_collection(self.collection_name)
                current_dim = info.config.params.vectors.size
                if current_dim != self.embedding_dim:
                    logger.warning(
                        f"[RAG] Dimension mismatch (Found {current_dim}, Expected {self.embedding_dim}). Recreating collection..."
                    )
                    self.qdrant.delete_collection(self.collection_name)
                    exists = False
                else:
                    # Payload indexes only take effect with server Qdrant; skip for local (path=) storage
                    if not getattr(self, "_qdrant_is_local", True):
                        try:
                            from qdrant_client.models import PayloadSchemaType

                            for field in (
                                "file_id",
                                "sheet_name",
                                "date",
                                "entity",
                                "category",
                                "url",
                                "scan_root",
                                "doc_type",
                                "domain",
                                "table",
                                "version",
                                "dataset",
                                "sheet",
                                "dept_name",
                            ):
                                try:
                                    self.qdrant.create_payload_index(
                                        collection_name=self.collection_name,
                                        field_name=field,
                                        field_schema=PayloadSchemaType.KEYWORD,
                                    )
                                except Exception:
                                    pass  # index may already exist
                        except Exception as exc:
                            logger.debug("%s", exc)

            if not exists:
                # Generic Qdrant index settings: Cosine, HNSW m=16, ef_construct=128 (256 if big), optional on_disk_payload
                vectors_config = VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE,
                )
                create_kw: dict = {
                    "collection_name": self.collection_name,
                    "vectors_config": vectors_config,
                }
                try:
                    from qdrant_client.models import HnswConfigDiff

                    _hnsw_big = os.environ.get("RAG_RAT_QDRANT_HNSW_BIG", "").strip().lower() in ("1", "true", "yes")
                    create_kw["hnsw_config"] = HnswConfigDiff(
                        m=16,
                        ef_construct=256 if _hnsw_big else 128,
                    )
                except ImportError as exc:
                    logger.debug("%s", exc)
                try:
                    _on_disk = os.environ.get("RAG_RAT_QDRANT_ON_DISK_PAYLOAD", "").strip().lower() in (
                        "1",
                        "true",
                        "yes",
                    )
                    if _on_disk:
                        create_kw["on_disk_payload"] = True
                except Exception as exc:
                    logger.debug("%s", exc)
                self.qdrant.create_collection(**create_kw)
                logger.info(
                    f"[RAG] Created Qdrant collection: {self.collection_name} (Cosine, HNSW m=16, ef_construct=128/256)"
                )
                # Payload indexes (high value): file_id, sheet_name, date, entity, category + existing. Server Qdrant only.
                if not getattr(self, "_qdrant_is_local", True):
                    try:
                        from qdrant_client.models import PayloadSchemaType

                        payload_index_fields = (
                            "file_id",
                            "sheet_name",
                            "date",
                            "entity",
                            "category",
                            "url",
                            "scan_root",
                            "doc_type",
                            "domain",
                            "table",
                            "version",
                            "dataset",
                            "sheet",
                            "dept_name",
                        )
                        for field in payload_index_fields:
                            try:
                                self.qdrant.create_payload_index(
                                    collection_name=self.collection_name,
                                    field_name=field,
                                    field_schema=PayloadSchemaType.KEYWORD,
                                )
                            except Exception as exc:
                                logger.debug("%s", exc)
                        logger.info(
                            "[RAG] Payload indexes created (server Qdrant): file_id, sheet_name, date, entity, category, ..."
                        )
                    except Exception as idx_err:
                        logger.debug("[RAG] Payload index creation skipped: %s", idx_err)
                else:
                    logger.debug(
                        "[RAG] Payload indexes skipped (local Qdrant). Use server Qdrant if you need payload indexes."
                    )
        except Exception as e:
            logger.error(f"[RAG] Qdrant init failed: {e}")

    def _load_metadata(self):
        """Load all metadata from Qdrant (paginated) to populate hash and BM25 buffers.
        Ensures search can detect all documents from the loaded vector DB.
        """
        if not self.qdrant:
            logger.warning("[RAG] Storage locked: Metadata secondary buffers will be empty.")
            return

        try:
            self.chunks = []
            self.chunk_hashes = set()
            offset = None
            batch_size = 2000
            while True:
                points, offset = self.qdrant.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                if not points:
                    break
                for p in points:
                    payload = p.payload or {}
                    text = payload.get("text", "")
                    text_hash = hashlib.sha256(text.encode()).hexdigest()
                    chunk = {
                        "text": text,
                        "url": payload.get("url"),
                        "title": payload.get("title"),
                        "scan_root": payload.get("scan_root"),
                        "hash": text_hash,
                        "qdrant_id": p.id,
                    }
                    if payload.get("is_table"):
                        chunk["is_table"] = True
                        if payload.get("sheet_name") is not None:
                            chunk["sheet_name"] = payload.get("sheet_name")
                        if payload.get("columns") is not None:
                            chunk["columns"] = payload.get("columns")
                    for key in (
                        "file_id",
                        "dataset",
                        "sheet",
                        "sheet_name",
                        "date",
                        "entity",
                        "category",
                        "dept_name",
                        "dept_id",
                        "beds_real",
                        "beds_struct",
                        "patients_present",
                        "free_beds",
                        "source_file",
                        "source_sheet",
                        "row_index",
                        "unit",
                    ):
                        if key in payload:
                            chunk[key] = payload[key]
                    self.chunks.append(chunk)
                    self.chunk_hashes.add(text_hash)
                if offset is None:
                    break
            if self.chunks:
                if not self._load_bm25_from_disk():
                    self._rebuild_bm25()
                logger.info(f"[RAG] Loaded {len(self.chunks)} chunks into search buffers (all from vector DB)")
        except Exception as e:
            logger.warning(f"[RAG] Metadata load failed: {e}")

    def _tokenize(self, text: str) -> List[str]:
        """Tokenizer for BM25: lowercase + normalize Romanian diacritics so semantic/key matching works across wording."""
        if not text:
            return []
        lower = text.lower()
        normalized = lower.translate(self._ro_normalize_table)
        return self._tokenizer_pattern.findall(normalized)

    def _rebuild_bm25(self):
        """Rebuild BM25 index for keyword search."""
        if not BM25_AVAILABLE or not self.chunks:
            return

        try:
            tokenized_corpus = [self._tokenize(c["text"]) for c in self.chunks]
            self.bm25 = BM25Okapi(tokenized_corpus)
            logger.debug(f"[RAG] BM25 Index rebuilt with {len(self.chunks)} items")
            try:
                self._save_bm25()
            except Exception as save_err:
                logger.debug(f"[RAG] BM25 save skipped: {save_err}")
        except Exception as e:
            logger.error(f"[RAG] BM25 rebuild failed: {e}")

    def _save_bm25(self):
        """Persist BM25 index + fingerprint to disk to avoid full rebuild on every restart."""
        import pickle

        bm25_path = self.cache_dir / "bm25_index.pkl"
        fp_path = self.cache_dir / "bm25_fingerprint.txt"
        fingerprint = hashlib.sha256("".join(sorted(c.get("hash", "") for c in self.chunks)).encode()).hexdigest()
        with open(bm25_path, "wb") as f:
            pickle.dump(self.bm25, f, protocol=4)
        fp_path.write_text(fingerprint, encoding="utf-8")
        logger.debug(f"[RAG] BM25 index persisted ({len(self.chunks)} docs, fp={fingerprint[:8]})")

    def _load_bm25_from_disk(self) -> bool:
        """Load BM25 from disk if fingerprint matches current chunk hashes. Returns True if loaded."""
        import pickle

        bm25_path = self.cache_dir / "bm25_index.pkl"
        fp_path = self.cache_dir / "bm25_fingerprint.txt"
        if not bm25_path.exists() or not fp_path.exists():
            return False
        try:
            current_fp = hashlib.sha256("".join(sorted(c.get("hash", "") for c in self.chunks)).encode()).hexdigest()
            saved_fp = fp_path.read_text(encoding="utf-8").strip()
            if current_fp != saved_fp:
                logger.debug("[RAG] BM25 fingerprint mismatch — rebuilding from scratch.")
                return False
            with open(bm25_path, "rb") as f:
                self.bm25 = pickle.load(f)
            logger.info(f"[RAG] BM25 loaded from disk ({len(self.chunks)} docs). Startup time saved!")
            return True
        except Exception as e:
            logger.warning(f"[RAG] BM25 disk load failed ({e}), falling back to rebuild.")
            return False

    def _calculate_entropy(self, text: str) -> float:
        """Compatibility delegator for tests."""
        return self.chunker._calculate_entropy(text)

    def _is_junk_chunk(self, text: str) -> bool:
        """Detect junk chunks using unified chunker."""
        return self.chunker.is_junk(text)

    def _find_near_duplicate(self, embedding: "np.ndarray", threshold: float) -> bool:
        """Check Qdrant for semantic near-duplicates."""
        try:
            results = self.qdrant.query_points(
                collection_name=self.collection_name,
                query=embedding.tolist(),
                limit=1,
                score_threshold=threshold,
            ).points
            return len(results) > 0
        except Exception:
            return False

    def chunk_documents(
        self,
        documents: List[Dict],
        chunk_size: int = 500,
        overlap: int = 50,
        filter_junk: bool = True,
    ) -> List[Dict]:
        """Split documents into chunks. Excel sheets (is_table) are kept as one chunk per sheet (vector table)."""
        all_chunks = []
        self.chunker.config.CHUNK_SIZE = chunk_size
        self.chunker.config.CHUNK_OVERLAP = overlap

        for doc in documents:
            content = doc.get("content", "")
            if not content or not content.strip():
                continue

            base_meta = {
                "url": doc.get("url"),
                "title": doc.get("title"),
                "scan_root": doc.get("scan_root"),
                "is_table": doc.get("is_table"),
                "sheet_name": doc.get("sheet_name"),
                "columns": doc.get("columns"),
            }

            # Excel row-level: one chunk per row (one Qdrant point per row). Payload: dataset, sheet, date, dept_name, beds_*, etc.
            if doc.get("excel_row") or doc.get("is_table"):
                text = content.strip()
                if not text:
                    continue
                chunk_meta = {
                    "url": base_meta["url"],
                    "title": base_meta["title"],
                    "scan_root": base_meta["scan_root"],
                    "is_table": True,
                    "sheet_name": base_meta.get("sheet_name"),
                    "columns": base_meta.get("columns"),
                    "text": text,  # no truncation — full row text for accurate counts
                    "chunk_index": doc.get("row_index", 0),
                }
                if doc.get("excel_row"):
                    chunk_meta["excel_row"] = True
                    for key in EXCEL_ROW_PAYLOAD_KEYS:
                        if key in doc:
                            chunk_meta[key] = doc[key]
                else:
                    # Use high limit so table content is not truncated (accurate counts)
                    max_table_chars = getattr(config.rag, "rag_table_max_chars", 80_000)
                    if max_table_chars and len(text) > max_table_chars:
                        chunk_meta["text"] = text[:max_table_chars] + "\n\n[... truncated ...]"
                all_chunks.append(chunk_meta)
                continue

            meta = {k: v for k, v in base_meta.items() if k in ("url", "title", "scan_root")}
            doc_chunks = self.chunker.chunk_document(
                content,
                metadata=meta,
                strategy=config.rag.chunk_strategy,
                filter_junk=filter_junk,
                model=self.model,
            )
            for c in doc_chunks:
                chunk_text = c.text.strip()
                if not self.chunker.is_junk(chunk_text):
                    all_chunks.append(
                        {
                            "url": c.metadata.get("url"),
                            "title": c.metadata.get("title"),
                            "scan_root": c.metadata.get("scan_root"),
                            "text": chunk_text,
                            "chunk_index": c.chunk_index,
                        }
                    )
        return all_chunks

    @staticmethod
    def _url_under_scan_root(url: str, scan_root: Optional[str]) -> bool:
        """True if url is under scan_root (filesystem paths only); always True for URLs or missing root."""
        if not scan_root or not url or url.startswith("http") or scan_root.startswith("http"):
            return True
        try:
            u = Path(url).resolve()
            r = Path(scan_root).resolve()
            return u == r or r in u.parents
        except (OSError, ValueError):
            return False

    @profile_execution("RAG Indexing")
    def build_index(
        self,
        documents: List[Dict],
        dedup_threshold: Optional[float] = None,
        filter_junk: bool = True,
    ):
        """Build/update Qdrant index with new documents.

        Uses SmartDeduplicator (4-tier) when available, otherwise falls back
        to the original hash + cosine dedup. Conflicts detected during
        ingestion are queued for Human-in-the-Loop review.
        Only indexes docs whose url is under scan_root.
        """
        if not self.qdrant:
            logger.warning("[RAG] Skipping indexing: Storage is LOCKED or not initialized.")
            return

        # Ensure collection exists (e.g. after clear_vector_index() it was deleted)
        self._init_collection()

        with self._lock:
            # Invalidate search cache on index update
            self.cache.clear()

            start_time = time.time()
            threshold = dedup_threshold or DedupeConfig.SIMILARITY_THRESHOLD

            docs_processed = 0
            chunks_added = 0
            total_chunks_from_docs = 0
            skipped_hash = 0
            skipped_near_dup = 0
            skipped_boilerplate = 0
            conflicts_found = 0
            import uuid

            # Reset smart dedup per ingestion session
            use_smart = self.smart_dedup is not None
            if use_smart:
                self.smart_dedup.clear()
                # Pre-warm hash cache with existing chunks
                for ch in self.chunks:
                    self.smart_dedup._hash_cache.add(ch.get("hash", ""))

            for doc in documents:
                # Enforce: only index documents under the provided scan root (avoid indexing beyond UI path)
                if not self._url_under_scan_root(doc.get("url", ""), doc.get("scan_root")):
                    logger.warning(
                        "[RAG] Skipping doc outside scan root: url=%s scan_root=%s",
                        doc.get("url"),
                        doc.get("scan_root"),
                    )
                    continue
                doc_chunks = self.chunk_documents([doc], filter_junk=filter_junk)
                if not doc_chunks:
                    continue
                total_chunks_from_docs += len(doc_chunks)
                docs_processed += 1

                BATCH_SIZE = 32
                for i in range(0, len(doc_chunks), BATCH_SIZE):
                    batch = doc_chunks[i : i + BATCH_SIZE]
                    texts = [c["text"] for c in batch]
                    embeddings = self.model.encode(texts, normalize_embeddings=True)

                    points = []
                    for chunk, embedding in zip(batch, embeddings):
                        text = chunk["text"]
                        text_hash = hashlib.sha256(text.encode()).hexdigest()

                        # Excel/table row chunks: only exact-hash dedup (no semantic/conflict)
                        # so we keep all distinct rows and avoid mass conflict queueing
                        is_table_row = chunk.get("excel_row") or chunk.get("row_index") is not None
                        if is_table_row:
                            if text_hash in self.chunk_hashes:
                                skipped_hash += 1
                                continue
                        # ── Smart Dedup (4-tier + conflict detection) for non-table chunks ────
                        elif use_smart:
                            result = self.smart_dedup.should_skip_chunk(
                                text=text,
                                embedding=embedding,
                                source_url=chunk.get("url"),
                                title=chunk.get("title"),
                            )
                            if result.should_skip:
                                reason = result.reason
                                if reason == "exact_duplicate":
                                    skipped_hash += 1
                                elif reason in (
                                    "boilerplate",
                                    "structural",
                                    "repetitive",
                                ):
                                    skipped_boilerplate += 1
                                else:
                                    skipped_near_dup += 1
                                continue

                            # Queue conflict for HITL review (chunk is still added)
                            if result.conflict and self.conflict_queue:
                                self.conflict_queue.add(result.conflict)
                                conflicts_found += 1
                        else:
                            # ── Legacy dedup (hash + cosine) ────────────
                            if text_hash in self.chunk_hashes:
                                skipped_hash += 1
                                continue

                            if self._find_near_duplicate(embedding, threshold):
                                skipped_near_dup += 1
                                continue

                        # ── Add to Qdrant ────────────────────────────────
                        unique_seed = text_hash + str(uuid.uuid4())
                        point_id = int(hashlib.md5(unique_seed.encode()).hexdigest()[:16], 16)

                        payload = {
                            "text": text,
                            "url": chunk.get("url"),
                            "title": chunk.get("title"),
                            "scan_root": chunk.get("scan_root"),
                        }
                        # Parent-Child hierarchical chunking: store parent context for LLM
                        if chunk.get("parent_text"):
                            payload["parent_text"] = chunk["parent_text"]
                        if chunk.get("parent_id"):
                            payload["parent_id"] = chunk["parent_id"]
                        if chunk.get("is_table"):
                            payload["is_table"] = True
                            if chunk.get("sheet_name") is not None:
                                payload["sheet_name"] = chunk.get("sheet_name")
                            if chunk.get("columns") is not None:
                                payload["columns"] = chunk.get("columns")
                        if chunk.get("excel_row"):
                            for key in EXCEL_ROW_PAYLOAD_KEYS:
                                if key in chunk:
                                    payload[key] = chunk[key]
                        points.append(
                            PointStruct(
                                id=point_id,
                                vector=embedding.tolist(),
                                payload=payload,
                            )
                        )

                        self.chunk_hashes.add(text_hash)
                        self.chunks.append(
                            {
                                "text": text,
                                "url": chunk.get("url"),
                                "title": chunk.get("title"),
                                "scan_root": chunk.get("scan_root"),
                                "hash": text_hash,
                                "qdrant_id": point_id,
                                **(
                                    {
                                        k: chunk[k]
                                        for k in ("is_table", "sheet_name", "columns")
                                        if chunk.get(k) is not None
                                    }
                                ),
                                **({k: chunk[k] for k in EXCEL_ROW_PAYLOAD_KEYS if chunk.get(k) is not None}),
                            }
                        )

                    if points:
                        self.qdrant.upsert(collection_name=self.collection_name, points=points)
                        chunks_added += len(points)

            self._rebuild_bm25()
            total_time = time.time() - start_time

            # Bump cache version for staleness detection (Zero-Waste)
            if chunks_added > 0 and hasattr(self.cache, "bump_version"):
                self.cache.bump_version()

            # ── Logging ──────────────────────────────────────────────────
            logger.info(f"[RAG] Ingested {chunks_added} chunks to Qdrant in {total_time:.2f}s")
            if use_smart:
                stats = self.smart_dedup.get_stats()
                logger.info(
                    f"[RAG] Dedup stats: {stats.get('kept', 0)} kept, "
                    f"{stats.get('exact_duplicates', 0)} exact-dup, "
                    f"{stats.get('boilerplate', 0)} boilerplate, "
                    f"{stats.get('structural', 0)} structural, "
                    f"{stats.get('semantic_duplicates', 0)} semantic-dup, "
                    f"{stats.get('conflicts_detected', 0)} conflicts queued"
                )

            if conflicts_found > 0 and self.conflict_queue:
                logger.info(
                    f"[RAG] ⚠ {conflicts_found} potential conflicts detected. Review in Settings → Conflict Resolution."
                )

            if chunks_added == 0 and documents:
                logger.warning(
                    "[RAG] Ingested 0 chunks: %d doc(s) → %d chunk(s) from chunker; "
                    "skipped %d exact-dup, %d boilerplate/structural, %d near-dup. "
                    "If re-indexing same content, this is normal.",
                    len(documents),
                    total_chunks_from_docs,
                    skipped_hash,
                    skipped_boilerplate,
                    skipped_near_dup,
                )

    def add_chunks(self, chunks: List[Dict], dedup_threshold: Optional[float] = None):
        """Add pre-chunked content with deduplication."""
        if not self.qdrant:
            logger.warning("[RAG] Skipping chunk addition: Storage is LOCKED or not initialized.")
            return

        with self._lock:
            threshold = dedup_threshold or DedupeConfig.SIMILARITY_THRESHOLD

            points = []
            import uuid

            for chunk in chunks:
                text = chunk.get("text", "")
                if not text:
                    continue

                if self._is_junk_chunk(text):
                    continue

                text_hash = hashlib.sha256(text.encode()).hexdigest()
                if text_hash in self.chunk_hashes:
                    continue

                embedding = self.model.encode([text], normalize_embeddings=True)[0]
                if self._find_near_duplicate(embedding, threshold):
                    continue

                unique_seed = text_hash + str(uuid.uuid4())
                point_id = int(hashlib.md5(unique_seed.encode()).hexdigest()[:16], 16)

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding.tolist(),
                        payload={
                            "text": text,
                            "url": chunk.get("url"),
                            "title": chunk.get("title"),
                            "scan_root": chunk.get("scan_root"),
                        },
                    )
                )

                self.chunk_hashes.add(text_hash)
                self.chunks.append(
                    {
                        "text": text,
                        "url": chunk.get("url"),
                        "title": chunk.get("title"),
                        "scan_root": chunk.get("scan_root"),
                        "hash": text_hash,
                        "qdrant_id": point_id,
                    }
                )

    # ─── Chunk Validator for Zero-Waste Cache ─────────────────────────────
    def _make_chunk_validator(self):
        """Create a validate_fn callback for the Zero-Waste cache.

        The callback accepts a CacheFingerprint and re-fetches the source
        chunks from Qdrant (using stored URLs) to compare SHA-256 hashes.
        If even one hash has changed, the entry is stale → return False.

        This is the *surgical* validation from Article Scenarios 4-6:
        instead of invalidating the whole cache on any write, we only
        invalidate the specific entries whose source data has changed.
        """
        if not self.qdrant or not ZERO_WASTE_AVAILABLE:
            return None  # No Qdrant → can't validate; fall back to version-only

        def _validate(fingerprint) -> bool:
            try:
                # If no source URLs recorded, fall back to version check only
                if not fingerprint.source_urls:
                    return fingerprint.collection_version >= getattr(self._zero_waste, "_collection_version", 0)

                # Re-fetch current texts for just the URLs in this fingerprint
                from qdrant_client import models

                for url in fingerprint.source_urls:
                    current_points, _ = self.qdrant.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="url",
                                    match=models.MatchValue(value=url),
                                )
                            ]
                        ),
                        limit=200,
                        with_payload=True,
                        with_vectors=False,
                    )
                    if not current_points:
                        # URL has been deleted → stale
                        return False

                    # Build current hashes and compare against cached
                    current_hashes = set(
                        hashlib.sha256(p.payload.get("text", "").encode()).hexdigest()[:16] for p in current_points
                    )
                    cached_hashes = set(fingerprint.chunk_hashes)
                    if not cached_hashes.issubset(current_hashes):
                        return False  # Some cached chunks no longer exist / changed

                return True
            except Exception:
                return False  # On error, treat as stale

        return _validate

    @profile_execution("RAG Semantic Search")
    def search(
        self,
        query: str,
        k: int = 5,
        rerank: bool = True,
        scan_root: Optional[str] = None,
    ) -> List[Dict]:
        """Direct Semantic search with Zero-Waste two-tier caching.

        Flow:
          1. Temporal bypass check ("latest"/"current" → skip all cache)
          2. Tier 1: Answer Cache (≥95% → return cached results, zero cost)
          3. Tier 2: Context Cache (≥70% → reuse chunks, skip Qdrant, re-rank)
          4. Full retrieval: Qdrant → rerank → store in both tiers

        When scan_root is set, bypasses cache and filters results to that root.
        """
        if not self.qdrant:
            if self.bm25:
                logger.debug("[RAG] Qdrant offline, falling back to BM25 for search.")
                return self.hybrid_search(query, k, alpha=0.0, rerank=rerank)
            return []

        use_scan_filter = scan_root and isinstance(scan_root, str) and scan_root.strip()

        # Build surgical validate_fn once per search (avoids recreating per call)
        _validator = self._make_chunk_validator() if not use_scan_filter else None

        # When filtering by scan_root, skip cache so results match current dataset
        if not use_scan_filter:
            # ── Tier 1: Answer Cache (cosine ≥0.95 → instant return) ──────────
            cached = self.cache.get(query, validate_fn=_validator)
            if cached:
                for res in cached:
                    res["_is_cached"] = True
                return cached

            # ── Tier 2: Context Cache (cosine ≥0.70 → reuse chunks) ──────────
            context_from_cache = None
            if hasattr(self.cache, "get_context"):
                context_from_cache = self.cache.get_context(query, validate_fn=_validator)

            if context_from_cache:
                logger.debug(f"[Cache] T2 hit: reusing {len(context_from_cache)} cached chunks")
                results = context_from_cache
                if rerank:
                    results = self.rerank(query, results, top_k=k)
                else:
                    results = results[:k]
                # Store with source from cache (already validated)
                self.cache.set(query, results, source_chunks=context_from_cache)
                return results

        # ── Full Retrieval: Qdrant vector search ─────────────────────────
        limit = min(200, max(k * 10, 50)) if rerank else min(100, max(k * 5, 20))
        query_vec = self.model.encode([query], normalize_embeddings=True)[0].tolist()
        query_kw: Dict[str, Any] = {
            "collection_name": self.collection_name,
            "query": query_vec,
            "limit": limit,
        }
        if use_scan_filter:
            query_kw["query_filter"] = Filter(
                must=[FieldCondition(key="scan_root", match=MatchValue(value=scan_root.strip()))]
            )
        _hnsw_ef = self._get_hnsw_ef_search()
        if _hnsw_ef is not None:
            query_kw["search_params"] = _hnsw_ef
        hits = self.qdrant.query_points(**query_kw).points

        results = []
        for hit in hits:
            p = hit.payload or {}
            r = {
                "text": p.get("text"),
                "url": p.get("url"),
                "title": p.get("title"),
                "score": hit.score,
            }
            # Parent-Child: expose parent_text for richer LLM context
            if p.get("parent_text"):
                r["parent_text"] = p["parent_text"]
            if p.get("parent_id"):
                r["parent_id"] = p["parent_id"]
            if p.get("is_table"):
                r["is_table"] = True
                if p.get("sheet_name") is not None:
                    r["sheet_name"] = p.get("sheet_name")
                if p.get("columns") is not None:
                    r["columns"] = p.get("columns")
            for key in (
                "file_id",
                "dataset",
                "sheet",
                "sheet_name",
                "date",
                "entity",
                "category",
                "dept_name",
                "dept_id",
                "beds_real",
                "beds_struct",
                "patients_present",
                "free_beds",
                "source_file",
                "source_sheet",
                "row_index",
                "unit",
            ):
                if key in p:
                    r[key] = p[key]
            results.append(r)

        # Store raw chunks in Tier 2 (before reranking) for topic reuse
        raw_results = list(results)  # snapshot before reranking mutates order/scores
        if hasattr(self.cache, "set_context") and results:
            self.cache.set_context(query, raw_results)

        # Apply Reranker
        if rerank:
            results = self.rerank(query, results, top_k=k)

        # Store final results in Tier 1 (answer cache), skip when filtering by scan_root
        # Pass raw_results as source_chunks for proper fingerprinting
        if not use_scan_filter:
            self.cache.set(query, results, source_chunks=raw_results)

        return results

    def delete_document_by_url(self, url: str) -> bool:
        """Delete all chunks associated with a specific URL/path.

        Uses surgical cache invalidation when Zero-Waste is available:
        only the cache entries whose source_urls include this URL are evicted,
        instead of nuking the entire cache.
        """
        if not self.qdrant:
            return False

        try:
            # Delete from Qdrant
            # Filter: payload.url == url
            from qdrant_client import models

            self.qdrant.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="url",
                                match=models.MatchValue(value=url),
                            ),
                        ],
                    )
                ),
            )

            # Surgical cache invalidation (only entries referencing this URL)
            with self._lock:
                if hasattr(self.cache, "invalidate_urls"):
                    evicted = self.cache.invalidate_urls({url})
                    logger.debug(f"[RAG] Surgical invalidation: {evicted} cache entries evicted for '{url}'")
                else:
                    self.cache.clear()

                # Bump version for staleness detection
                if hasattr(self.cache, "bump_version"):
                    self.cache.bump_version()
                # We should also rebuild BM25 and chunks
                prev_len = len(self.chunks)
                self.chunks = [c for c in self.chunks if c.get("url") != url]
                new_len = len(self.chunks)

                # Rebuild BM25 immediately to keep it consistent
                self._rebuild_bm25()

            logger.info(f"[RAG] Deleted document: {url} (removed {prev_len - new_len} chunks)")
            return True
        except Exception as e:
            logger.error(f"[RAG] Failed to delete document {url}: {e}")
            return False

    def clear_vector_index(self) -> bool:
        """Delete the entire Qdrant collection and clear in-memory state. Next index will recreate."""
        if not self.qdrant:
            return False
        try:
            self.qdrant.delete_collection(self.collection_name)
            with self._lock:
                self.chunks = []
                self.chunk_hashes = set()
                self.cache.clear()
            logger.info(f"[RAG] Cleared vector index (collection {self.collection_name})")
            return True
        except Exception as e:
            logger.error(f"[RAG] Failed to clear vector index: {e}")
            return False

    @profile_execution("Hybrid Search")
    def hybrid_search(self, query: str, k: int = 5, alpha: float = 0.5, rerank: bool = True) -> List[Dict]:
        if not self.chunks:
            return []

        _t0 = time.time()  # For MetricsTracker latency

        # Build surgical validate_fn for cache lookups
        _validator = self._make_chunk_validator()

        # ── Tier 1: Answer Cache (exact/semantic match → instant return) ──
        cached = self.cache.get(query, validate_fn=_validator) if hasattr(self.cache, "get") else None
        if cached:
            for res in cached:
                res["_is_cached"] = True
            if METRICS_AVAILABLE and _metrics:
                _metrics.record_query(query, time.time() - _t0, cache_tier=1, n_results=len(cached))
            return cached

        # ── Tier 2: Context Cache (skip Qdrant+BM25 if topic matches) ───
        if hasattr(self.cache, "get_context"):
            context_from_cache = self.cache.get_context(query, validate_fn=_validator)
            if context_from_cache:
                logger.debug(f"[Cache] T2 hit in hybrid_search: reusing {len(context_from_cache)} chunks")
                results = context_from_cache
                if rerank:
                    results = self.rerank(query, results, top_k=k)
                else:
                    results = results[:k]
                # Store in T1 with proper source_chunks
                self.cache.set(query, results, source_chunks=context_from_cache)
                if METRICS_AVAILABLE and _metrics:
                    _metrics.record_query(query, time.time() - _t0, cache_tier=2, n_results=len(results))
                return results

        k_search = max(k * 5, 50)  # Retrieve more candidates for RRF/Reranking

        # 1. Semantic Search (Qdrant)
        hits = []
        if self.qdrant:
            query_vec = self.model.encode([query], normalize_embeddings=True)[0].tolist()
            query_kw = {
                "collection_name": self.collection_name,
                "query": query_vec,
                "limit": k_search,
            }
            _hnsw_ef = self._get_hnsw_ef_search()
            if _hnsw_ef is not None:
                query_kw["search_params"] = _hnsw_ef
            hits = self.qdrant.query_points(**query_kw).points
        else:
            logger.debug("[RAG] Qdrant offline, search using BM25 only.")
            alpha = 0.0  # Force BM25 only if Qdrant is missing

        id_to_idx = {c["qdrant_id"]: i for i, c in enumerate(self.chunks)}
        f_ranks = {}
        for rank, hit in enumerate(hits):
            if hit.id in id_to_idx:
                f_ranks[id_to_idx[hit.id]] = rank + 1

        b_ranks = {}
        if self.bm25:
            tokens = self._tokenize(query)
            scores = self.bm25.get_scores(tokens)
            pos_indices = sorted(
                [(i, s) for i, s in enumerate(scores) if s > 0],
                key=lambda x: x[1],
                reverse=True,
            )[:k_search]
            b_ranks = {i: rank + 1 for rank, (i, s) in enumerate(pos_indices)}

        K_RRF = 60
        fusion_scores = {}
        all_indices = set(f_ranks.keys()) | set(b_ranks.keys())
        for idx in all_indices:
            f_score = (1.0 / (K_RRF + f_ranks[idx])) if idx in f_ranks else 0.0
            b_score = (1.0 / (K_RRF + b_ranks[idx])) if idx in b_ranks else 0.0
            fusion_scores[idx] = (alpha * f_score) + ((1.0 - alpha) * b_score)

        # Get Candidates (Top 2 * k or at least 20 for reranking)
        k_candidates = k * 3 if rerank else k
        sorted_indices = sorted(fusion_scores.keys(), key=lambda x: fusion_scores[x], reverse=True)[:k_candidates]
        results = [self.chunks[idx].copy() for idx in sorted_indices]
        for i, res in enumerate(results):
            res["fusion_score"] = fusion_scores[sorted_indices[i]]

        # Store in Tier 2 context cache (raw fused results, before reranking)
        raw_results = list(results)  # snapshot before reranking mutates
        if hasattr(self.cache, "set_context") and results:
            self.cache.set_context(query, raw_results)

        # 2. Reranking (optional)
        if rerank:
            results = self.rerank(query, results, top_k=k)

        # Store final results in Tier 1 (answer cache) with source_chunks
        self.cache.set(query, results, source_chunks=raw_results)

        # Record metrics (full retrieval path — no cache hit)
        if METRICS_AVAILABLE and _metrics:
            _metrics.record_query(query, time.time() - _t0, cache_tier=None, n_results=len(results))

        return results

    def rerank(self, query: str, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        Re-rank retrieved chunks using the AdvancedReranker (5-factor scoring)
        or falling back to the CrossEncoder-only approach.
        """
        if not chunks:
            return []

        # ── Try Advanced 5-Factor Reranker first ─────────────────────────
        if self.advanced_reranker is not None:
            try:
                ranked, scores = self.advanced_reranker.rerank(query, chunks, top_k=top_k)
                if ranked:
                    # Attach score for backward compatibility
                    for chunk, score in zip(ranked, scores):
                        chunk["rerank_score"] = score
                    return ranked
            except Exception as e:
                logger.warning(f"[RAG] AdvancedReranker failed, falling back: {e}")

        # ── Fallback: original CrossEncoder reranking ─────────────────────
        try:
            if self.cross_encoder is None:
                from sentence_transformers import CrossEncoder

                reranker_path = getattr(config.rag, "reranker_model_path", None)
                if reranker_path and Path(reranker_path).expanduser().exists():
                    load_name = str(Path(reranker_path).expanduser().resolve())
                    logger.info(f"[RAG] Loading reranker from local path (no hub): {load_name}")
                else:
                    load_name = getattr(config.rag, "reranker_model", "BAAI/bge-reranker-base")
                device = "cuda" if config.rag.use_gpu and hasattr(config.rag, "use_gpu") else "cpu"
                try:
                    import torch

                    if device == "cuda" and not torch.cuda.is_available():
                        device = "cpu"
                except Exception:
                    device = "cpu"
                self.cross_encoder = CrossEncoder(load_name, device=device)

            # Prepare pairs [query, content]
            pairs = [[query, c["text"]] for c in chunks]
            scores = self.cross_encoder.predict(pairs)

            # Attach scores
            for i, chunk in enumerate(chunks):
                chunk["rerank_score"] = float(scores[i])

            # Sort by new score
            sorted_chunks = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
            return sorted_chunks[:top_k]

        except Exception as e:
            logger.error(f"[RAG] Re-ranking failed: {e}")
            return chunks[:top_k]

    def save(self, path: Optional[Path] = None):
        pass

    def load(self, path: Optional[Path] = None) -> bool:
        """Reload state from database."""
        self._load_metadata()
        return True

    def get_stats(self) -> Dict:
        if not self.qdrant:
            return {"points_count": len(self.chunks), "status": "degraded"}
        try:
            info = self.qdrant.get_collection(self.collection_name)
            return {
                "total_chunks": info.points_count,
                "collection": self.collection_name,
            }
        except Exception:
            return {"error": "Collection not available"}


# =============================================================================
# ASYNC WRAPPERS (Non-Blocking)
# =============================================================================
import asyncio  # noqa: E402


class AsyncLocalRAG(LocalRAG):
    """Async wrapper for LocalRAG to prevent blocking the event loop."""

    async def search_async(self, query: str, k: int = 5) -> List[Dict]:
        return await asyncio.to_thread(self.search, query, k)

    async def hybrid_search_async(self, query: str, k: int = 5, alpha: float = 0.5) -> List[Dict]:
        return await asyncio.to_thread(self.hybrid_search, query, k, alpha)

    async def rerank_async(self, query: str, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
        return await asyncio.to_thread(self.rerank, query, chunks, top_k)

    async def build_index_async(self, documents: List[Dict], dedup_threshold: Optional[float] = None):
        return await asyncio.to_thread(self.build_index, documents, dedup_threshold)

    async def add_chunks_async(self, chunks: List[Dict], dedup_threshold: Optional[float] = None):
        return await asyncio.to_thread(self.add_chunks, chunks, dedup_threshold)


async def generate_rag_response_async(
    query: str,
    rag: LocalRAG,
    llm_backend,
    use_hybrid: bool = True,
    k: int = 5,
    alpha: float = 0.6,
):
    """
    Async generator for RAG response.
    """
    if use_hybrid:
        if hasattr(rag, "hybrid_search_async"):
            candidates = await rag.hybrid_search_async(query, k=k * 3, alpha=alpha)
        else:
            candidates = await asyncio.to_thread(rag.hybrid_search, query, k=k * 3, alpha=alpha)
    else:
        if hasattr(rag, "search_async"):
            candidates = await rag.search_async(query, k=k * 3)
        else:
            candidates = await asyncio.to_thread(rag.search, query, k=k * 3)

    # Apply Re-ranking
    if hasattr(rag, "rerank_async"):
        context_chunks = await rag.rerank_async(query, candidates, top_k=k)
    else:
        context_chunks = await asyncio.to_thread(rag.rerank, query, candidates, top_k=k)

    if not context_chunks:
        yield "I don't have enough information in my knowledge base."
        return

    MAX_CTX_CHARS = 80_000  # high limit so all chunks included for accurate counts
    context_text = ""
    for i, c in enumerate(context_chunks):
        chunk_text = f"Source [{i + 1}]: {c['text']}\n\n"
        if len(context_text) + len(chunk_text) > MAX_CTX_CHARS:
            break
        context_text += chunk_text

    prompt = f"Context:\n{context_text}\n\nQuestion: {query}\n\nAnswer mentioning sources:"

    # LLM backend should ideally differ here or use run_in_executor if it's blocking
    # Assuming send_message is synchronous generator:
    # We can't easily await a sync generator loop, so we iterate in small chunks or use thread
    # But since Python generators are stateful, we'll assume send_message_async exists OR use the sync one carefully.

    # Best practice: The backend usually has send_message_async.
    if hasattr(llm_backend, "send_message_async"):
        async for chunk in llm_backend.send_message_async(prompt):
            yield chunk
    else:
        # Fallback to sync generator in thread (tricky for streaming)
        # Using iterator in thread is hard. For now, we assume backend handles its own sync/async.
        # Actually, looking at async_backend.py, it likely has send_message_stream
        for chunk in llm_backend.send_message(prompt):
            yield chunk
