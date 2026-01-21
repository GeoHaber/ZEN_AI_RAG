"""
rag_pipeline.py - RAG implementation with FAISS + SQLite + Parallel Batching
"""
import time
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Generator

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

class LocalRAG:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_dir: Path = None):
        if not DEPS_AVAILABLE:
            raise ImportError("Install: pip install sentence-transformers faiss-cpu")
        
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.chunks = [] # In-memory cache for fast retrieval & FAISS mapping
        self.cache_dir = cache_dir or Path(".")
        
        # Connect to SQLite
        db_path = self.cache_dir / "rag.db"
        self.db = RAGDatabase(db_path)
        
        self.bm25 = None
        
        # Load state from DB
        self._load_from_db()

    def _load_from_db(self):
        """Restore index from DB."""
        load_start = time.time()
        self.chunks = self.db.get_all_chunks()
        if self.chunks:
            logger.info(f"[RAG] Restoring {len(self.chunks)} chunks from DB...")
            self._rebuild_faiss()
            self._rebuild_bm25()
            dur = time.time() - load_start
            logger.info(f"[RAG] State restored in {dur:.2f}s")

    def _rebuild_faiss(self):
        """Rebuild FAISS index from self.chunks vectors."""
        if not self.chunks: return
        
        # Extract vectors with checking
        vectors = []
        valid_indices = []
        for i, c in enumerate(self.chunks):
            v = c.get('vector')
            if v is not None and v.size > 0:
                vectors.append(v)
                valid_indices.append(i)
                
        if not vectors: return
        
        # Stack
        embeddings = np.vstack(vectors)
        dimension = embeddings.shape[1]
        
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))
        logger.info(f"[RAG] FAISS Index rebuilt: {self.index.ntotal} vectors")

    def _rebuild_bm25(self):
        if BM25_AVAILABLE and self.chunks:
            texts = [c.get("text", "") for c in self.chunks]
            # Simple tokenization
            tokenized_texts = [text.lower().split() for text in texts]
            self.bm25 = BM25Okapi(tokenized_texts)

    def chunk_documents(self, documents: List[Dict], chunk_size: int = 500, overlap: int = 50) -> List[Dict]:
        """Split documents into chunks."""
        chunks = []
        for doc in documents:
            content = doc.get("content", "")
            if not content: continue
            
            start = 0
            while start < len(content):
                end = start + chunk_size
                chunk_text = content[start:end]
                if len(chunk_text) > 20: 
                    chunks.append({
                        "url": doc.get("url"),
                        "title": doc.get("title"),
                        "text": chunk_text,
                        "chunk_index": len(chunks)
                    })
                start = end - overlap
                if overlap >= chunk_size: start = end
        return chunks
    
    def build_index(self, documents: list):
        """Build/Update index with new documents (Parallel Batching)."""
        start_time = time.time()
        
        # 1. Processing & Deduplication
        BATCH_SIZE = 32
        new_chunks_accumulated = []
        docs_processed = 0
        skipped = 0
        
        for doc in documents:
            content = doc.get('content', '')
            if not content: continue

            # Check Duplicates via Hash
            content_hash = hashlib.md5(content.encode()).hexdigest()
            if self.db.document_exists(content_hash):
                skipped += 1
                continue
                
            # Add Doc to DB
            doc_id = self.db.add_document(doc.get('url'), doc.get('title'), content)
            
            # Chunk
            doc_chunks = self.chunk_documents([doc])
            for c in doc_chunks:
                c['doc_id'] = doc_id 
            new_chunks_accumulated.extend(doc_chunks)
            docs_processed += 1
            
        logger.info(f"[RAG] Processed {docs_processed} new docs (skipped {skipped}). New chunks: {len(new_chunks_accumulated)}")
        
        if not new_chunks_accumulated:
            logger.info("[RAG] No new content to ingest.")
            return

        # 2. Batched Embedding
        total_chunks = len(new_chunks_accumulated)
        embed_start = time.time()
        BATCH_SIZE = 64 # Increased for throughput
        
        # Process in batches
        for i in range(0, total_chunks, BATCH_SIZE):
            batch_start = time.time()
            batch = new_chunks_accumulated[i : i + BATCH_SIZE]
            texts = [c['text'] for c in batch]
            
            # Embed (Parallelized by SentenceTransformer/Torch internal/MKL)
            embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            
            # Assign vectors & Insert
            for j, vec in enumerate(embeddings):
                batch[j]['vector'] = vec
            
            # Bulk Insert into DB (One transaction per batch)
            self.db.add_chunks(batch)
            
            # Add to memory cache
            self.chunks.extend(batch)
            
            batch_dur = time.time() - batch_start
            if total_chunks > BATCH_SIZE:
                logger.debug(f"[RAG] Batch {i//BATCH_SIZE + 1} ({len(batch)} chunks) took {batch_dur:.2f}s")
            
        embed_time = time.time() - embed_start
        logger.info(f"[RAG] Embedded & Stored {total_chunks} chunks in {embed_time:.2f}s")
            
        # 3. Update Search Indices
        self._rebuild_faiss()
        self._rebuild_bm25()
        
        total_time = time.time() - start_time
        logger.info(f"[RAG] Ingest Complete: {total_time:.2f}s")

    def search(self, query: str, k: int = 3) -> List[Dict]:
        """FAISS Search."""
        if not self.index or not self.chunks: return []
        
        query_vec = self.model.encode([query], convert_to_numpy=True)
        distances, indices = self.index.search(query_vec.astype('float32'), k)
        
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.chunks) and idx >= 0:
                chunk = self.chunks[idx].copy()
                chunk['score'] = 1.0 / (1.0 + float(dist)) if dist >= 0 else 0
                results.append(chunk)
        return results

    def hybrid_search(self, query: str, k: int = 5, alpha: float = 0.5) -> List[Dict]:
        """Hybrid Search (RRF)."""
        if not self.index or not self.chunks: return []
        
        # Semantic Candidates
        k_search = min(k * 3, len(self.chunks))
        sem_res = self.search(query, k=k_search)
        
        # Map Chunk Index -> Rank
        # Since self.chunks is list, and FAISS returns list index,
        # we can use the list index as the stable ID for this session.
        # But wait, `search` returns simplified dict. We need indices.
        # Let's re-run search logic linearly or just use returned results?
        # Actually `sem_res` doesn't have the original index easily unless we add it.
        # Let's assume `search` logic returns copies.
        # Refactor: RRF needs indices?
        # Simpler RRF implementation:
        
        # 1. Semantic Scores
        # Re-calc semantic ranks from scratch to get indices
        q_vec = self.model.encode([query], convert_to_numpy=True)
        _, f_indices = self.index.search(q_vec.astype('float32'), k_search)
        f_ranks = {idx: i+1 for i, idx in enumerate(f_indices[0]) if idx >= 0 and idx < len(self.chunks)}
        
        # 2. Keyword Scores
        b_ranks = {}
        if self.bm25:
             scores = self.bm25.get_scores(query.lower().split())
             top_b = np.argsort(scores)[::-1][:k_search]
             b_ranks = {idx: i+1 for i, idx in enumerate(top_b)}
        
        # 3. Fuse
        fusion = {}
        all_ids = set(f_ranks.keys()) | set(b_ranks.keys())
        k_rrf = 60
        for i in all_ids:
            s = 0
            if i in f_ranks: s += alpha * (1/(k_rrf + f_ranks[i]))
            if i in b_ranks: s += (1-alpha) * (1/(k_rrf + b_ranks[i]))
            fusion[i] = s
            
        sorted_ids = sorted(fusion, key=fusion.get, reverse=True)[:k]
        
        results = []
        for i in sorted_ids:
            chunk = self.chunks[i].copy()
            chunk['fusion_score'] = fusion[i]
            results.append(chunk)
            
        return results

    def save(self, path: Path):
        """No-op (SQLite auto-saves)."""
        pass
    
    def load(self, path: Path):
        """Reload from DB."""
        self._load_from_db()
        return True

def generate_rag_response(query: str, rag: LocalRAG, llm_backend, use_hybrid: bool = True) -> Generator[str, None, None]:
    """Generate response using RAG context."""
    if use_hybrid and rag.bm25:
        context_chunks = rag.hybrid_search(query, k=5, alpha=0.6)
    else:
        context_chunks = rag.search(query, k=5)
    
    if not context_chunks:
        yield "I don't have enough information to answer that question."
        return
    
    source_lines = []
    context_text = ""
    for i, c in enumerate(context_chunks, 1):
        context_text += f"\n[{i}] Source: {c.get('title','?')}\n{c.get('text','?')}\n"
        source_lines.append(f"[{i}] {c.get('title','?')} - {c.get('url','N/A')}")

    prompt = f"Using sources:\n{context_text}\n\nAnswer: {query}\nCite [1], [2]..."
    
    for chunk in llm_backend.send_message(prompt):
        yield chunk
    
    yield "\n\n**Sources:**\n" + "\n".join(source_lines[:3])
