# -*- coding: utf-8 -*-
"""
zena_mode/query_processor.py — Intelligent Query Processing & Expansion
========================================================================

Adapted from RAG_RAT Core/query_processor.py for ZEN_AI_RAG.

Features:
  - Query normalisation & cleanup
  - Intent detection (factual / how-to / comparison / opinion / causal)
  - Short-query rewriting hints
  - Synonym-based query expansion (no LLM dependency)
  - Multi-query generation for comprehensive retrieval
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Intelligent query processing for better retrieval."""

    def __init__(self, *, expansion_enabled: bool = True, rewriting_enabled: bool = True) -> None:
        """Configure query expansion and rewriting toggles."""
        self.expansion_enabled = expansion_enabled
        self.rewriting_enabled = rewriting_enabled

    # ── public API ────────────────────────────────────────────────────────

    def process_query(self, query: str, *, expand: bool = True) -> Dict[str, Any]:
        """Process, normalise, classify, and optionally expand a user query.

        Returns
        -------
        dict
            ``original``, ``processed``, ``alternatives``, ``intent``
        """
        result: Dict[str, Any] = {
            "original": query,
            "processed": query,
            "alternatives": [],
            "intent": None,
        }

        processed = self._normalise(query)
        result["processed"] = processed
        result["intent"] = self._detect_intent(processed)

        # Rewrite short / very-long queries
        if self.rewriting_enabled and self._needs_rewriting(processed):
            rewritten = self._rewrite_query(processed)
            if rewritten:
                result["processed"] = rewritten
                logger.info("Rewrote query: '%s' → '%s'", query, rewritten)

        # Expand with synonym alternatives
        if expand and self.expansion_enabled:
            result["alternatives"] = self._expand_query(result["processed"])

        return result

    def generate_multi_queries(self, query: str, n: int = 3) -> List[str]:
        """Generate *n* related sub-queries for comprehensive retrieval."""
        queries: List[str] = [query]
        intent = self._detect_intent(query)

        q_lower = query.lower()
        if intent == "factual":
            base = re.sub(r"^what is\s+", "", q_lower, flags=re.I).strip()
            queries.append(f"What is the background of {base}?")
            queries.append(f"What are examples of {base}?")
        elif intent == "how-to":
            base = re.sub(r"^how to\s+", "", q_lower, flags=re.I).strip()
            queries.append(f"What do I need before {base}?")
            queries.append(f"What are common mistakes when {base}?")
        elif intent == "comparison":
            parts = re.split(r"\s+vs\.?\s+|\s+versus\s+", query, flags=re.I)
            if len(parts) == 2:
                queries.append(f"What is {parts[0].strip()}?")
                queries.append(f"What is {parts[1].strip()}?")
        else:
            # Generic expansion
            queries.append(f"{query} detailed explanation")
            queries.append(f"{query} examples")

        return queries[:n]

    # ── internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _normalise(query: str) -> str:
        """Remove extra whitespace and add ``?`` if it looks like a question."""
        query = re.sub(r"\s+", " ", query.strip())
        q_words = {
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
            "which",
            "can",
            "could",
            "would",
            "should",
            "is",
            "are",
            "does",
            "do",
        }
        first = query.lower().split()[0] if query.split() else ""
        if (first in q_words or query.endswith("?")) and not query.endswith("?"):
            query += "?"
        return query

    @staticmethod
    def _needs_rewriting(query: str) -> bool:
        """Return True if the query is too short or too long for good retrieval."""
        words = query.split()
        return len(words) < 3 or len(words) > 50

    @staticmethod
    def _rewrite_query(query: str) -> Optional[str]:
        """Heuristic rewriting (no LLM). Returns *None* if no improvement."""
        words = query.split()
        if len(words) < 3:
            return f"Please explain {query.rstrip('?')}?"
        if len(words) > 50:
            return " ".join(words[:40]) + "?"
        return None

    @staticmethod
    def _expand_query(query: str) -> List[str]:
        """Synonym-based expansion — returns up to 3 alternatives."""
        synonyms = {
            "what is": ["define", "explain", "describe"],
            "how to": ["steps to", "way to", "method to"],
            "why": ["reason for", "cause of", "explanation for"],
            "when": ["time of", "date of", "period of"],
            "where": ["location of", "place of", "position of"],
        }
        q_lower = query.lower()
        alts: List[str] = []
        for phrase, replacements in synonyms.items():
            if phrase not in q_lower:
                continue
            for r in replacements:
                alts.append(q_lower.replace(phrase, r).capitalize())
        return alts[:3]

    @staticmethod
    def _detect_intent(query: str) -> str:
        """Classify the query intent (factual, how-to, comparison, etc.)."""
        q = query.lower()
        if any(w in q for w in ("what", "when", "where", "who", "define", "explain")):
            return "factual"
        if "how" in q or "steps" in q:
            return "how-to"
        if any(w in q for w in ("compare", "difference", "vs", "versus", "better")):
            return "comparison"
        if any(w in q for w in ("should", "recommend", "best", "opinion")):
            return "opinion"
        if "why" in q or "reason" in q:
            return "causal"
        return "general"


# ── singleton ─────────────────────────────────────────────────────────────

_instance: Optional[QueryProcessor] = None


def get_query_processor() -> QueryProcessor:
    """Return the global :class:`QueryProcessor` singleton."""
    global _instance
    if _instance is None:
        _instance = QueryProcessor()
    return _instance
