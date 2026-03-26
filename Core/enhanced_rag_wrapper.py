"""
Core/enhanced_rag_wrapper.py - Enhanced RAG with Query Intelligence & Caching

Wraps the existing RAG service with:
- Query expansion and processing
- Semantic caching
- Answer evaluation
- Reranking → Compression → Generation (proper pipeline order)
- Performance metrics

This is a non-breaking enhancement that can be toggled on/off.
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime
import time

from Core.services.rag_service import RAGService
from Core.query_processor import get_query_processor
from Core.semantic_cache import get_semantic_cache
from Core.evaluation import get_answer_evaluator
from Core.contextual_compressor import get_contextual_compressor
from Core.reranker import get_reranker

logger = logging.getLogger(__name__)


def _add_response_validation(result: Dict[str, Any]) -> None:
    """Run chat response validation and attach result for UI (error/gibberish detection)."""
    try:
        from Core.chat_query_interpretation import validate_chat_response

        response = result.get("response", "") or ""
        qm = result.get("query_metadata") or {}
        intent = qm.get("intent", "DOC")
        validation = validate_chat_response(response, intent=intent)
        result["response_validation"] = validation
        if not validation.get("ok"):
            logger.warning(
                "Response validation failed: is_error=%s is_gibberish=%s suggestion=%s",
                validation.get("is_error"),
                validation.get("is_gibberish"),
                validation.get("suggestion", ""),
            )
    except Exception as e:
        logger.debug("Response validation skipped: %s", e)
        result["response_validation"] = {
            "ok": True,
            "is_error": False,
            "is_gibberish": False,
            "is_empty": False,
            "suggestion": "",
        }


class EnhancedRAGService:
    """
    Enhanced RAG service with query intelligence and caching

    Features:
    - Query expansion for better retrieval
    - Semantic caching for faster responses
    - Answer quality evaluation
    - Performance tracking
    """

    def __init__(
        self,
        enable_cache: bool = True,
        enable_query_expansion: bool = True,
        enable_evaluation: bool = True,
    ):
        """
        Initialize enhanced RAG service

        Args:
            enable_cache: Enable semantic caching
            enable_query_expansion: Enable query expansion
            enable_evaluation: Enable answer evaluation
        """
        self.base_service = RAGService()
        self.enable_cache = enable_cache
        self.enable_query_expansion = enable_query_expansion
        self.enable_evaluation = enable_evaluation

        # Initialize components
        self.query_processor = get_query_processor() if enable_query_expansion else None
        self.cache = get_semantic_cache() if enable_cache else None
        self.evaluator = get_answer_evaluator() if enable_evaluation else None

        logger.info(
            f"Enhanced RAG initialized: cache={enable_cache}, "
            f"expansion={enable_query_expansion}, eval={enable_evaluation}"
        )

    async def full_rag_pipeline(
        self,
        query: str,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        top_k: int = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
        use_cache: bool = True,
        use_deep_research: bool = False,
        use_deep_verify: bool = False,
        use_conflict_detection: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute enhanced RAG pipeline with caching and evaluation
        """
        if top_k is None:
            try:
                from config_enhanced import Config

                top_k = getattr(Config, "TOP_K_RESULTS", 30)
            except Exception:
                top_k = 30
        start_time = time.time()

        # Step 1: Interpret chat query (STAT/DOC/HYBRID) for correct routing
        try:
            from Core.chat_query_interpretation import interpret_chat_query

            interpretation = interpret_chat_query(query)
            route_intent = interpretation.get("intent", "DOC")
            route_hint = interpretation.get("route_hint", "documents")
            logger.info(f"📌 Query interpretation: intent={route_intent}, route_hint={route_hint}")
        except Exception as e:
            logger.warning(f"Chat interpretation failed (non-critical): {e}")
            route_intent = "DOC"
            route_hint = "documents"

        # Step 1b: Process query (expansion/normalization)
        processed_query = query
        query_metadata = {
            "original_query": query,
            "intent": route_intent,
            "route_hint": route_hint,
        }
        if self.enable_query_expansion and self.query_processor:
            logger.info("🔍 Processing query...")
            query_result = self.query_processor.process_query(query, expand=False)
            processed_query = query_result["processed"]
            query_metadata["processed_query"] = processed_query
            query_metadata["intent_detail"] = query_result.get("intent")
            logger.info(f"Query intent (detail): {query_result.get('intent')}")

        # Step 2: Check cache
        cache_hit = False
        if self.enable_cache and use_cache and self.cache:
            try:
                from ui.state import get_rag_integration

                rag_integration = get_rag_integration()

                if rag_integration and hasattr(rag_integration, "embed_text"):
                    query_embedding = await rag_integration.embed_text(processed_query)
                    cached_result = self.cache.lookup(processed_query, query_embedding)

                    if cached_result:
                        cache_hit = True
                        logger.info("⚡ Cache HIT - returning cached result")
                        cached_result["cache_hit"] = True
                        cached_result["latency_ms"] = (time.time() - start_time) * 1000
                        return cached_result
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")

        # Step 2.5: STAT path (schema + examples → SQL → optional execute) for statistics queries
        try:
            from Core.stat_router import is_stat_query

            if is_stat_query(processed_query):
                from Core.stat_pipeline import run_stat_pipeline
                from ui.state import get_rag_integration

                logger.info("📊 STAT path: schema + SQL pipeline")

                async def _llm_for_stat(messages, **kw):
                    return await self.base_service.generate_response(
                        messages,
                        kw.get("provider"),
                        kw.get("model"),
                        api_key=kw.get("api_key"),
                        temperature=kw.get("temperature", 0.3),
                        max_tokens=kw.get("max_tokens", 512),
                    )

                stat_result = await run_stat_pipeline(
                    processed_query,
                    get_rag_integration,
                    {"provider": provider, "model": model, "api_key": api_key},
                    _llm_for_stat,
                )
                if stat_result.get("response"):
                    out = {
                        "response": stat_result["response"],
                        "sources": stat_result.get("sources", []),
                        "query_metadata": {
                            **query_metadata,
                            "intent": "STAT",
                            "applied_filters": stat_result.get("applied_filters", {}),
                        },
                        "evaluation": {},
                        "conflicts": [],
                        "verify_result": None,
                        "cache_hit": False,
                        "latency_ms": (time.time() - start_time) * 1000,
                    }
                    _add_response_validation(out)
                    return out
        except ImportError as exc:
            logger.debug("%s", exc)
        except Exception as e:
            logger.warning("STAT path failed, falling back to RAG: %s", e)

        # Step 3: Execute Core Logic (RAG or Research)
        try:
            documents = []
            raw_response = ""

            if use_deep_research:
                logger.info("🕵️‍♂️ Using Deep Research...")
                from Core.research_agent import ResearchAgent

                agent = ResearchAgent()
                research_result = await agent.research_async(processed_query, max_sources=3)
                raw_response = research_result.get("answer", "")
                documents = research_result.get("sources", [])
            else:
                # === Proper pipeline: Retrieve → Rerank → Compress → Augment → Generate ===

                # Step 3a: Retrieve documents
                logger.info(f"📚 Retrieving top-{top_k} documents...")
                documents = await self.base_service.retrieve_documents(processed_query, top_k)
                logger.info(f"📚 Retrieved {len(documents)} documents")

                # Step 3b: Rerank for better relevance ordering
                if documents and self.enable_query_expansion:
                    try:
                        reranker = get_reranker()
                        chunk_texts = [doc.get("content", doc.get("text", "")) for doc in documents]
                        if chunk_texts and any(chunk_texts):
                            ranked_texts, scores = reranker.rerank(
                                processed_query,
                                chunk_texts,
                                top_k=top_k,
                                return_scores=True,
                            )
                            # Rebuild documents list in reranked order (support duplicate content)
                            text_to_docs = {}
                            for doc in documents:
                                key = doc.get("content", doc.get("text", ""))
                                text_to_docs.setdefault(key, []).append(doc)
                            reranked_docs = []
                            for text, score in zip(ranked_texts, scores):
                                stack = text_to_docs.get(text)
                                if stack:
                                    doc = stack.pop(0).copy()
                                    doc["rerank_score"] = score
                                    reranked_docs.append(doc)
                            if reranked_docs:
                                documents = reranked_docs
                                logger.info(f"🔄 Reranked {len(documents)} documents")
                    except Exception as e:
                        logger.warning(f"Reranking failed (non-critical): {e}")

                # Step 3c: Skip compression for STAT/table data so counts and numbers stay accurate
                skip_compression = route_intent == "STAT" or any(
                    doc.get("sheet_name") is not None or doc.get("row_index") is not None for doc in documents
                )
                if documents and not skip_compression:
                    try:
                        compressor = get_contextual_compressor()
                        chunk_texts = [doc.get("content", doc.get("text", "")) for doc in documents]
                        compressed_texts, comp_stats = compressor.compress_chunks(
                            processed_query, chunk_texts, use_llm=False
                        )
                        # Update document texts with compressed versions
                        for doc, compressed in zip(documents, compressed_texts):
                            if "content" in doc:
                                doc["content"] = compressed
                            elif "text" in doc:
                                doc["text"] = compressed
                        savings = comp_stats.get("token_savings_percent", 0)
                        if savings > 0:
                            logger.info(f"🗜️ Compressed context: {savings:.0f}% token savings")
                    except Exception as e:
                        logger.warning(f"Compression failed (non-critical): {e}")
                elif skip_compression:
                    logger.info("📊 Skipping compression (STAT/table data) to preserve accurate numbers")

                # Step 3d: Augment query with reranked+compressed context
                messages = self.base_service.augment_query(processed_query, documents, system_prompt)

                # Step 3e: Generate response from LLM
                logger.info("🤖 Generating response...")
                raw_response = await self.base_service.generate_response(
                    messages,
                    provider,
                    model,
                    api_key,
                    temperature,
                    max_tokens,
                    **kwargs,
                )
                logger.info(f"📚 Retrieved {len(documents)} documents")

                # Step 3b: Rerank for better relevance ordering (independent of query expansion)
                if documents:
                    try:
                        reranker = get_reranker()
                        chunk_texts = [doc.get("content", doc.get("text", "")) for doc in documents]
                        if chunk_texts and any(chunk_texts):
                            ranked_texts, scores = reranker.rerank(
                                processed_query,
                                chunk_texts,
                                top_k=top_k,
                                return_scores=True,
                            )
                            # Rebuild documents list in reranked order (support duplicate content)
                            text_to_docs = {}
                            for doc in documents:
                                key = doc.get("content", doc.get("text", ""))
                                text_to_docs.setdefault(key, []).append(doc)
                            reranked_docs = []
                            for text, score in zip(ranked_texts, scores):
                                stack = text_to_docs.get(text)
                                if stack:
                                    doc = stack.pop(0).copy()
                                    doc["rerank_score"] = score
                                    reranked_docs.append(doc)
                            if reranked_docs:
                                documents = reranked_docs
                                logger.info(f"🔄 Reranked {len(documents)} documents")
                    except Exception as e:
                        logger.warning(f"Reranking failed (non-critical): {e}")

                # Step 3c: Skip compression for STAT/table data so counts and numbers stay accurate
                skip_compression = route_intent == "STAT" or any(
                    doc.get("sheet_name") is not None or doc.get("row_index") is not None for doc in documents
                )
                if documents and not skip_compression:
                    try:
                        compressor = get_contextual_compressor()
                        chunk_texts = [doc.get("content", doc.get("text", "")) for doc in documents]
                        compressed_texts, comp_stats = compressor.compress_chunks(
                            processed_query, chunk_texts, use_llm=False
                        )
                        # Update document texts with compressed versions
                        for doc, compressed in zip(documents, compressed_texts):
                            if "content" in doc:
                                doc["content"] = compressed
                            elif "text" in doc:
                                doc["text"] = compressed
                        savings = comp_stats.get("token_savings_percent", 0)
                        if savings > 0:
                            logger.info(f"🗜️ Compressed context: {savings:.0f}% token savings")
                    except Exception as e:
                        logger.warning(f"Compression failed (non-critical): {e}")
                elif skip_compression:
                    logger.info("📊 Skipping compression (STAT/table data) to preserve accurate numbers")

                # Step 3d: Augment query with reranked+compressed context
                messages = self.base_service.augment_query(processed_query, documents, system_prompt)

                # Step 3e: Generate response from LLM
                logger.info("🤖 Generating response...")
                raw_response = await self.base_service.generate_response(
                    messages,
                    provider,
                    model,
                    api_key,
                    temperature,
                    max_tokens,
                    **kwargs,
                )
                logger.info(f"📚 Retrieved {len(documents)} documents")

                # Step 3b: Rerank for better relevance ordering (independent of query expansion)
                if documents:
                    try:
                        reranker = get_reranker()
                        chunk_texts = [doc.get("content", doc.get("text", "")) for doc in documents]
                        if chunk_texts and any(chunk_texts):
                            ranked_texts, scores = reranker.rerank(
                                processed_query,
                                chunk_texts,
                                top_k=top_k,
                                return_scores=True,
                            )
                            # Rebuild documents list in reranked order (support duplicate content)
                            text_to_docs = {}
                            for doc in documents:
                                key = doc.get("content", doc.get("text", ""))
                                text_to_docs[key] = doc
                            reranked_docs = []
                            for text, score in zip(ranked_texts, scores):
                                if text in text_to_docs:
                                    doc = text_to_docs[text].copy()
                                    doc["rerank_score"] = score
                                    reranked_docs.append(doc)
                            if reranked_docs:
                                documents = reranked_docs
                                logger.info(f"🔄 Reranked {len(documents)} documents")
                    except Exception as e:
                        logger.warning(f"Reranking failed (non-critical): {e}")

                # Step 3c: Skip compression for STAT/table data so counts and numbers stay accurate
                skip_compression = route_intent == "STAT" or any(
                    doc.get("sheet_name") is not None or doc.get("row_index") is not None for doc in documents
                )
                if documents and not skip_compression:
                    try:
                        compressor = get_contextual_compressor()
                        chunk_texts = [doc.get("content", doc.get("text", "")) for doc in documents]
                        compressed_texts, comp_stats = compressor.compress_chunks(
                            processed_query, chunk_texts, use_llm=False
                        )
                        # Update document texts with compressed versions
                        for doc, compressed in zip(documents, compressed_texts):
                            if "content" in doc:
                                doc["content"] = compressed
                            elif "text" in doc:
                                doc["text"] = compressed
                        savings = comp_stats.get("token_savings_percent", 0)
                        if savings > 0:
                            logger.info(f"🗜️ Compressed context: {savings:.0f}% token savings")
                    except Exception as e:
                        logger.warning(f"Compression failed (non-critical): {e}")
                elif skip_compression:
                    logger.info("📊 Skipping compression (STAT/table data) to preserve accurate numbers")

                # Step 3d: Augment query with reranked+compressed context
                messages = self.base_service.augment_query(processed_query, documents, system_prompt)

                # Step 3e: Generate response from LLM
                logger.info("🤖 Generating response...")
                raw_response = await self.base_service.generate_response(
                    messages,
                    provider,
                    model,
                    api_key,
                    temperature,
                    max_tokens,
                    **kwargs,
                )

            # Step 4: Conflict Detection
            conflicts = []
            if use_conflict_detection:
                try:
                    from Core.conflict_detector import ConflictDetector

                    detector = ConflictDetector()
                    conflicts = detector.detect_conflicts_in_sources(processed_query, documents)
                except Exception as e:
                    logger.error(f"Conflict detection failed: {e}")

            # Step 5: Deep Verify (LLM Judge)
            verify_result = None
            if use_deep_verify:
                try:
                    logger.info("🧠 Performing Deep Verify...")
                    from Core.deep_risk_analyzer import DeepRiskAnalyzer

                    analyzer = DeepRiskAnalyzer(llm_service=self.base_service.llm_service)
                    chunk_texts = [doc.get("content", doc.get("text", "")) for doc in documents]
                    verify_result = await analyzer.analyze_conflicts(processed_query, chunk_texts)
                except Exception as e:
                    logger.error(f"Deep Verify failed: {e}")

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Step 6: Evaluate answer
            evaluation_scores = {}
            if self.enable_evaluation and self.evaluator:
                logger.info("📊 Evaluating answer quality...")
                source_texts = [doc.get("content", doc.get("text", "")) for doc in documents]
                evaluation_scores = self.evaluator.evaluate_answer(
                    query,
                    raw_response,
                    source_texts,
                    metadata={"latency_ms": latency_ms},
                )

            # Build result
            result = {
                "response": raw_response,
                "sources": documents,
                "query_metadata": query_metadata,
                "evaluation": evaluation_scores,
                "conflicts": conflicts,
                "verify_result": verify_result,
                "cache_hit": False,
                "latency_ms": latency_ms,
                "timestamp": datetime.now().isoformat(),
            }

            # Step 6.5: Validate response (error/gibberish detection, aligned with test checks)
            _add_response_validation(result)

            # Step 7: Store in cache
            if self.enable_cache and self.cache and not cache_hit:
                try:
                    from ui.state import get_rag_integration

                    rag_integration = get_rag_integration()
                    if rag_integration and hasattr(rag_integration, "embed_text"):
                        query_embedding = await rag_integration.embed_text(processed_query)
                        self.cache.store(processed_query, query_embedding, result)
                        logger.info("💾 Stored result in cache")
                except Exception as e:
                    logger.warning(f"Cache storage failed: {e}")

            return result

        except Exception as e:
            logger.error(f"Enhanced RAG pipeline failed: {e}")
            raise

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return {"message": "Cache not enabled"}

    def get_evaluation_stats(self) -> Dict[str, Any]:
        """Get evaluation statistics"""
        if self.evaluator:
            return self.evaluator.get_statistics()
        return {"message": "Evaluation not enabled"}

    def clear_cache(self):
        """Clear semantic cache"""
        if self.cache:
            self.cache.clear()
            logger.info("Cache cleared")


# Singleton instance
_enhanced_rag_service = None


def get_enhanced_rag_service(
    enable_cache: bool = True,
    enable_query_expansion: bool = True,
    enable_evaluation: bool = True,
) -> EnhancedRAGService:
    """Get or create enhanced RAG service instance"""
    global _enhanced_rag_service
    if _enhanced_rag_service is None:
        _enhanced_rag_service = EnhancedRAGService(
            enable_cache=enable_cache,
            enable_query_expansion=enable_query_expansion,
            enable_evaluation=enable_evaluation,
        )
    return _enhanced_rag_service
