"""
Core/flare_retrieval.py — Forward-Looking Active Retrieval (FLARE).

Iterative retrieval strategy:
  1. Generate initial answer
  2. Detect uncertain spans (low-confidence tokens)
  3. Formulate targeted sub-queries for uncertain parts
  4. Re-retrieve and merge new context
  5. Regenerate with enriched context

Ported from ZEN_RAG.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FLAREResult:
    """Result of a FLARE retrieval round."""

    final_answer: str
    iterations: int = 0
    sub_queries: List[str] = field(default_factory=list)
    total_chunks_retrieved: int = 0
    confidence_improved: bool = False


class FLARERetriever:
    """Forward-Looking Active Retrieval for iterative query refinement.

    Usage:
        flare = FLARERetriever(
            retrieve_fn=my_search,
            generate_fn=my_llm_generate,
        )
        result = flare.retrieve_and_generate(query, initial_chunks)
    """

    # Uncertainty markers in LLM output
    UNCERTAINTY_PATTERNS = [
        re.compile(r"\b(possibly|perhaps|maybe|might|could|approximately|roughly|about|around)\b", re.I),
        re.compile(r"\b(not\s+(?:entirely\s+)?(?:sure|certain|clear)|unclear|uncertain|unknown)\b", re.I),
        re.compile(r"\b(it\s+(?:is|seems?)\s+(?:likely|possible|probable))\b", re.I),
        re.compile(r"\b(some\s+sources?\s+(?:say|suggest|indicate|claim))\b", re.I),
        re.compile(r"\b(estimated|approximate|roughly|circa)\b", re.I),
    ]

    def __init__(
        self,
        retrieve_fn: Optional[Callable] = None,
        generate_fn: Optional[Callable] = None,
        max_iterations: int = 3,
        uncertainty_threshold: float = 0.3,
    ):
        """
        Args:
            retrieve_fn: function(query) -> List[Dict] (search chunks)
            generate_fn: function(query, context_chunks) -> str (LLM generate)
            max_iterations: maximum FLARE iterations
            uncertainty_threshold: sentence uncertainty ratio to trigger re-retrieval
        """
        self.retrieve_fn = retrieve_fn
        self.generate_fn = generate_fn
        self.max_iterations = max_iterations
        self.uncertainty_threshold = uncertainty_threshold

    def retrieve_and_generate(
        self,
        query: str,
        initial_chunks: Optional[List[Dict]] = None,
    ) -> FLAREResult:
        """Run FLARE: generate → detect uncertainty → re-retrieve → regenerate."""
        if not self.generate_fn:
            return FLAREResult(final_answer="", iterations=0)

        chunks = list(initial_chunks or [])
        result = FLAREResult(final_answer="", total_chunks_retrieved=len(chunks))

        for iteration in range(self.max_iterations):
            # Generate with current context
            answer = self._generate(query, chunks)
            if not answer:
                break

            # Detect uncertain spans
            uncertain_spans = self._detect_uncertainty(answer)

            if not uncertain_spans or iteration == self.max_iterations - 1:
                result.final_answer = answer
                result.iterations = iteration + 1
                result.confidence_improved = iteration > 0
                break

            # Formulate sub-queries for uncertain spans
            sub_queries = self._formulate_sub_queries(query, uncertain_spans)
            result.sub_queries.extend(sub_queries)

            # Re-retrieve with sub-queries
            new_chunks = self._retrieve_additional(sub_queries)
            if not new_chunks:
                result.final_answer = answer
                result.iterations = iteration + 1
                break

            # Merge new chunks (dedup by text hash)
            existing_texts = {c.get("text", "")[:100] for c in chunks}
            for c in new_chunks:
                if c.get("text", "")[:100] not in existing_texts:
                    chunks.append(c)
                    existing_texts.add(c.get("text", "")[:100])
                    result.total_chunks_retrieved += 1

            result.iterations = iteration + 1

        if not result.final_answer and chunks:
            result.final_answer = self._generate(query, chunks) or ""

        return result

    def _generate(self, query: str, chunks: List[Dict]) -> str:
        """Generate answer using LLM."""
        try:
            return self.generate_fn(query, chunks)
        except Exception as e:
            logger.warning(f"[FLARE] Generation failed: {e}")
            return ""

    def _detect_uncertainty(self, text: str) -> List[str]:
        """Detect uncertain sentences in generated text."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        uncertain = []

        for sentence in sentences:
            uncertainty_count = sum(
                1 for p in self.UNCERTAINTY_PATTERNS if p.search(sentence)
            )
            words = len(sentence.split())
            if words > 0 and uncertainty_count / max(words, 1) > 0.02:
                uncertain.append(sentence)

        # Also flag very short/vague sentences
        for sentence in sentences:
            if len(sentence.split()) < 5 and any(
                w in sentence.lower() for w in ("unclear", "unknown", "varies")
            ):
                if sentence not in uncertain:
                    uncertain.append(sentence)

        return uncertain

    def _formulate_sub_queries(self, original_query: str, uncertain_spans: List[str]) -> List[str]:
        """Create targeted sub-queries from uncertain spans."""
        sub_queries = []

        for span in uncertain_spans[:3]:  # Limit to 3 sub-queries
            # Extract key nouns/phrases from the uncertain span
            key_words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", span)
            if not key_words:
                key_words = [w for w in re.findall(r"\b\w{4,}\b", span)
                             if w.lower() not in {"possibly", "perhaps", "maybe", "could", "might",
                                                   "approximately", "roughly", "about", "around",
                                                   "unclear", "uncertain", "unknown"}]

            if key_words:
                sub_query = f"{original_query} specifically {' '.join(key_words[:3])}"
                sub_queries.append(sub_query)

        return sub_queries

    def _retrieve_additional(self, sub_queries: List[str]) -> List[Dict]:
        """Retrieve additional chunks for sub-queries."""
        if not self.retrieve_fn:
            return []

        all_chunks = []
        for sq in sub_queries:
            try:
                chunks = self.retrieve_fn(sq)
                if chunks:
                    all_chunks.extend(chunks[:3])  # Top 3 per sub-query
            except Exception as e:
                logger.warning(f"[FLARE] Sub-query retrieval failed: {e}")

        return all_chunks
