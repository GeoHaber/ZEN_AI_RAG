"""
Core/hyde_retrieval.py — Hypothetical Document Embeddings (HyDE).

Industry best practice: Instead of embedding the raw query, generate a
hypothetical answer and embed THAT. The hypothetical document is closer
in embedding space to relevant passages than the short query alone.

Pipeline:
  1. User query → LLM generates hypothetical answer (no retrieval)
  2. Embed the hypothetical answer
  3. Search vector store with hypothetical embedding
  4. Return real documents similar to the hypothetical

References:
  - Gao et al. "Precise Zero-Shot Dense Retrieval without Relevance Labels" (2022)
  - Widely adopted in LangChain, LlamaIndex, and production RAG systems
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HyDEResult:
    """Result of HyDE expansion."""

    original_query: str
    hypothetical_document: str
    hypothetical_embedding: Optional[List[float]] = None
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    strategy_used: str = "hyde"
    fallback_used: bool = False


class HyDERetriever:
    """Hypothetical Document Embeddings for improved retrieval.

    Generates a hypothetical answer to the query, then uses that
    document's embedding to find real similar passages. This bridges
    the lexical gap between questions and answers in embedding space.

    Usage:
        hyde = HyDERetriever(
            llm_fn=my_generate,
            embed_fn=my_embed,
            search_fn=my_vector_search,
        )
        results = hyde.retrieve("What causes aurora borealis?")
    """

    _HYDE_PROMPT_FACTUAL = (
        "Write a short, detailed passage (3-5 sentences) that would be a "
        "perfect answer to the following question. Write it as if it were "
        "extracted from a reference document. Be specific and factual.\n\n"
        "Question: {query}\n\nPassage:"
    )

    _HYDE_PROMPT_TECHNICAL = (
        "Write a technical documentation paragraph (3-5 sentences) that "
        "directly addresses the following question with precise details.\n\n"
        "Question: {query}\n\nDocumentation:"
    )

    _HYDE_PROMPT_ANALYTICAL = (
        "Write an analytical paragraph (3-5 sentences) that provides a "
        "comprehensive answer with reasoning and evidence.\n\n"
        "Question: {query}\n\nAnalysis:"
    )

    def __init__(
        self,
        llm_fn: Optional[Callable] = None,
        embed_fn: Optional[Callable] = None,
        search_fn: Optional[Callable] = None,
        num_hypothetical: int = 1,
        max_hypothetical_len: int = 500,
    ):
        """
        Args:
            llm_fn: function(prompt) -> str for hypothetical generation
            embed_fn: function(text) -> List[float] for embedding
            search_fn: function(embedding, top_k) -> List[Dict] for vector search
            num_hypothetical: number of hypothetical documents to generate
            max_hypothetical_len: max chars per hypothetical document
        """
        self.llm_fn = llm_fn
        self.embed_fn = embed_fn
        self.search_fn = search_fn
        self.num_hypothetical = num_hypothetical
        self.max_hypothetical_len = max_hypothetical_len

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        query_type: str = "factual",
    ) -> HyDEResult:
        """Generate hypothetical document and retrieve similar real passages.

        Args:
            query: User query
            top_k: Number of results to return
            query_type: "factual", "technical", or "analytical"

        Returns:
            HyDEResult with search results
        """
        if not self.llm_fn or not self.embed_fn or not self.search_fn:
            logger.warning("[HyDE] Missing required functions, falling back")
            return HyDEResult(
                original_query=query,
                hypothetical_document="",
                fallback_used=True,
            )

        # Step 1: Generate hypothetical document(s)
        hypotheticals = self._generate_hypotheticals(query, query_type)
        if not hypotheticals:
            return HyDEResult(
                original_query=query,
                hypothetical_document="",
                fallback_used=True,
            )

        # Step 2: Embed hypothetical(s) and search
        all_results: List[Dict[str, Any]] = []
        primary_hypothetical = hypotheticals[0]

        for hyp_doc in hypotheticals:
            try:
                embedding = self.embed_fn(hyp_doc)
                results = self.search_fn(embedding, top_k)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"[HyDE] Search with hypothetical failed: {e}")

        # Deduplicate by text
        seen_texts = set()
        unique_results = []
        for r in all_results:
            text_key = r.get("text", "")[:100]
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                unique_results.append(r)

        # Sort by score descending
        unique_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        return HyDEResult(
            original_query=query,
            hypothetical_document=primary_hypothetical,
            search_results=unique_results[:top_k],
            strategy_used="hyde",
        )

    def retrieve_with_fusion(
        self,
        query: str,
        standard_results: List[Dict[str, Any]],
        top_k: int = 10,
        hyde_weight: float = 0.4,
    ) -> List[Dict[str, Any]]:
        """Fuse HyDE results with standard retrieval results.

        Combines standard dense/hybrid search results with HyDE results
        using weighted Reciprocal Rank Fusion.

        Args:
            query: Original user query
            standard_results: Results from standard retrieval
            top_k: Number of results to return
            hyde_weight: Weight for HyDE results (0-1), rest for standard
        """
        hyde_result = self.retrieve(query, top_k=top_k)

        if hyde_result.fallback_used or not hyde_result.search_results:
            return standard_results[:top_k]

        # RRF fusion with weights
        scores: Dict[str, float] = {}
        items: Dict[str, Dict] = {}
        k = 60  # RRF constant

        # Standard results (weighted)
        standard_weight = 1.0 - hyde_weight
        for rank, item in enumerate(standard_results):
            text_key = item.get("text", "")[:100]
            rrf = standard_weight * (1.0 / (k + rank + 1))
            scores[text_key] = scores.get(text_key, 0.0) + rrf
            if text_key not in items:
                items[text_key] = item

        # HyDE results (weighted)
        for rank, item in enumerate(hyde_result.search_results):
            text_key = item.get("text", "")[:100]
            rrf = hyde_weight * (1.0 / (k + rank + 1))
            scores[text_key] = scores.get(text_key, 0.0) + rrf
            if text_key not in items:
                items[text_key] = item

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [
            {**items[key], "fusion_score": score, "_hyde_fused": True}
            for key, score in ranked[:top_k]
            if key in items
        ]

    def _generate_hypotheticals(self, query: str, query_type: str) -> List[str]:
        """Generate hypothetical answer documents."""
        prompts = {
            "factual": self._HYDE_PROMPT_FACTUAL,
            "technical": self._HYDE_PROMPT_TECHNICAL,
            "analytical": self._HYDE_PROMPT_ANALYTICAL,
        }
        prompt_template = prompts.get(query_type, self._HYDE_PROMPT_FACTUAL)
        results = []

        for _ in range(self.num_hypothetical):
            try:
                prompt = prompt_template.format(query=query)
                response = self.llm_fn(prompt)
                if response and len(response.strip()) > 20:
                    results.append(response.strip()[:self.max_hypothetical_len])
            except Exception as e:
                logger.warning(f"[HyDE] Hypothetical generation failed: {e}")

        return results

    @staticmethod
    def classify_query_type(query: str) -> str:
        """Heuristic classification of query type for prompt selection."""
        q = query.lower()
        technical_markers = [
            "how to", "implement", "configure",
            "install", "debug", "error",
        ]
        analytical_markers = [
            "why", "compare", "analyze", "evaluate", "impact",
            "difference", "advantage", "tradeoff", "pros and cons",
        ]
        if any(m in q for m in technical_markers):
            return "technical"
        if any(m in q for m in analytical_markers):
            return "analytical"
        return "factual"
