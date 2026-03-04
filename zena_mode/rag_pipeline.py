"""
rag_pipeline.py - RAG implementation with Qdrant + BM25 + Advanced Deduplication
"""
import time
import hashlib
import logging
import threading
import re
from pathlib import Path
from typing import List, Dict, Generator, Optional, Set
from .chunker import TextChunker, ChunkerConfig
from .profiler import profile_execution
from config_system import config

logger = logging.getLogger(__name__)

# Core dependencies
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
DEPS_AVAILABLE = True # Assume true, check later or wrap in try/except during lazy load


# Optional: BM25 for hybrid search
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False


# =============================================================================
# Configuration Constants
# =============================================================================
class DedupeConfig:
    """Deduplication configuration - adjust per use case."""
    SIMILARITY_THRESHOLD: float = 0.95  # Cosine similarity for near-duplicates
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
        """Initialize instance."""
        self.model = model
        self.max_entries = max_entries
        self.ttl = ttl
        self.threshold = threshold
        
        # Tier 1: Exact Match (Fastest) O(1)
        # Use simple dict + separate eviction list for Python < 3.7 ordering safety, 
        # though modern Python dicts are ordered. We use LRU approximation.
        self._exact_cache = {} # key -> {results, timestamp}
        
        # Tier 2: Semantic (Slower but smart) O(N) but N is small (cache size)
        # List of (embedding, normal_query, results, timestamp)
        self._semantic_cache = [] 
        
        self._lock = threading.Lock()

    def get(self, query: str) -> Optional[List[Dict]]:
        """Retrieve results if query matches exact or semantic cache."""
        with self._lock:
            q_norm = query.strip().lower()
            now = time.time()
            
            # Tier 1: Exact
            if q_norm in self._exact_cache:
                entry = self._exact_cache[q_norm]
                if now - entry['timestamp'] < self.ttl:
                    return entry['results']
                else:
                    del self._exact_cache[q_norm]
            
            # Tier 2: Semantic
            # Generating embedding is costly, so we only do it if semantic cache has items
            if not self._semantic_cache:
                return None
                
            # Embed query
            # Note: self.model is the SentenceTransformer instance
            try:
                q_vec = self.model.encode([query], normalize_embeddings=True)[0]
                
                for i, (emb, _, results, ts) in enumerate(self._semantic_cache):
                    if now - ts > self.ttl: continue
                    
                    # Cosine sim for normalized vectors is just dot product
                    score = np.dot(q_vec, emb)
                    
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
            except Exception: pass
            
    def clear(self):
        with self._lock:
            self._exact_cache.clear()
            self._semantic_cache.clear()


class _LocalRAGBase:
    """Base methods for LocalRAG."""

def _do_do_init___setup_setup(cache_dir):
    """Helper: setup phase for _do_init___setup."""


    self.cache_dir = cache_dir or config.BASE_DIR / "rag_storage"
    self.cache_dir.mkdir(parents=True, exist_ok=True)

    self._lock = threading.Lock()


    # Initialize Embedding Model
    self._lazy_load_deps()

    # Resolve Model Name from Config
    profile = config.rag.embedding_model # e.g. "balanced"
    model_name = config.embedding_config.MODELS.get(profile)
    if not model_name: 
        logger.warning(f"[RAG] Unknown profile '{profile}', falling back to 'fast'")
        model_name = config.embedding_config.MODELS['fast']

    device = "cuda" if config.rag.use_gpu and hasattr(config.rag, "use_gpu") else "cpu"
    # Since torch is lazy loaded, we check availability inside try block

    logger.info(f"[RAG] Loading transformer: {model_name} (Target Device: {device})")

    try:
        # Check for GPU if requested
        import torch
        if device == "cuda" and not torch.cuda.is_available():
            logger.warning("[RAG] GPU requested but not available. Falling back to CPU.")
            device = "cpu"

        self.model = SentenceTransformer(model_name, device=device)
    except Exception as e:
        logger.error(f"[RAG] Failed to load {model_name}: {e}")
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

    return device

    return device


def _do_do_init___setup_init(cache_dir):
    """Helper: setup phase for _do_init___setup."""

    _do_do_init___setup_setup(cache_dir)

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize instance."""
        device = _do_init___setup(cache_dir)
        # Enable Half Precision on GPU
        if device == "cuda":
            try:
                self.model.half()
                logger.info("[RAG] Enabled FP16 precision for embeddings.")
            except Exception: pass

        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        # Dynamic Collection Name (prevents dimension mismatch crashes)
        self.collection_name = f"zenai_knowledge_{self.embedding_dim}"

        # Initialize Qdrant Client (100% Local)
        try:
            self.qdrant = QdrantClient(path=str(self.cache_dir))
            self._init_collection()
            self.read_only = False
        except Exception as e:
            if "already accessed by another instance" in str(e):
                logger.warning(f"[RAG] ⚠️ Storage LOCKED by another process. Running in DEGRADED mode (Metadata only).")
                self.qdrant = None
                self.read_only = True
            else:
                logger.error(f"[RAG] ❌ Failed to initialize Qdrant: {e}")
                raise

        # Standard In-memory buffers for quick lookups and BM25
        self.chunks = []         # Metadata cache for BM25 mapping
        self.chunk_hashes = set() # For O(1) exact duplicate check
        self.bm25 = None
        self.cross_encoder = None # Lazy loaded
        self._tokenizer_pattern = re.compile(r'\w+')


        # Initialize Semantic Cache (New)
        self.cache = SemanticCache(self.model, max_entries=1000, ttl=3600)

        # Loader
        self._load_metadata()

        # Initialize Chunker
        self.chunker = TextChunker()

        # --- COMPATIBILITY SHIM FOR LEGACY TESTS ---
        self.index = self # Alias for old tests (allows rag.index.ntotal)

        # Initialize Advanced Extractor
        try:
            from .universal_extractor import UniversalExtractor
            self.extractor = UniversalExtractor()
        except ImportError:
            self.extractor = None

    def _lazy_load_deps(self):
        """Lazy load heavy dependencies to prevent startup freeze."""
        global SentenceTransformer, CrossEncoder, QdrantClient, Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, np, DEPS_AVAILABLE

        if SentenceTransformer is not None: return

        try:
             logger.info("[RAG] Lazy loading heavy dependencies (SentenceTransformers, Qdrant)...")
             from sentence_transformers import SentenceTransformer, CrossEncoder
             from qdrant_client import QdrantClient
             from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
             import numpy as np
             DEPS_AVAILABLE = True
             logger.info("[RAG] Dependencies loaded.")
        except ImportError as e:
             DEPS_AVAILABLE = False
             logger.warning(f"[RAG] Dependencies missing: {e}")
             raise ImportError(f"RAG dependencies missing: {e}")

    def warmup(self):
        """Pre-load heavy models into memory to avoid first-query lag."""
        logger.info("[RAG] Warming up models...")
        # 1. Warmup Embedding Model
        _ = self.model.encode(["warmup"], normalize_embeddings=True)

        # 2. Warmup Cross-Encoder (New)
        if self.cross_encoder is None:
            self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            _ = self.cross_encoder.predict([["warmup query", "warmup doc"]])

        logger.info("[RAG] Models warmed up and ready.")

    @property
    def ntotal(self) -> int:
        """Compatibility shim for legacy FAISS tests."""
        try:
            return self.qdrant.get_collection(self.collection_name).points_count
        except Exception:
            return 0


def _do_init___setup_part1():
    """Do init   setup part 1."""


    def close(self):
        """Explicitly close the Qdrant client to release storage locks."""
        try:
            if hasattr(self, 'qdrant'):
                del self.qdrant
        except Exception:
            pass

    def _rebuild_bm25(self):
        """Rebuild BM25 index for keyword search."""
        if not BM25_AVAILABLE or not self.chunks:
            return

        try:
            tokenized_corpus = [self._tokenize(c['text']) for c in self.chunks]
            self.bm25 = BM25Okapi(tokenized_corpus)
            logger.debug(f"[RAG] BM25 Index rebuilt with {len(self.chunks)} items")
        except Exception as e:
            logger.error(f"[RAG] BM25 rebuild failed: {e}")


def _do_init___setup(cache_dir):
    """Helper: setup phase for __init__."""
    _do_do_init___setup_init(cache_dir)

    def close(self):
        """Explicitly close the Qdrant client to release storage locks."""
        try:
            if hasattr(self, 'qdrant'):
                # In newer qdrant-client versions, the client has a close method
                if hasattr(self.qdrant, 'close'):
                    self.qdrant.close()
                elif hasattr(self.qdrant, '_client') and hasattr(self.qdrant._client, 'close'):
                    self.qdrant._client.close()
                del self.qdrant
        except Exception:
            pass

    def __del__(self):
        self.close()

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
                    logger.warning(f"[RAG] Dimension mismatch (Found {current_dim}, Expected {self.embedding_dim}). Recreating collection...")
                    self.qdrant.delete_collection(self.collection_name)
                    exists = False
            
            if not exists:
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"[RAG] Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"[RAG] Qdrant init failed: {e}")

    def _load_metadata(self):
        """Load metadata from Qdrant to populate hash and BM25 buffers."""
        if not self.qdrant:
            logger.warning("[RAG] Storage locked: Metadata secondary buffers will be empty.")
            return
            
        try:
            points, _ = self.qdrant.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            
            self.chunks = []
            self.chunk_hashes = set()
            
            for p in points:
                payload = p.payload
                text = payload.get('text', '')
                text_hash = hashlib.sha256(text.encode()).hexdigest()
                
                chunk = {
                    'text': text,
                    'url': payload.get('url'),
                    'title': payload.get('title'),
                    'hash': text_hash,
                    'qdrant_id': p.id
                }
                self.chunks.append(chunk)
                self.chunk_hashes.add(text_hash)
            
            if self.chunks:
                self._rebuild_bm25()
                logger.info(f"[RAG] Loaded {len(self.chunks)} chunks into search buffers")
        except Exception as e:
            logger.warning(f"[RAG] Metadata load failed: {e}")

    def _tokenize(self, text: str) -> List[str]:
        """Standard tokenizer for BM25 and processing."""
        return self._tokenizer_pattern.findall(text.lower())
    _do_init___setup_part1()


class LocalRAG(_LocalRAGBase):
    """
    Production-grade RAG system using Qdrant.
    Combines Qdrant's high-performance vector search with BM25 keyword search.
    """
    

    def _calculate_entropy(self, text: str) -> float:
        """Compatibility delegator for tests."""
        return self.chunker._calculate_entropy(text)

    def _is_junk_chunk(self, text: str) -> bool:
        """Detect junk chunks using unified chunker."""
        return self.chunker.is_junk(text)

    def _find_near_duplicate(self, embedding: 'np.ndarray', threshold: float) -> bool:
        """Check Qdrant for semantic near-duplicates."""
        try:
            results = self.qdrant.query_points(
                collection_name=self.collection_name,
                query=embedding.tolist(),
                limit=1,
                score_threshold=threshold
            ).points
            return len(results) > 0
        except Exception:
            return False

    def chunk_documents(self, documents: List[Dict], chunk_size: int = 500, 
                       overlap: int = 50, filter_junk: bool = True) -> List[Dict]:
        """Split documents into chunks using unified chunker."""
        all_chunks = []
        # Update chunker config if different
        self.chunker.config.CHUNK_SIZE = chunk_size
        self.chunker.config.CHUNK_OVERLAP = overlap

        for doc in documents:
            content = doc.get("content", "")
            if not content or not content.strip(): continue
            
            meta = {"url": doc.get("url"), "title": doc.get("title")}
            doc_chunks = self.chunker.chunk_document(
                content, 
                metadata=meta, 
                strategy=config.rag.chunk_strategy, 
                filter_junk=filter_junk,
                model=self.model
            )
            
            for c in doc_chunks:
                chunk_text = c.text.strip()
                if len(chunk_text) > 20:
                    all_chunks.append({
                        "url": c.metadata.get("url"),
                        "title": c.metadata.get("title"),
                        "text": chunk_text,
                        "chunk_index": c.chunk_index,
                        "metadata": doc.get("metadata", {}) 
                    })
        return all_chunks

    @profile_execution("RAG Indexing")
    def build_index(self, documents: List[Dict], dedup_threshold: Optional[float] = None, 
                    filter_junk: bool = True):
        """Build/update Qdrant index with new documents."""
        if not self.qdrant:
            logger.warning("[RAG] Skipping indexing: Storage is LOCKED or not initialized.")
            return

        with self._lock:
            # Invalidate search cache on index update
            self.cache.clear()
            
            start_time = time.time()
            threshold = dedup_threshold or DedupeConfig.SIMILARITY_THRESHOLD
            
            docs_processed = 0
            chunks_added = 0
            
            for doc in documents:
                doc_chunks = self.chunk_documents([doc], filter_junk=filter_junk)
                if not doc_chunks: continue
                
                BATCH_SIZE = 32
                for i in range(0, len(doc_chunks), BATCH_SIZE):
                    batch = doc_chunks[i:i + BATCH_SIZE]
                    texts = [c['text'] for c in batch]
                    embeddings = self.model.encode(texts, normalize_embeddings=True)
                    
                    points = []
                    for chunk, embedding in zip(batch, embeddings):
                        text = chunk['text']
                        text_hash = hashlib.sha256(text.encode()).hexdigest()
                        
                        if text_hash in self.chunk_hashes:
                            continue
                        
                        if self._find_near_duplicate(embedding, threshold):
                            continue
                        
                        point_id = int(hashlib.sha256(text_hash.encode()).hexdigest()[:16], 16)
                        
                        payload = {
                            "text": text,
                            "url": chunk.get("url"),
                            "title": chunk.get("title"),
                            "metadata": chunk.get("metadata", {})
                        }
                        
                        points.append(PointStruct(
                            id=point_id,
                            vector=embedding.tolist(),
                            payload=payload
                        ))
                        
                        self.chunk_hashes.add(text_hash)
                        self.chunks.append({
                            'text': text,
                            'url': chunk.get("url"),
                            'title': chunk.get("title"),
                            'hash': text_hash,
                            'qdrant_id': point_id
                        })
                    
                    if points:
                        self.qdrant.upsert(
                            collection_name=self.collection_name,
                            points=points
                        )
                        chunks_added += len(points)
                docs_processed += 1
            
            self._rebuild_bm25()
            total_time = time.time() - start_time
            logger.info(f"[RAG] Ingested {chunks_added} chunks to Qdrant in {total_time:.2f}s")

    def add_chunks(self, chunks: List[Dict], dedup_threshold: Optional[float] = None):
        """Add pre-chunked content with deduplication."""
        if not self.qdrant:
            logger.warning("[RAG] Skipping chunk addition: Storage is LOCKED or not initialized.")
            return

        with self._lock:
            threshold = dedup_threshold or DedupeConfig.SIMILARITY_THRESHOLD
            
            points = []
            for chunk in chunks:
                text = chunk.get('text', '')
                if not text: continue
                
                if self._is_junk_chunk(text): continue
                
                text_hash = hashlib.sha256(text.encode()).hexdigest()
                if text_hash in self.chunk_hashes: continue
                
                embedding = self.model.encode([text], normalize_embeddings=True)[0]
                if self._find_near_duplicate(embedding, threshold): continue
                
                point_id = int(hashlib.sha256(text_hash.encode()).hexdigest()[:16], 16)
                
                payload = {
                     "text": text,
                     "url": chunk.get("url"),
                     "title": chunk.get("title"),
                     "metadata": chunk.get("metadata", {})
                }
                
                points.append(PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload=payload
                ))
                
                self.chunk_hashes.add(text_hash)
                self.chunks.append({
                    'text': text,
                    'url': chunk.get("url"),
                    'title': chunk.get("title"),
                    'hash': text_hash,
                    'qdrant_id': point_id
                })
            
            if points:
                self.qdrant.upsert(collection_name=self.collection_name, points=points)
                self._rebuild_bm25()
                logger.info(f"[RAG] Manually added {len(points)} chunks")

    @profile_execution("RAG Semantic Search")
    def search(self, query: str, k: int = 5, rerank: bool = True) -> List[Dict]:
        """Direct Semantic search using Qdrant with result caching and optional reranking."""
        if not self.qdrant:
             # Fallback: If BM25 is available, use it, otherwise return empty
             if self.bm25:
                 logger.debug("[RAG] Qdrant offline, falling back to BM25 for search.")
                 return self.hybrid_search(query, k, alpha=0.0, rerank=rerank)
             return []
             
        # Check Semantic Cache
        cached = self.cache.get(query)
        if cached:
            # Inject cache flag for UI
            for res in cached:
                res['_is_cached'] = True
            return cached

        # Retrieval Limit: Fetch more if reranking is enabled
        limit = k * 3 if rerank else k

        query_vec = self.model.encode([query], normalize_embeddings=True)[0].tolist()
        hits = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=query_vec,
            limit=limit
        ).points
        
        results = [
            {
                "text": hit.payload.get("text"),
                "url": hit.payload.get("url"),
                "title": hit.payload.get("title"),
                "metadata": hit.payload.get("metadata", {}),
                "score": hit.score
            }
            for hit in hits
        ]
        
        # Apply Reranker
        if rerank:
            results = self.rerank(query, results, top_k=k)
        
        # Store in Semantic Cache
        self.cache.set(query, results)
        
        return results

    def hybrid_search(self, query: str, k: int = 5, alpha: float = 0.5, rerank: bool = True) -> List[Dict]:
        """Hybrid search combining Qdrant scores with BM25 via RRF, optionally reranked."""
        if not self.chunks:
            return []
            
        k_search = max(k * 5, 50) # Retrieve more candidates for RRF/Reranking
        
        # 1. Semantic Search (Qdrant)
        hits = []
        if self.qdrant:
            query_vec = self.model.encode([query], normalize_embeddings=True)[0].tolist()
            hits = self.qdrant.query_points(
                collection_name=self.collection_name,
                query=query_vec,
                limit=k_search
            ).points
        else:
            logger.debug("[RAG] Qdrant offline, search using BM25 only.")
            alpha = 0.0 # Force BM25 only if Qdrant is missing
        
        id_to_idx = {c['qdrant_id']: i for i, c in enumerate(self.chunks)}
        f_ranks = {}
        for rank, hit in enumerate(hits):
            if hit.id in id_to_idx:
                f_ranks[id_to_idx[hit.id]] = rank + 1
        
        b_ranks = {}
        if self.bm25:
            tokens = self._tokenize(query)
            scores = self.bm25.get_scores(tokens)
            pos_indices = sorted([(i, s) for i, s in enumerate(scores) if s > 0], key=lambda x: x[1], reverse=True)[:k_search]
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
            res['fusion_score'] = fusion_scores[sorted_indices[i]]
            
        # 2. Reranking (optional)
        if rerank:
            results = self.rerank(query, results, top_k=k)
            
        return results

    def rerank(self, query: str, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        Re-rank retrieved chunks using a Cross-Encoder for higher precision.
        """
        if not chunks:
            return []
        
        try:
            if self.cross_encoder is None:
                from sentence_transformers import CrossEncoder
                model_name = getattr(config.rag, "reranker_model", "BAAI/bge-reranker-base")
                device = "cuda" if config.rag.use_gpu and hasattr(config.rag, "use_gpu") else "cpu"
                
                logger.info(f"[RAG] Loading Reranker: {model_name} (Device: {device})")
                
                # Check GPU availability
                try:
                    import torch
                    if device == "cuda" and not torch.cuda.is_available():
                         device = "cpu"
                except Exception: device = "cpu"

                self.cross_encoder = CrossEncoder(model_name, device=device)

            # Prepare pairs [query, content]
            pairs = [[query, c['text']] for c in chunks]
            scores = self.cross_encoder.predict(pairs)
            
            # Attach scores
            for i, chunk in enumerate(chunks):
                chunk['rerank_score'] = float(scores[i])
            
            # Sort by new score
            sorted_chunks = sorted(chunks, key=lambda x: x['rerank_score'], reverse=True)
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
        """Get stats."""
        if not self.qdrant:
            return {"points_count": len(self.chunks), "status": "degraded"}
        try:
            info = self.qdrant.get_collection(self.collection_name)
            return {"total_chunks": info.points_count, "collection": self.collection_name}
        except Exception:
            return {"error": "Collection not available"}


@profile_execution("RAG Retrieval Logic")
def generate_rag_response(
    query: str, 
    rag: LocalRAG, 
    llm_backend, 
    use_hybrid: bool = True,
    k: int = 5,
    alpha: float = 0.6
) -> Generator[str, None, None]:
    """
    Generate streaming response using RAG context.
    """
    if use_hybrid:
        # Retrieve 3x candidates for re-ranking
        candidates = rag.hybrid_search(query, k=k*3, alpha=alpha)
    else:
        candidates = rag.search(query, k=k*3)
    
    # Apply Re-ranking
    context_chunks = rag.rerank(query, candidates, top_k=k)
    
    if not context_chunks:
        yield "I don't have enough information in my knowledge base."
        return
    
    MAX_CTX_CHARS = 12000 # Approx 3000 tokens
    context_text = ""
    for i, c in enumerate(context_chunks):
        chunk_text = f"Source [{i+1}]: {c['text']}\n\n"
        if len(context_text) + len(chunk_text) > MAX_CTX_CHARS:
            break
        context_text += chunk_text
    
    prompt = (
        f"You are a precise assistant. Use ONLY the following Context to answer the Question.\n"
        f"If the answer is not in the Context, say 'I don't have that information in my sources'.\n"
        f"Do not use outside knowledge.\n\n"
        f"Context:\n{context_text}\n\n"
        f"Question: {query}\n\n"
        f"Answer:"
    )
    
    for chunk in llm_backend.send_message(prompt):
        yield chunk

# =============================================================================
# ASYNC WRAPPERS (Non-Blocking)
# =============================================================================
import asyncio

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
    alpha: float = 0.6
):
    """
    Async generator for RAG response.
    """
    if use_hybrid:
        if hasattr(rag, 'hybrid_search_async'):
             candidates = await rag.hybrid_search_async(query, k=k*3, alpha=alpha)
        else:
             candidates = await asyncio.to_thread(rag.hybrid_search, query, k=k*3, alpha=alpha)
    else:
        if hasattr(rag, 'search_async'):
             candidates = await rag.search_async(query, k=k*3)
        else:
             candidates = await asyncio.to_thread(rag.search, query, k=k*3)
    
    # Apply Re-ranking
    if hasattr(rag, 'rerank_async'):
        context_chunks = await rag.rerank_async(query, candidates, top_k=k)
    else:
        context_chunks = await asyncio.to_thread(rag.rerank, query, candidates, top_k=k)
    
    if not context_chunks:
        yield "I don't have enough information in my knowledge base."
        return
    
    MAX_CTX_CHARS = 12000 
    context_text = ""
    for i, c in enumerate(context_chunks):
        chunk_text = f"Source [{i+1}]: {c['text']}\n\n"
        if len(context_text) + len(chunk_text) > MAX_CTX_CHARS:
            break
        context_text += chunk_text
    
    prompt = f"Context:\n{context_text}\n\nQuestion: {query}\n\nAnswer mentioning sources:"
    
    # LLM backend should ideally differ here or use run_in_executor if it's blocking
    # Assuming send_message is synchronous generator:
    # We can't easily await a sync generator loop, so we iterate in small chunks or use thread
    # But since Python generators are stateful, we'll assume send_message_async exists OR use the sync one carefully.
    
    # Best practice: The backend usually has send_message_async.
    if hasattr(llm_backend, 'send_message_async'):
         async for chunk in llm_backend.send_message_async(prompt):
             yield chunk
    else:
         # Fallback to sync generator in thread (tricky for streaming)
         # Using iterator in thread is hard. For now, we assume backend handles its own sync/async.
         # Actually, looking at async_backend.py, it likely has send_message_stream
         for chunk in llm_backend.send_message(prompt):
             yield chunk
