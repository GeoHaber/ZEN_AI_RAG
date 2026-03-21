"""
Core/services/enhanced_rag_service.py — Industry-Best Enhanced RAG Pipeline.

Extends the base RAGService with adaptive routing and SOTA enhancements:

  1. **Query Router**: Classifies intent → selects optimal pipeline
  2. **HyDE**: Hypothetical document embeddings for better retrieval
  3. **Contextual Retrieval**: Anthropic-style chunk enrichment
  4. **Corrective RAG**: Self-healing retrieval with quality grading
  5. **FLARE**: Forward-looking active retrieval for uncertain answers
  6. **Parent Document Retrieval**: Small-to-big context expansion
  7. **Graph RAG**: Community-based global Q&A

The pipeline adapts automatically based on query complexity:
  - Simple queries: fast path (retrieve → rerank → generate)
  - Analytical queries: full path (HyDE + CRAG + FLARE + rerank)
  - Multi-hop queries: knowledge graph + multi-hop traversal
  - Global queries: community summaries via Graph RAG
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EnhancedRAGService:
    """Orchestrates the full industry-best RAG pipeline with adaptive routing.

    This service wires together all SOTA RAG components, selecting
    the optimal strategy per query based on intent classification.

    Usage:
        service = EnhancedRAGService()
        service.initialize(
            retrieve_fn=my_search,
            generate_fn=my_generate,
            llm_fn=my_llm,
            embed_fn=my_embed,
        )
        result = service.query("Compare X and Y")
    """

    def __init__(self):
        self._initialized = False
        self._retrieve_fn: Optional[Callable] = None
        self._generate_fn: Optional[Callable] = None
        self._llm_fn: Optional[Callable] = None
        self._embed_fn: Optional[Callable] = None
        self._search_by_embedding_fn: Optional[Callable] = None

        # Lazy component references
        self._router = None
        self._hyde = None
        self._crag = None
        self._flare = None
        self._compressor = None
        self._reranker = None
        self._parent_retriever = None
        self._graph_rag = None

    def initialize(
        self,
        retrieve_fn: Optional[Callable] = None,
        generate_fn: Optional[Callable] = None,
        llm_fn: Optional[Callable] = None,
        embed_fn: Optional[Callable] = None,
        search_by_embedding_fn: Optional[Callable] = None,
        knowledge_graph: Any = None,
    ):
        """Wire up function dependencies for the pipeline.

        Args:
            retrieve_fn: function(query, top_k) -> List[Dict]
            generate_fn: function(query, chunks) -> str
            llm_fn: function(prompt) -> str
            embed_fn: function(text) -> List[float]
            search_by_embedding_fn: function(embedding, top_k) -> List[Dict]
            knowledge_graph: Optional KnowledgeGraph instance
        """
        self._retrieve_fn = retrieve_fn
        self._generate_fn = generate_fn
        self._llm_fn = llm_fn
        self._embed_fn = embed_fn
        self._search_by_embedding_fn = search_by_embedding_fn

        # Initialize components lazily
        self._init_router()
        self._init_hyde()
        self._init_crag()
        self._init_flare()
        self._init_compressor()
        self._init_parent_retriever()
        self._init_graph_rag(knowledge_graph)

        self._initialized = True
        logger.info("[EnhancedRAG] Pipeline initialized with all SOTA components")

    def query(
        self,
        query: str,
        top_k: int = 10,
        context: Optional[Dict[str, Any]] = None,
        force_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute the adaptive RAG pipeline.

        Args:
            query: User query
            top_k: Max results to retrieve
            context: Optional context (conversation history, etc.)
            force_strategy: Override automatic routing

        Returns:
            Dict with 'answer', 'sources', 'metadata'
        """
        start_time = time.time()

        if not self._initialized:
            logger.warning("[EnhancedRAG] Not initialized, returning empty")
            return {"answer": "", "sources": [], "metadata": {"error": "not_initialized"}}

        # Step 1: Route query to optimal pipeline
        routing = self._route_query(query, context, force_strategy)
        logger.info(
            f"[EnhancedRAG] Routed '{query[:50]}' → {routing.get('intent', 'unknown')} "
            f"(confidence: {routing.get('confidence', 0):.2f})"
        )

        # Step 2: Execute the determined pipeline
        try:
            result = self._execute_pipeline(query, top_k, routing)
        except Exception as e:
            logger.error(f"[EnhancedRAG] Pipeline failed: {e}")
            result = {"answer": "", "sources": [], "metadata": {"error": str(e)}}

        elapsed = time.time() - start_time
        result.setdefault("metadata", {})
        result["metadata"]["latency_ms"] = round(elapsed * 1000, 2)
        result["metadata"]["routing"] = routing

        return result

    def _route_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
        force_strategy: Optional[str],
    ) -> Dict[str, Any]:
        """Determine the optimal pipeline for this query."""
        if force_strategy:
            from Core.query_router import QueryIntent
            intent_map = {
                "simple": QueryIntent.SIMPLE,
                "analytical": QueryIntent.ANALYTICAL,
                "multi_hop": QueryIntent.MULTI_HOP,
                "temporal": QueryIntent.TEMPORAL,
                "aggregate": QueryIntent.AGGREGATE,
            }
            intent = intent_map.get(force_strategy)
            if intent and self._router:
                config = self._router.get_pipeline_for_intent(intent)
                return {
                    "intent": force_strategy,
                    "confidence": 1.0,
                    **config,
                }

        if self._router:
            decision = self._router.route(query, context)
            return {
                "intent": decision.intent.value,
                "confidence": decision.confidence,
                "use_hyde": decision.use_hyde,
                "use_flare": decision.use_flare,
                "use_crag": decision.use_crag,
                "use_knowledge_graph": decision.use_knowledge_graph,
                "use_contextual_compression": decision.use_contextual_compression,
                "top_k": decision.top_k,
                "temperature": decision.temperature,
                "pipeline": decision.recommended_pipeline,
            }

        # Fallback: standard pipeline
        return {
            "intent": "simple",
            "confidence": 0.5,
            "use_hyde": False,
            "use_flare": False,
            "use_crag": False,
            "use_knowledge_graph": False,
            "top_k": top_k if 'top_k' in dir() else 10,
            "pipeline": ["retrieve", "rerank", "generate"],
        }

    def _execute_pipeline(
        self,
        query: str,
        top_k: int,
        routing: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute the pipeline determined by routing."""
        effective_top_k = routing.get("top_k", top_k)
        chunks: List[Dict[str, Any]] = []
        metadata: Dict[str, Any] = {"stages": []}

        # Stage: Knowledge Graph lookup (for multi-hop)
        if routing.get("use_knowledge_graph") and self._graph_rag:
            strategy = "global" if routing.get("intent") == "aggregate" else "local"
            graph_result = self._graph_rag.query(query, strategy=strategy)
            if graph_result.answer:
                metadata["graph_rag"] = {
                    "strategy": graph_result.strategy,
                    "communities_used": graph_result.community_summaries_used,
                }
                metadata["stages"].append("graph_rag")
                # For global queries, graph answer may be sufficient
                if strategy == "global" and graph_result.answer:
                    return {
                        "answer": graph_result.answer,
                        "sources": [
                            {"type": "community", "entities": c.entities[:5]}
                            for c in graph_result.matched_communities
                        ],
                        "metadata": metadata,
                    }

        # Stage: HyDE retrieval
        if routing.get("use_hyde") and self._hyde and self._retrieve_fn:
            try:
                standard_chunks = self._retrieve_fn(query, effective_top_k)
                from Core.hyde_retrieval import HyDERetriever
                query_type = HyDERetriever.classify_query_type(query)
                chunks = self._hyde.retrieve_with_fusion(
                    query, standard_chunks, top_k=effective_top_k,
                )
                metadata["stages"].append("hyde")
            except Exception as e:
                logger.warning(f"[EnhancedRAG] HyDE failed, falling back: {e}")
                if self._retrieve_fn:
                    chunks = self._retrieve_fn(query, effective_top_k)
        elif self._retrieve_fn:
            # Standard retrieval
            chunks = self._retrieve_fn(query, effective_top_k)
            metadata["stages"].append("retrieve")

        # Stage: Parent document expansion
        if self._parent_retriever and any(c.get("parent_id") for c in chunks):
            chunks = self._parent_retriever.get_parent_context(chunks)
            metadata["stages"].append("parent_expansion")

        # Stage: Contextual compression
        if routing.get("use_contextual_compression") and self._compressor:
            chunks = self._compressor.compress(query, chunks)
            metadata["stages"].append("compression")

        # Stage: Corrective RAG
        if routing.get("use_crag") and self._crag:
            crag_result = self._crag.retrieve_and_generate(
                query, initial_chunks=chunks, top_k=effective_top_k,
            )
            if crag_result.answer:
                metadata["crag"] = {
                    "grade": crag_result.grade.value,
                    "confidence": crag_result.confidence,
                    "corrections": crag_result.corrections_applied,
                    "iterations": crag_result.iterations,
                }
                metadata["stages"].append("crag")
                return {
                    "answer": crag_result.answer,
                    "sources": self._format_sources(crag_result.corrected_chunks),
                    "metadata": metadata,
                }

        # Stage: FLARE (iterative retrieval)
        if routing.get("use_flare") and self._flare:
            flare_result = self._flare.retrieve_and_generate(query, chunks)
            if flare_result.final_answer:
                metadata["flare"] = {
                    "iterations": flare_result.iterations,
                    "sub_queries": flare_result.sub_queries,
                    "confidence_improved": flare_result.confidence_improved,
                }
                metadata["stages"].append("flare")
                return {
                    "answer": flare_result.final_answer,
                    "sources": self._format_sources(chunks),
                    "metadata": metadata,
                }

        # Stage: Standard generation
        answer = ""
        if self._generate_fn and chunks:
            try:
                answer = self._generate_fn(query, chunks)
                metadata["stages"].append("generate")
            except Exception as e:
                logger.warning(f"[EnhancedRAG] Generation failed: {e}")

        return {
            "answer": answer or "",
            "sources": self._format_sources(chunks),
            "metadata": metadata,
        }

    # ─── Component Initialization ──────────────────────────

    def _init_router(self):
        try:
            from Core.query_router import QueryRouter
            self._router = QueryRouter(llm_fn=self._llm_fn)
        except Exception as e:
            logger.debug(f"[EnhancedRAG] QueryRouter init failed: {e}")

    def _init_hyde(self):
        try:
            from Core.hyde_retrieval import HyDERetriever
            self._hyde = HyDERetriever(
                llm_fn=self._llm_fn,
                embed_fn=self._embed_fn,
                search_fn=self._search_by_embedding_fn,
            )
        except Exception as e:
            logger.debug(f"[EnhancedRAG] HyDE init failed: {e}")

    def _init_crag(self):
        try:
            from Core.corrective_rag import CorrectiveRAG
            self._crag = CorrectiveRAG(
                retrieve_fn=self._retrieve_fn,
                generate_fn=self._generate_fn,
                llm_fn=self._llm_fn,
                embed_fn=self._embed_fn,
            )
        except Exception as e:
            logger.debug(f"[EnhancedRAG] CRAG init failed: {e}")

    def _init_flare(self):
        try:
            from Core.flare_retrieval import FLARERetriever
            self._flare = FLARERetriever(
                retrieve_fn=self._retrieve_fn,
                generate_fn=self._generate_fn,
            )
        except Exception as e:
            logger.debug(f"[EnhancedRAG] FLARE init failed: {e}")

    def _init_compressor(self):
        try:
            from Core.contextual_compressor import ContextualCompressor
            self._compressor = ContextualCompressor(max_tokens=2000)
        except Exception as e:
            logger.debug(f"[EnhancedRAG] Compressor init failed: {e}")

    def _init_parent_retriever(self):
        try:
            from Core.parent_document_retrieval import ParentDocumentRetriever
            self._parent_retriever = ParentDocumentRetriever()
        except Exception as e:
            logger.debug(f"[EnhancedRAG] ParentDoc init failed: {e}")

    def _init_graph_rag(self, knowledge_graph: Any = None):
        if knowledge_graph:
            try:
                from Core.graph_rag import GraphRAG
                self._graph_rag = GraphRAG(
                    knowledge_graph=knowledge_graph,
                    llm_fn=self._llm_fn,
                )
            except Exception as e:
                logger.debug(f"[EnhancedRAG] GraphRAG init failed: {e}")

    @staticmethod
    def _format_sources(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format chunk list into clean source references."""
        sources = []
        for chunk in chunks[:10]:
            sources.append({
                "text": chunk.get("text", "")[:300],
                "url": chunk.get("url", ""),
                "title": chunk.get("title", ""),
                "score": chunk.get("score", 0),
            })
        return sources
