"""
rag_pipeline.py - RAG implementation with FAISS + SQLite + Advanced Deduplication

Features:
- Exact hash deduplication (SHA256)
- Semantic near-duplicate detection via FAISS (checks against existing index)
- Junk chunk filtering (entropy, length, blacklist)
- Thread-safe operations
- Hybrid search with RRF fusion
"""
import time
import hashlib
import logging
import threading
from pathlib import Path
from typing import List, Dict, Generator, Optional, Set, FrozenSet
from collections import Counter
from math import log2

logger = logging.getLogger(__name__)

# Core dependencies
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    logger.warning("[RAG] sentence-transformers or faiss-cpu not installed")

# Optional: BM25 for hybrid search
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

from .rag_db import RAGDatabase


# =============================================================================
# Configuration Constants
# =============================================================================
class DedupeConfig:
    """Deduplication configuration - adjust per use case."""
    SIMILARITY_THRESHOLD: float = 0.95  # Cosine similarity for near-duplicates
    MIN_CHUNK_LENGTH: int = 50          # Skip chunks shorter than this
    MIN_ENTROPY: float = 1.5            # Skip low-entropy (repetitive) text
    MAX_ENTROPY: float = 6.0            # Skip high-entropy (garbage/encoded) text
    BLACKLIST_KEYWORDS: FrozenSet[str] = frozenset({
        'advertisement', 'sponsored', 'cookie policy', 'privacy policy',
        'subscribe now', 'sign up for', 'click here to'
    })


class LocalRAG:
    """
    Local RAG system with FAISS vector search, SQLite persistence,
    and advanced deduplication.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_dir: Optional[Path] = None):
        if not DEPS_AVAILABLE:
            raise ImportError("Install: pip install sentence-transformers faiss-cpu")
        
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        self.index: Optional[faiss.IndexFlatIP] = None  # Inner product for cosine sim
        self.chunks: List[Dict] = []  # In-memory cache for fast retrieval
        self.chunk_hashes: Set[str] = set()  # Fast hash lookup
        
        self.cache_dir = cache_dir or Path(".")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Connect to SQLite
        db_path = self.cache_dir / "rag.db"
        self.db = RAGDatabase(db_path)
        
        self.bm25 = None
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Load state from DB
        self._load_from_db()

    # =========================================================================
    # State Management
    # =========================================================================
    
    def _load_from_db(self):
        """Restore index from DB."""
        with self._lock:
            load_start = time.time()
            self.chunks = self.db.get_all_chunks()
            self.chunk_hashes = {
                hashlib.sha256(c.get('text', '').encode()).hexdigest() 
                for c in self.chunks
            }
            
            if self.chunks:
                logger.info(f"[RAG] Restoring {len(self.chunks)} chunks from DB...")
                self._rebuild_faiss()
                self._rebuild_bm25()
                dur = time.time() - load_start
                logger.info(f"[RAG] State restored in {dur:.2f}s")

    def _rebuild_faiss(self):
        """Rebuild FAISS index from self.chunks vectors using cosine similarity."""
        if not self.chunks:
            self.index = None
            return
        
        # Extract and validate vectors
        vectors = []
        for c in self.chunks:
            v = c.get('vector')
            if v is not None and hasattr(v, 'size') and v.size > 0:
                vectors.append(v)
        
        if not vectors:
            self.index = None
            return
        
        # Stack and normalize for cosine similarity
        embeddings = np.vstack(vectors).astype('float32')
        faiss.normalize_L2(embeddings)
        
        # Use Inner Product index (with normalized vectors = cosine similarity)
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)
        logger.info(f"[RAG] FAISS Index rebuilt: {self.index.ntotal} vectors (cosine sim)")

    def _rebuild_bm25(self):
        """Rebuild BM25 index for keyword search."""
        if BM25_AVAILABLE and self.chunks:
            texts = [c.get("text", "") for c in self.chunks]
            tokenized_texts = [text.lower().split() for text in texts]
            self.bm25 = BM25Okapi(tokenized_texts)

    # =========================================================================
    # Junk Detection
    # =========================================================================
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text (measures randomness)."""
        if not text:
            return 0.0
        freq = Counter(text.lower())
        total = len(text)
        return -sum((count/total) * log2(count/total) for count in freq.values())

    def _is_junk_chunk(self, text: str) -> bool:
        """
        Detect junk chunks that shouldn't be indexed.
        Returns True if chunk should be skipped.
        """
        # Length check
        if len(text.strip()) < DedupeConfig.MIN_CHUNK_LENGTH:
            return True
        
        # Entropy check (too low = repetitive, too high = garbage)
        entropy = self._calculate_entropy(text)
        if entropy < DedupeConfig.MIN_ENTROPY or entropy > DedupeConfig.MAX_ENTROPY:
            return True
        
        # Blacklist keyword check
        text_lower = text.lower()
        for keyword in DedupeConfig.BLACKLIST_KEYWORDS:
            if keyword in text_lower:
                return True
        
        return False

    # =========================================================================
    # Deduplication
    # =========================================================================
    
    def _is_exact_duplicate(self, text: str) -> bool:
        """Check if text is an exact duplicate via SHA256 hash."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return text_hash in self.chunk_hashes

    def _find_near_duplicate(self, embedding: np.ndarray, threshold: Optional[float] = None) -> Optional[int]:
        """
        Check if embedding is a near-duplicate of existing chunks.
        Returns index of similar chunk if found, None otherwise.
        
        Uses existing FAISS index for O(log n) lookup.
        """
        threshold = threshold or DedupeConfig.SIMILARITY_THRESHOLD
        
        if self.index is None or self.index.ntotal == 0:
            return None
        
        # Normalize query vector for cosine similarity
        query = embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query)
        
        # Search for nearest neighbor
        similarities, indices = self.index.search(query, 1)
        
        if indices[0][0] >= 0 and similarities[0][0] > threshold:
            return int(indices[0][0])
        
        return None

    # =========================================================================
    # Document Processing
    # =========================================================================
    
    def chunk_documents(self, documents: List[Dict], chunk_size: int = 500, 
                       overlap: int = 50, filter_junk: bool = True) -> List[Dict]:
        """
        Split documents into chunks with optional junk filtering.
        
        Args:
            documents: List of dicts with 'content', 'url', 'title' keys
            chunk_size: Max characters per chunk
            overlap: Character overlap between chunks
            filter_junk: Whether to filter out junk chunks
            
        Returns:
            List of chunk dicts
        """
        chunks = []
        filtered_count = 0
        
        for doc in documents:
            content = doc.get("content", "")
            if not content:
                continue
            
            url = doc.get("url")
            title = doc.get("title")
            
            start = 0
            chunk_idx = 0
            while start < len(content):
                end = start + chunk_size
                chunk_text = content[start:end]
                
                # Junk filter
                if filter_junk and self._is_junk_chunk(chunk_text):
                    filtered_count += 1
                    start = end - overlap if overlap < chunk_size else end
                    continue
                
                if len(chunk_text.strip()) > 20:
                    chunks.append({
                        "url": url,
                        "title": title,
                        "text": chunk_text,
                        "chunk_index": chunk_idx
                    })
                    chunk_idx += 1
                
                start = end - overlap if overlap < chunk_size else end
        
        if filtered_count > 0:
            logger.info(f"[RAG] Filtered {filtered_count} junk chunks during chunking")
        
        return chunks

    def build_index(self, documents: List[Dict], dedup_threshold: Optional[float] = None, 
                    filter_junk: bool = True):
        """
        Build/update index with new documents.
        Includes document-level and chunk-level deduplication.
        
        Args:
            documents: List of dicts with 'content', 'url', 'title' keys
            dedup_threshold: Cosine similarity threshold for near-duplicate detection
            filter_junk: Whether to filter out junk chunks (disable for testing)
        """
        with self._lock:
            start_time = time.time()
            threshold = dedup_threshold or DedupeConfig.SIMILARITY_THRESHOLD
            
            # Stats
            docs_processed = 0
            docs_skipped = 0
            chunks_added = 0
            chunks_exact_dup = 0
            chunks_near_dup = 0
            
            BATCH_SIZE = 64
            
            for doc in documents:
                content = doc.get('content', '')
                if not content:
                    continue
                
                # Document-level deduplication (SHA256)
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                if self.db.document_exists(content_hash):
                    docs_skipped += 1
                    continue
                
                # Add document to DB
                doc_id = self.db.add_document(
                    doc.get('url', ''), 
                    doc.get('title', 'Untitled'), 
                    content
                )
                
                # Chunk the document
                doc_chunks = self.chunk_documents([doc], filter_junk=filter_junk)
                
                if not doc_chunks:
                    continue
                
                # Process chunks in batches for efficient embedding
                for batch_start in range(0, len(doc_chunks), BATCH_SIZE):
                    batch = doc_chunks[batch_start:batch_start + BATCH_SIZE]
                    texts = [c['text'] for c in batch]
                    
                    # Batch embed
                    embeddings = self.model.encode(
                        texts, 
                        convert_to_numpy=True, 
                        show_progress_bar=False,
                        normalize_embeddings=True  # Pre-normalize for cosine sim
                    )
                    
                    # Process each chunk with deduplication
                    chunks_to_add = []
                    for chunk, embedding in zip(batch, embeddings):
                        text = chunk['text']
                        
                        # Exact duplicate check (O(1) hash lookup)
                        text_hash = hashlib.sha256(text.encode()).hexdigest()
                        if text_hash in self.chunk_hashes:
                            chunks_exact_dup += 1
                            continue
                        
                        # Near-duplicate check against EXISTING index (O(log n))
                        near_dup_idx = self._find_near_duplicate(embedding, threshold)
                        if near_dup_idx is not None:
                            chunks_near_dup += 1
                            logger.debug(f"[RAG] Near-dup skipped (sim > {threshold})")
                            continue
                        
                        # Prepare chunk for storage
                        chunk['doc_id'] = doc_id
                        chunk['vector'] = embedding
                        chunk['hash'] = text_hash
                        chunks_to_add.append(chunk)
                        
                        # Update in-memory structures immediately for subsequent dedup checks
                        self.chunk_hashes.add(text_hash)
                        
                        # Add to FAISS index immediately for near-dup checks in this batch
                        if self.index is None:
                            self.index = faiss.IndexFlatIP(self.embedding_dim)
                        
                        vec = embedding.reshape(1, -1).astype('float32')
                        # Already normalized from encode()
                        self.index.add(vec)
                        self.chunks.append(chunk)
                    
                    # Batch insert to DB
                    if chunks_to_add:
                        self.db.add_chunks(chunks_to_add)
                        chunks_added += len(chunks_to_add)
                
                docs_processed += 1
            
            # Rebuild BM25 (needs full rebuild for efficiency)
            self._rebuild_bm25()
            
            total_time = time.time() - start_time
            
            logger.info(
                f"[RAG] Ingest complete in {total_time:.2f}s: "
                f"{docs_processed} docs processed, {docs_skipped} skipped, "
                f"{chunks_added} chunks added, "
                f"{chunks_exact_dup} exact dups, {chunks_near_dup} near dups filtered"
            )

    def add_chunks(self, chunks: List[Dict], dedup_threshold: Optional[float] = None):
        """
        Add pre-chunked content with deduplication.
        For when you have chunks already (e.g., from external source).
        
        Args:
            chunks: List of dicts with 'text', 'url', 'title' keys
            dedup_threshold: Cosine similarity threshold for near-duplicate detection
        """
        with self._lock:
            threshold = dedup_threshold or DedupeConfig.SIMILARITY_THRESHOLD
            
            # Filter and prepare
            valid_chunks = [c for c in chunks if not self._is_junk_chunk(c.get('text', ''))]
            
            if not valid_chunks:
                logger.info("[RAG] No valid chunks to add after junk filtering")
                return
            
            # Batch embed
            texts = [c['text'] for c in valid_chunks]
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=len(texts) > 100,
                normalize_embeddings=True
            )
            
            # Deduplicate and add
            added = 0
            exact_dup = 0
            near_dup = 0
            chunks_to_persist = []
            
            for chunk, embedding in zip(valid_chunks, embeddings):
                text = chunk['text']
                text_hash = hashlib.sha256(text.encode()).hexdigest()
                
                # Exact duplicate
                if text_hash in self.chunk_hashes:
                    exact_dup += 1
                    continue
                
                # Near duplicate
                if self._find_near_duplicate(embedding, threshold) is not None:
                    near_dup += 1
                    continue
                
                # Add
                chunk['vector'] = embedding
                chunk['hash'] = text_hash
                chunk['doc_id'] = 0  # No parent document
                
                self.chunk_hashes.add(text_hash)
                self.chunks.append(chunk)
                chunks_to_persist.append(chunk)
                
                if self.index is None:
                    self.index = faiss.IndexFlatIP(self.embedding_dim)
                self.index.add(embedding.reshape(1, -1).astype('float32'))
                
                added += 1
            
            # Persist to DB
            if chunks_to_persist:
                self.db.add_chunks(chunks_to_persist)
            
            self._rebuild_bm25()
            
            logger.info(
                f"[RAG] Added {added} chunks, "
                f"skipped {exact_dup} exact dups, {near_dup} near dups"
            )

    # =========================================================================
    # Search
    # =========================================================================
    
    def search(self, query: str, k: int = 5) -> List[Dict]:
        """
        Semantic search using FAISS.
        
        Returns chunks with 'score' field (cosine similarity, 0-1).
        """
        if not self.index or not self.chunks:
            return []
        
        # Encode and normalize query
        query_vec = self.model.encode(
            [query], 
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype('float32')
        
        # Search (inner product on normalized vectors = cosine similarity)
        k = min(k, len(self.chunks))
        similarities, indices = self.index.search(query_vec, k)
        
        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            if 0 <= idx < len(self.chunks):
                chunk = self.chunks[idx].copy()
                # Similarity is already in [0, 1] range for normalized vectors
                chunk['score'] = float(max(0, min(1, sim)))
                results.append(chunk)
        
        return results

    def hybrid_search(self, query: str, k: int = 5, alpha: float = 0.5) -> List[Dict]:
        """
        Hybrid search combining semantic (FAISS) and keyword (BM25) with RRF fusion.
        
        Args:
            query: Search query
            k: Number of results to return
            alpha: Weight for semantic vs keyword (0=keyword only, 1=semantic only)
            
        Returns:
            List of chunks with 'fusion_score' field
        """
        if not self.index or not self.chunks:
            return []
        
        k_search = min(k * 3, len(self.chunks))
        
        # 1. Semantic search rankings
        query_vec = self.model.encode(
            [query],
            convert_to_numpy=True, 
            normalize_embeddings=True
        ).astype('float32')
        
        _, f_indices = self.index.search(query_vec, k_search)
        f_ranks = {
            int(idx): rank + 1 
            for rank, idx in enumerate(f_indices[0]) 
            if 0 <= idx < len(self.chunks)
        }
        
        # 2. Keyword search rankings (BM25)
        b_ranks = {}
        if self.bm25:
            scores = self.bm25.get_scores(query.lower().split())
            top_indices = np.argsort(scores)[::-1][:k_search]
            b_ranks = {int(idx): rank + 1 for rank, idx in enumerate(top_indices)}
        
        # 3. Reciprocal Rank Fusion
        K_RRF = 60  # Standard RRF constant
        fusion_scores = {}
        all_indices = set(f_ranks.keys()) | set(b_ranks.keys())
        
        for idx in all_indices:
            score = 0.0
            if idx in f_ranks:
                score += alpha * (1.0 / (K_RRF + f_ranks[idx]))
            if idx in b_ranks:
                score += (1.0 - alpha) * (1.0 / (K_RRF + b_ranks[idx]))
            fusion_scores[idx] = score
        
        # Sort by fusion score
        sorted_indices = sorted(fusion_scores.keys(), key=lambda x: fusion_scores[x], reverse=True)[:k]
        
        results = []
        for idx in sorted_indices:
            chunk = self.chunks[idx].copy()
            chunk['fusion_score'] = fusion_scores[idx]
            results.append(chunk)
        
        return results

    # =========================================================================
    # Persistence
    # =========================================================================
    
    def save(self, path: Optional[Path] = None):
        """No-op - SQLite auto-saves. Kept for API compatibility."""
        pass
    
    def load(self, path: Optional[Path] = None):
        """Reload state from database."""
        self._load_from_db()
        return True
    
    def get_stats(self) -> Dict:
        """Get current index statistics."""
        return {
            "total_chunks": len(self.chunks),
            "unique_hashes": len(self.chunk_hashes),
            "index_vectors": self.index.ntotal if self.index else 0,
            "model": self.model_name,
            "embedding_dim": self.embedding_dim,
            "bm25_available": self.bm25 is not None
        }


# =============================================================================
# Response Generation
# =============================================================================

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
    
    Args:
        query: User's question
        rag: LocalRAG instance
        llm_backend: LLM backend with send_message() method
        use_hybrid: Use hybrid search (semantic + keyword) if True
        k: Number of context chunks to retrieve
        alpha: Hybrid search weight (higher = more semantic)
        
    Yields:
        Response chunks as strings
    """
    # Retrieve context
    if use_hybrid and rag.bm25:
        context_chunks = rag.hybrid_search(query, k=k, alpha=alpha)
    else:
        context_chunks = rag.search(query, k=k)
    
    if not context_chunks:
        yield "I don't have enough information in my knowledge base to answer that question."
        return
    
    # Build context and sources
    context_parts = []
    source_lines = []
    
    for i, chunk in enumerate(context_chunks, 1):
        title = chunk.get('title', 'Unknown')
        text = chunk.get('text', '')
        url = chunk.get('url', 'N/A')
        
        context_parts.append(f"[{i}] Source: {title}\n{text}")
        source_lines.append(f"[{i}] {title} - {url}")
    
    context_text = "\n\n".join(context_parts)
    
    # Build prompt
    prompt = (
        f"Using the following sources, answer the question. "
        f"Cite sources using [1], [2], etc.\n\n"
        f"{context_text}\n\n"
        f"Question: {query}"
    )
    
    # Stream response
    for chunk in llm_backend.send_message(prompt):
        yield chunk
    
    # Append sources
    yield "\n\n**Sources:**\n" + "\n".join(source_lines[:k])
