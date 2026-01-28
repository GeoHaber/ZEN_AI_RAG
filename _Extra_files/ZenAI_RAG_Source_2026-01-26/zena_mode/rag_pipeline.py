"""
rag_pipeline.py - RAG implementation with Qdrant + BM25 + Advanced Deduplication
"""
import time
import hashlib
import logging
import threading
import re
from pathlib import Path
from typing import List, Dict, Generator, Optional, Set, FrozenSet
from collections import Counter
from math import log2
from .chunker import TextChunker, ChunkerConfig

logger = logging.getLogger(__name__)

# Core dependencies
try:
    from sentence_transformers import SentenceTransformer, CrossEncoder
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
    import numpy as np
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    logger.warning("[RAG] sentence-transformers or qdrant-client not installed")

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


class LocalRAG:
    """
    Production-grade RAG system using Qdrant.
    Combines Qdrant's high-performance vector search with BM25 keyword search.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path("./rag_storage")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.collection_name = "zenai_knowledge"
        self._lock = threading.Lock()
        
        # Initialize Embedding Model
        logger.info(f"[RAG] Loading transformer: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        # Initialize Qdrant Client (100% Local)
        self.qdrant = QdrantClient(path=str(self.cache_dir))
        self._init_collection()
        
        # Standard In-memory buffers for quick lookups and BM25
        self.chunks = []         # Metadata cache for BM25 mapping
        self.chunk_hashes = set() # For O(1) exact duplicate check
        self.bm25 = None
        self.cross_encoder = None # Lazy loaded
        self._tokenizer_pattern = re.compile(r'\w+')
        
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
        except:
            return 0

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
        except:
            pass

    def __del__(self):
        self.close()

    def _init_collection(self):
        """Initialize Qdrant collection if not exists."""
        try:
            collections = self.qdrant.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
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

    def close(self):
        """Explicitly close the Qdrant client to release storage locks."""
        try:
            if hasattr(self, 'qdrant'):
                del self.qdrant
        except:
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
        except:
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
            doc_chunks = self.chunker.chunk_document(content, metadata=meta, strategy="recursive", filter_junk=filter_junk)
            
            for c in doc_chunks:
                chunk_text = c.text.strip()
                if len(chunk_text) > 20:
                    all_chunks.append({
                        "url": c.metadata.get("url"),
                        "title": c.metadata.get("title"),
                        "text": chunk_text,
                        "chunk_index": c.chunk_index
                    })
        return all_chunks

    def build_index(self, documents: List[Dict], dedup_threshold: Optional[float] = None, 
                    filter_junk: bool = True):
        """Build/update Qdrant index with new documents."""
        with self._lock:
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
                        
                        point_id = int(hashlib.md5(text_hash.encode()).hexdigest()[:16], 16)
                        
                        points.append(PointStruct(
                            id=point_id,
                            vector=embedding.tolist(),
                            payload={
                                "text": text,
                                "url": chunk.get("url"),
                                "title": chunk.get("title")
                            }
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
                
                point_id = int(hashlib.md5(text_hash.encode()).hexdigest()[:16], 16)
                
                points.append(PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload={
                        "text": text,
                        "url": chunk.get("url"),
                        "title": chunk.get("title")
                    }
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

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """Direct Semantic search using Qdrant."""
        query_vec = self.model.encode([query], normalize_embeddings=True)[0].tolist()
        hits = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=query_vec,
            limit=k
        ).points
        
        return [
            {
                "text": hit.payload.get("text"),
                "url": hit.payload.get("url"),
                "title": hit.payload.get("title"),
                "score": hit.score
            }
            for hit in hits
        ]

    def hybrid_search(self, query: str, k: int = 5, alpha: float = 0.5) -> List[Dict]:
        """Hybrid search combining Qdrant scores with BM25 via RRF."""
        if not self.chunks:
            return []
            
        k_search = max(k * 5, 20)
        query_vec = self.model.encode([query], normalize_embeddings=True)[0].tolist()
        hits = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=query_vec,
            limit=k_search
        ).points
        
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
            
        sorted_indices = sorted(fusion_scores.keys(), key=lambda x: fusion_scores[x], reverse=True)[:k]
        results = [self.chunks[idx].copy() for idx in sorted_indices]
        for i, res in enumerate(results):
            res['fusion_score'] = fusion_scores[sorted_indices[i]]
        return results

    def rerank(self, query: str, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        Re-rank retrieved chunks using a Cross-Encoder for higher precision.
        """
        if not chunks:
            return []
        
        try:
            if self.cross_encoder is None:
                logger.info("[RAG] Loading CrossEncoder for Re-ranking...")
                # Use a fast & effective re-ranker
                self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

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
        try:
            info = self.qdrant.get_collection(self.collection_name)
            return {"total_chunks": info.points_count, "collection": self.collection_name}
        except:
            return {"error": "Collection not available"}


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
    
    context_text = "\n\n".join([f"Source [{i+1}]: {c['text']}" for i, c in enumerate(context_chunks)])
    prompt = f"Context:\n{context_text}\n\nQuestion: {query}\n\nAnswer mentioning sources:"
    
    for chunk in llm_backend.send_message(prompt):
        yield chunk
