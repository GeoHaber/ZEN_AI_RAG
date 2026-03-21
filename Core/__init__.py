"""
Core package - Business logic, domain models, and service layer.

Adapted from RAG_RAT's proven Clean Architecture pattern.
Provides the foundational types, exceptions, and service abstractions
used throughout ZEN_AI_RAG.

Advanced RAG modules ported from ZEN_RAG:
  constants, rag_models, zero_waste_cache, smart_deduplicator,
  hallucination_detector_v2, answer_refinement, reranker_advanced,
  knowledge_graph, flare_retrieval, confidence_scorer, query_rewriter,
  contextual_compressor, conflict_detector, follow_up_generator,
  prompt_focus, metrics_tracker, evaluation, inference_guard.

Industry-best RAG enhancements (2024-2026 SOTA):
  contextual_retrieval — Anthropic-style chunk contextualization
  hyde_retrieval — Hypothetical Document Embeddings (Gao et al. 2022)
  corrective_rag — Self-healing retrieval (CRAG, Yan et al. 2024)
  query_router — Adaptive intent-based pipeline routing
  parent_document_retrieval — Small-to-big hierarchical retrieval
  graph_rag — Microsoft-style community detection & global Q&A
"""

from Core.models import (
    ResponseStatus,
    QueryRequest,
    QueryResponse,
    ChatRequest,
    ChatResponse,
    ChatMessage,
    SearchRequest,
    SearchResult,
    SearchResponse,
    StreamRequest,
    StreamChunk,
    StatusResponse,
)

from Core.exceptions import (
    ZenAIError,
    ConfigurationError,
    ProviderError,
    AuthenticationError,
    LLMError,
    RAGError,
    DocumentError,
    ValidationError,
)

# --- Advanced RAG modules (lazy-importable) ---
# These are NOT eagerly imported to avoid heavy dependency loading at startup.
# Import them explicitly when needed:
#   from Core.zero_waste_cache import ZeroWasteCache
#   from Core.hallucination_detector_v2 import AdvancedHallucinationDetector
#   etc.

__all__ = [
    # Models
    "ResponseStatus",
    "QueryRequest",
    "QueryResponse",
    "ChatRequest",
    "ChatResponse",
    "ChatMessage",
    "SearchRequest",
    "SearchResult",
    "SearchResponse",
    "StreamRequest",
    "StreamChunk",
    "StatusResponse",
    # Exceptions
    "ZenAIError",
    "ConfigurationError",
    "ProviderError",
    "AuthenticationError",
    "LLMError",
    "RAGError",
    "DocumentError",
    "ValidationError",
    # Advanced RAG module names (for documentation / discoverability)
    "constants",
    "rag_models",
    "zero_waste_cache",
    "smart_deduplicator",
    "hallucination_detector_v2",
    "answer_refinement",
    "reranker_advanced",
    "knowledge_graph",
    "flare_retrieval",
    "confidence_scorer",
    "query_rewriter",
    "contextual_compressor",
    "conflict_detector",
    "follow_up_generator",
    "prompt_focus",
    "metrics_tracker",
    "evaluation",
    "inference_guard",
    # Industry-best RAG enhancements (lazy-importable)
    "contextual_retrieval",
    "hyde_retrieval",
    "corrective_rag",
    "query_router",
    "parent_document_retrieval",
    "graph_rag",
]
