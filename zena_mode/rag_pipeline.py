"""
rag_pipeline.py - RAG implementation with FAISS vector store + BM25 hybrid search
"""
import json
import pickle
import time
from pathlib import Path
from typing import List, Dict, Tuple, Generator
import logging

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
    logger.info("[RAG] rank_bm25 not installed - hybrid search disabled")


class LocalRAG:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_dir: Path = None):
        if not DEPS_AVAILABLE:
            raise ImportError("Install: pip install sentence-transformers faiss-cpu")
        
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.chunks = []
        self.cache_dir = cache_dir or Path(".")
        self.bm25 = None  # For hybrid search
    
    def chunk_documents(self, documents: List[Dict], chunk_size: int = 500, overlap: int = 50) -> List[Dict]:
        """
        Split documents into overlapping chunks for embedding.
        
        Args:
            documents: List of docs with 'content', 'url', 'title' keys
            chunk_size: Target size of each chunk in characters
            overlap: Number of characters to overlap between chunks (prevents context loss)
        
        Returns:
            List of chunk dictionaries with text and metadata
        """
        chunks = []
        
        for doc in documents:
            content = doc["content"]
            doc_url = doc.get("url", "unknown")
            doc_title = doc.get("title", "Untitled")
            
            # Sliding window with overlap
            start = 0
            while start < len(content):
                end = start + chunk_size
                chunk_text = content[start:end]
                
                # Skip tiny chunks
                if len(chunk_text) > 20:
                    chunks.append({
                        "url": doc_url,
                        "title": doc_title,
                        "chunk_id": len(chunks),
                        "text": chunk_text
                    })
                
                # Move forward, but step back by overlap to create sliding window
                start = end - overlap
                
                # Prevent infinite loop if overlap >= chunk_size
                if overlap >= chunk_size:
                    start = end
        
        logger.info(f"[RAG] Created {len(chunks)} chunks from {len(documents)} documents (overlap: {overlap} chars)")
        return chunks
    
    def build_index(self, documents: list):
        """Build FAISS index and optionally BM25 index from documents."""
        start_time = time.time()
        
        # Chunk documents with overlap
        chunk_start = time.time()
        self.chunks = self.chunk_documents(documents, chunk_size=500, overlap=50)
        chunk_time = time.time() - chunk_start
        logger.info(f"[RAG] ✅ Chunking: {len(self.chunks)} chunks with overlap in {chunk_time:.2f}s")
        
        if not self.chunks:
            logger.warning("[RAG] No chunks to index")
            return
        
        texts = [c["text"] for c in self.chunks]
        
        # Generate embeddings for FAISS
        embed_start = time.time()
        logger.info(f"[RAG] Generating embeddings for {len(texts)} chunks...")
        embeddings = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        embed_time = time.time() - embed_start
        logger.info(f"[RAG] ✅ Embeddings: {len(embeddings)} vectors in {embed_time:.2f}s ({embed_time/len(embeddings)*1000:.1f}ms/chunk)")
        
        # Build FAISS index
        index_start = time.time()
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))
        index_time = time.time() - index_start
        
        # Build BM25 index for hybrid search (if available)
        if BM25_AVAILABLE:
            bm25_start = time.time()
            tokenized_texts = [text.lower().split() for text in texts]
            self.bm25 = BM25Okapi(tokenized_texts)
            bm25_time = time.time() - bm25_start
            logger.info(f"[RAG] ✅ BM25 index built in {bm25_time:.2f}s")
        
        total_time = time.time() - start_time
        logger.info(f"[RAG] ✅ Index built: {self.index.ntotal} vectors in {total_time:.2f}s | {dimension} dimensions")
    
    def search(self, query: str, k: int = 3) -> List[Dict]:
        """Find top-k relevant chunks using FAISS (semantic search)."""
        if not self.index or not self.chunks:
            logger.warning("[RAG] Index not built yet")
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        
        # Search FAISS
        distances, indices = self.index.search(query_embedding.astype('float32'), k)
        
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.chunks):
                chunk = self.chunks[idx].copy()
                chunk['distance'] = float(dist)
                chunk['score'] = 1.0 / (1.0 + float(dist))  # Convert distance to score
                results.append(chunk)
        
        return results
    
    def hybrid_search(self, query: str, k: int = 5, alpha: float = 0.5) -> List[Dict]:
        """
        Hybrid search combining FAISS (semantic) + BM25 (keyword) using Reciprocal Rank Fusion.
        
        Args:
            query: User query string
            k: Number of results to return
            alpha: Weight for semantic search (0=keyword only, 1=semantic only, 0.5=balanced)
        
        Returns:
            List of chunks with combined scores
        """
        if not self.index or not self.chunks:
            logger.warning("[RAG] Index not built yet")
            return []
        
        # Always get more candidates than we need for fusion
        num_candidates = min(k * 3, len(self.chunks))
        
        # 1. FAISS semantic search
        faiss_results = self.search(query, k=num_candidates)
        faiss_ranks = {r['chunk_id']: i + 1 for i, r in enumerate(faiss_results)}
        
        # 2. BM25 keyword search (if available)
        bm25_ranks = {}
        if BM25_AVAILABLE and self.bm25:
            tokenized_query = query.lower().split()
            bm25_scores = self.bm25.get_scores(tokenized_query)
            
            # Get top indices by BM25 score
            top_bm25_indices = np.argsort(bm25_scores)[::-1][:num_candidates]
            for rank, idx in enumerate(top_bm25_indices):
                bm25_ranks[idx] = rank + 1
        
        # 3. Reciprocal Rank Fusion (RRF)
        # RRF score = sum(1 / (k + rank)) for each ranking
        k_rrf = 60  # Standard RRF parameter
        fusion_scores = {}
        
        all_chunk_ids = set(faiss_ranks.keys()) | set(bm25_ranks.keys())
        
        for chunk_id in all_chunk_ids:
            score = 0.0
            
            # Semantic contribution
            if chunk_id in faiss_ranks:
                score += alpha * (1.0 / (k_rrf + faiss_ranks[chunk_id]))
            
            # Keyword contribution
            if chunk_id in bm25_ranks:
                score += (1 - alpha) * (1.0 / (k_rrf + bm25_ranks[chunk_id]))
            
            fusion_scores[chunk_id] = score
        
        # Sort by fusion score
        sorted_ids = sorted(fusion_scores.keys(), key=lambda x: fusion_scores[x], reverse=True)[:k]
        
        # Build results
        results = []
        for chunk_id in sorted_ids:
            chunk = self.chunks[chunk_id].copy()
            chunk['fusion_score'] = fusion_scores[chunk_id]
            chunk['in_faiss'] = chunk_id in faiss_ranks
            chunk['in_bm25'] = chunk_id in bm25_ranks
            results.append(chunk)
        
        logger.info(f"[RAG] Hybrid search: {len(results)} results (FAISS: {len(faiss_ranks)}, BM25: {len(bm25_ranks)})")
        return results
    
    def save(self, path: Path):
        """Save index and chunks to disk."""
        if not self.index:
            logger.warning("[RAG] No index to save")
            return
        
        try:
            path.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            index_path = path / "faiss.index"
            faiss.write_index(self.index, str(index_path))
            
            # Save chunks as JSON
            chunks_path = path / "chunks.json"
            with open(chunks_path, "w", encoding='utf-8') as f:
                json.dump(self.chunks, f, ensure_ascii=False)
            
            logger.info(f"[RAG] Saved index to {path} ({self.index.ntotal} vectors, {len(self.chunks)} chunks)")
        
        except Exception as e:
            logger.error(f"[RAG] Failed to save index: {e}")
            raise
    
    def load(self, path: Path):
        """Load index and chunks from disk."""
        index_path = path / "faiss.index"
        chunks_json = path / "chunks.json"
        chunks_pkl = path / "chunks.pkl"
        
        if not index_path.exists():
            logger.warning(f"[RAG] Index not found at {path}")
            return False
        
        if not chunks_json.exists() and not chunks_pkl.exists():
            logger.warning(f"[RAG] Chunks not found at {path}")
            return False
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(index_path))
            
            # Load chunks (prefer JSON, fallback to pickle)
            if chunks_json.exists():
                with open(chunks_json, "r", encoding='utf-8') as f:
                    self.chunks = json.load(f)
                logger.info(f"[RAG] Loaded index: {self.index.ntotal} vectors from JSON")
            else:
                with open(chunks_pkl, "rb") as f:
                    self.chunks = pickle.load(f)
                logger.info(f"[RAG] Loaded index: {self.index.ntotal} vectors from pickle")
            
            # Rebuild BM25 index for hybrid search
            if BM25_AVAILABLE and self.chunks:
                texts = [c["text"] for c in self.chunks]
                tokenized_texts = [text.lower().split() for text in texts]
                self.bm25 = BM25Okapi(tokenized_texts)
                logger.info(f"[RAG] Rebuilt BM25 index for hybrid search")
            
            return True
        
        except Exception as e:
            logger.error(f"[RAG] Failed to load index: {e}")
            return False


def generate_rag_response(query: str, rag: LocalRAG, llm_backend, use_hybrid: bool = True) -> Generator[str, None, None]:
    """
    Generate response using RAG context with source citations.
    
    Args:
        query: User question
        rag: LocalRAG instance with loaded index
        llm_backend: Backend for LLM communication
        use_hybrid: Use hybrid search (FAISS + BM25) if available
    
    Yields:
        Response text chunks from LLM
    """
    # Search relevant chunks (hybrid if available, otherwise semantic)
    if use_hybrid and BM25_AVAILABLE and rag.bm25:
        context_chunks = rag.hybrid_search(query, k=5, alpha=0.6)  # Slightly favor semantic
    else:
        context_chunks = rag.search(query, k=5)
    
    if not context_chunks:
        yield "I don't have enough information to answer that question."
        return
    
    # Build numbered context for citations
    context_parts = []
    sources_list = []
    
    for i, c in enumerate(context_chunks, 1):
        context_parts.append(f"[{i}] Source: {c['title']}\n{c['text']}")
        sources_list.append(f"[{i}] {c['title']} - {c.get('url', 'N/A')}")
    
    context = "\n\n".join(context_parts)
    
    # Enhanced prompt with citation instructions
    prompt = f"""Based on the following sources, answer the user's question. 
Cite your sources using [1], [2], etc. when referring to specific information.

SOURCES:
{context}

USER QUESTION: {query}

INSTRUCTIONS:
- Answer based ONLY on the provided sources
- Cite sources like [1], [2] when using specific facts
- If the answer isn't in the sources, say "I couldn't find this in my knowledge base."
- Be concise but thorough

ANSWER:"""
    
    # Send to LLM (streaming)
    for chunk in llm_backend.send_message(prompt):
        yield chunk
    
    # Append sources footer
    yield "\n\n---\n**Sources:**\n"
    for source in sources_list[:3]:  # Show top 3 sources
        yield f"{source}\n"
