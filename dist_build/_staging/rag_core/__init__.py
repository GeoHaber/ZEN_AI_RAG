"""
rag_core — Standardised RAG Pipeline
======================================

Shared, production-grade RAG engine used across all projects:
  - Local_LLM (function catalog search)
  - RAG_RAT  (document Q&A)
  - ZEN_AI_RAG (agent workflows)

Pipeline (2025 best practices)::

    Documents → Chunker → Embed → Deduplicate → Vector Store (Qdrant)
                                                        ↓
    Query → Dense + BM25 → RRF Fusion → Cross-Encoder Rerank → Results

Usage::

    from rag_core import RAGEngine

    rag = RAGEngine(collection="my_project")
    await rag.initialize()
    await rag.build_index(documents)
    results = await rag.search("parse JSON config", top_k=10)
"""

from rag_core.engine import RAGEngine
from rag_core.search import HybridSearcher, SearchResult
from rag_core.embeddings import EmbeddingManager, EMBEDDING_MODELS
from rag_core.reranker import RerankerManager, RERANKER_MODELS
from rag_core.bm25_index import BM25Index
from rag_core.chunker import TextChunker, ChunkerConfig, Chunk
from rag_core.fusion import reciprocal_rank_fusion
from rag_core.dedup import DeduplicationManager
from rag_core.cache import SemanticCache

__version__ = "1.0.0"

__all__ = [
    "RAGEngine",
    "HybridSearcher",
    "SearchResult",
    "EmbeddingManager",
    "EMBEDDING_MODELS",
    "RerankerManager",
    "RERANKER_MODELS",
    "BM25Index",
    "TextChunker",
    "ChunkerConfig",
    "Chunk",
    "reciprocal_rank_fusion",
    "DeduplicationManager",
    "SemanticCache",
]
