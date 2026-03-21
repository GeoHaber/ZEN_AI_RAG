"""
Core/query_rewriter.py — LLM-Based + Template Query Rewriting with RRF Fusion.

Strategies:
  1. LLM rewriting: ask LLM to generate query variations
  2. Template rewriting: rule-based reformulations
  3. Passthrough: return original query unchanged

Results merged via Reciprocal Rank Fusion (RRF).

Ported from ZEN_RAG.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

from Core.rag_models import QueryRewriteResult

logger = logging.getLogger(__name__)


class QueryRewriter:
    """Multi-strategy query rewriter for RAG retrieval improvement.

    Usage:
        rewriter = QueryRewriter(llm_fn=my_generate)
        result = rewriter.rewrite("What causes climate change?")
        for query in result.all_queries:
            chunks = search(query)
    """

    # Template patterns for rule-based rewriting
    TEMPLATES = {
        # "what is X" → ["define X", "X definition", "explain X"]
        r"^what\s+is\s+(.+?)[\?\.]*$": [
            "define {0}",
            "{0} definition",
            "explain {0}",
        ],
        # "how to X" → ["steps to X", "guide for X", "X tutorial"]
        r"^how\s+to\s+(.+?)[\?\.]*$": [
            "steps to {0}",
            "guide for {0}",
            "{0} tutorial",
        ],
        # "why does X" → ["reason for X", "cause of X", "X explanation"]
        r"^why\s+(?:does|do|did|is|are)\s+(.+?)[\?\.]*$": [
            "reason for {0}",
            "cause of {0}",
            "{0} explanation",
        ],
        # "compare X and Y" → ["X vs Y", "difference between X and Y"]
        r"^compare\s+(.+?)\s+and\s+(.+?)[\?\.]*$": [
            "{0} vs {1}",
            "difference between {0} and {1}",
            "{0} compared to {1}",
        ],
    }

    def __init__(
        self,
        llm_fn: Optional[Callable] = None,
        max_rewrites: int = 3,
        use_templates: bool = True,
    ):
        """
        Args:
            llm_fn: function(prompt) -> str for LLM-based rewriting
            max_rewrites: max number of rewrites to generate
            use_templates: whether to use template-based rewriting
        """
        self.llm_fn = llm_fn
        self.max_rewrites = max_rewrites
        self.use_templates = use_templates

    def rewrite(self, query: str) -> QueryRewriteResult:
        """Generate query rewrites using best available strategy."""
        query = query.strip()
        if not query:
            return QueryRewriteResult(original=query, strategy="passthrough")

        # Try LLM rewriting first
        if self.llm_fn:
            try:
                rewrites = self._llm_rewrite(query)
                if rewrites:
                    return QueryRewriteResult(
                        original=query,
                        rewrites=rewrites[:self.max_rewrites],
                        strategy="llm",
                    )
            except Exception as e:
                logger.warning(f"[QueryRewriter] LLM rewrite failed: {e}")

        # Fallback to templates
        if self.use_templates:
            rewrites = self._template_rewrite(query)
            if rewrites:
                return QueryRewriteResult(
                    original=query,
                    rewrites=rewrites[:self.max_rewrites],
                    strategy="template",
                )

        return QueryRewriteResult(original=query, strategy="passthrough")

    def _llm_rewrite(self, query: str) -> List[str]:
        """Use LLM to generate query variations."""
        prompt = (
            f"Generate {self.max_rewrites} alternative search queries for the following question. "
            f"Each should capture a different aspect or phrasing.\n\n"
            f"Original: {query}\n\n"
            f"Alternatives (one per line, no numbering):"
        )

        response = self.llm_fn(prompt)
        if not response:
            return []

        lines = [l.strip().lstrip("0123456789.-) ") for l in response.strip().split("\n")]
        return [l for l in lines if l and l.lower() != query.lower() and len(l) > 5]

    def _template_rewrite(self, query: str) -> List[str]:
        """Apply template-based query transformations."""
        rewrites = []
        query_lower = query.lower().strip()

        for pattern, templates in self.TEMPLATES.items():
            m = re.match(pattern, query_lower, re.IGNORECASE)
            if m:
                groups = m.groups()
                for tpl in templates:
                    try:
                        rewrite = tpl.format(*groups)
                        if rewrite.lower() != query_lower:
                            rewrites.append(rewrite)
                    except (IndexError, KeyError):
                        continue

        return rewrites

    @staticmethod
    def reciprocal_rank_fusion(
        result_lists: List[List[Dict[str, Any]]],
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """Merge multiple result lists using Reciprocal Rank Fusion.

        Args:
            result_lists: list of search result lists (each from a different query)
            k: RRF constant (default 60)

        Returns:
            Merged and re-scored list of results
        """
        scores: Dict[str, float] = {}
        items: Dict[str, Dict] = {}

        for results in result_lists:
            for rank, item in enumerate(results):
                text_key = item.get("text", "")[:100]  # Use first 100 chars as key
                rrf_score = 1.0 / (k + rank + 1)
                scores[text_key] = scores.get(text_key, 0.0) + rrf_score
                if text_key not in items:
                    items[text_key] = item

        # Sort by RRF score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [
            {**items[key], "fusion_score": score}
            for key, score in ranked
            if key in items
        ]
