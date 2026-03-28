"""
Core/query_rewriter.py — LLM-powered query expansion and multi-query generation.

Phase 1.3 improvement: Instead of searching with the raw user query only,
we generate 3-5 semantically diverse reformulations and merge the result sets
via Reciprocal Rank Fusion. This dramatically improves recall for:
  - Ambiguous queries ("it" / "this" / pronouns)
  - Multi-hop questions that benefit from decomposition
  - Non-native language queries with imprecise phrasing

Usage:
    rewriter = QueryRewriter(llm_adapter=my_llm)
    result = rewriter.rewrite("tell me about hospital beds")
    for q in result.all_queries:
        results_i = rag.hybrid_search(q, k=10)
    merged = rewriter.merge_results(per_query_results, top_k=5)
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# =============================================================================
# Template-based fallback (zero LLM cost)
# =============================================================================

_TEMPLATE_EXPANSIONS = {
    # Temporal → add recency / history
    r"\b(latest|current|recent|now)\b": [
        "{q} in {year}",
        "{q} updated",
        "most recent {q}",
    ],
    # How-to → procedural
    r"\bhow\s+to\b": [
        "steps to {rest}",
        "guide for {rest}",
        "tutorial {rest}",
    ],
    # What is → definition
    r"\bwhat\s+is\b": [
        "definition of {rest}",
        "explain {rest}",
        "{rest} meaning",
    ],
    # Compare
    r"\b(vs|versus|compare|difference)\b": [
        "comparison {q}",
        "pros and cons {q}",
        "{q} advantages disadvantages",
    ],
}

_CURRENT_YEAR = "2026"


def _template_rewrite(query: str) -> List[str]:
    """Fast template-based rewrite when no LLM is available."""
    rewrites = []
    q_lower = query.lower()
    for pattern, templates in _TEMPLATE_EXPANSIONS.items():
        if re.search(pattern, q_lower, re.I):
            rest = re.sub(pattern, "", query, flags=re.I).strip()
            for t in templates:
                rw = t.format(q=query, rest=rest or query, year=_CURRENT_YEAR).strip()
                if rw.lower() != query.lower():
                    rewrites.append(rw)
            break  # Apply only first matching pattern
    return rewrites[:3]


# =============================================================================
# Main QueryRewriter class
# =============================================================================


class QueryRewriter:
    """
    Generates diverse query reformulations via:
      1. LLM-based expansion (primary, highest recall boost)
      2. Template-based expansion (fast fallback)
      3. Passthrough (original query only, if all fails)

    Then merges multi-query results via Reciprocal Rank Fusion.
    """

    REWRITE_PROMPT = """You are a search query optimization expert.

Given the user query below, generate {n} diverse reformulations that:
- Use different vocabulary/synonyms
- Vary the specificity (one broader, one narrower)
- May decompose complex questions into simpler sub-questions
- Are each self-contained and searchable

User query: "{query}"

Respond with ONLY the reformulated queries, one per line (no numbering, no explanations).
Do not repeat the original query."""

    def __init__(
        self,
        llm_adapter: Any = None,
        n_rewrites: int = 3,
        timeout: float = 15.0,
    ):
        """
        Args:
            llm_adapter: Any LLM adapter with .generate(prompt) or .query_sync(prompt) method.
            n_rewrites: Number of reformulations to generate (default 3).
            timeout: Max seconds to wait for LLM response.
        """
        self.llm = llm_adapter
        self.n_rewrites = n_rewrites
        self.timeout = timeout

    def rewrite(self, query: str) -> "QueryRewriteResult":
        """
        Generate query reformulations.

        Returns QueryRewriteResult with .all_queries property for iteration.
        """
        from Core.rag_models import QueryRewriteResult

        if not query or not query.strip():
            return QueryRewriteResult(original=query, rewrites=[], strategy="passthrough")

        # Try LLM first
        if self.llm is not None:
            try:
                rewrites = self._llm_rewrite(query)
                if rewrites:
                    return QueryRewriteResult(
                        original=query,
                        rewrites=rewrites,
                        strategy="llm",
                    )
            except Exception as e:
                logger.warning(f"[QueryRewriter] LLM rewrite failed: {e}, falling back to templates.")

        # Template fallback
        rewrites = _template_rewrite(query)
        if rewrites:
            return QueryRewriteResult(original=query, rewrites=rewrites, strategy="template")

        # Passthrough
        return QueryRewriteResult(original=query, rewrites=[], strategy="passthrough")

    def _llm_rewrite(self, query: str) -> List[str]:
        """Call LLM to generate reformulations."""
        prompt = self.REWRITE_PROMPT.format(query=query, n=self.n_rewrites)
        response = ""

        # Try different LLM adapter interfaces
        if hasattr(self.llm, "query_sync"):
            response = self.llm.query_sync(prompt, max_tokens=200, temperature=0.7)
        elif hasattr(self.llm, "generate"):
            response = self.llm.generate(prompt)
        elif callable(self.llm):
            response = self.llm(prompt)

        if not response or not response.strip():
            return []

        # Parse: one query per line
        lines = [line.strip() for line in response.strip().split("\n")]
        rewrites = [
            line
            for line in lines
            if line
            and len(line) > 5
            and line.lower() != query.lower()
            and not line.startswith(("#", "-", "*", "•", "1.", "2.", "3."))  # Strip bullets
        ]
        # Strip leading bullets/numbers if any slipped through
        cleaned = []
        for r in rewrites:
            r = re.sub(r"^[\d]+[\.\)]\s*", "", r).strip()
            r = re.sub(r"^[-*•]\s*", "", r).strip()
            if r and r.lower() != query.lower():
                cleaned.append(r)

        return cleaned[: self.n_rewrites]

    # =========================================================================
    # Multi-query result merging (Reciprocal Rank Fusion)
    # =========================================================================

    @staticmethod
    def merge_results(
        per_query_results: List[List[Dict]],
        top_k: int = 5,
        rrf_k: int = 60,
    ) -> List[Dict]:
        """
        Merge multiple ranked result lists into one via Reciprocal Rank Fusion.

        Args:
            per_query_results: List of result lists (one per query variant).
            top_k: Final number of results to return.
            rrf_k: RRF smoothing constant (default 60, same as pipeline).

        Returns:
            Deduplicated, merged, and re-ranked result list.
        """
        if not per_query_results:
            return []

        # Build score map keyed by chunk text hash
        scores: Dict[str, float] = {}
        chunks_by_key: Dict[str, Dict] = {}

        for result_list in per_query_results:
            for rank, chunk in enumerate(result_list):
                text = chunk.get("text", "")
                if not text:
                    continue
                key = text[:200]  # Use first 200 chars as dedup key (fast)
                rrf_score = 1.0 / (rrf_k + rank + 1)
                scores[key] = scores.get(key, 0.0) + rrf_score
                if key not in chunks_by_key:
                    chunks_by_key[key] = chunk

        # Sort by fused score
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)

        results = []
        for key in sorted_keys[:top_k]:
            chunk = chunks_by_key[key].copy()
            chunk["_multi_query_rrf_score"] = scores[key]
            results.append(chunk)

        return results
