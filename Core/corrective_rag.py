"""
Core/corrective_rag.py — Corrective RAG (CRAG) with Self-Healing Retrieval.

Industry best practice: When initial retrieval confidence is low,
automatically trigger corrective actions:
  1. Score retrieval quality
  2. If CORRECT: proceed normally
  3. If AMBIGUOUS: refine query and re-retrieve
  4. If INCORRECT: trigger alternative knowledge sources / web search

This implements the Corrective-RAG pattern (Yan et al. 2024) which
adds a lightweight retrieval evaluator that grades document relevance
before generation, preventing the LLM from generating answers based
on irrelevant or low-quality retrieved context.

References:
  - Yan et al. "Corrective Retrieval Augmented Generation" (2024)
  - Self-RAG: Asai et al. (2023)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RetrievalGrade(Enum):
    """Quality grade for retrieved documents."""
    CORRECT = "correct"
    AMBIGUOUS = "ambiguous"
    INCORRECT = "incorrect"


@dataclass
class CRAGResult:
    """Result of Corrective RAG pipeline."""

    answer: str = ""
    grade: RetrievalGrade = RetrievalGrade.CORRECT
    original_chunks: List[Dict[str, Any]] = field(default_factory=list)
    corrected_chunks: List[Dict[str, Any]] = field(default_factory=list)
    corrections_applied: List[str] = field(default_factory=list)
    confidence: float = 0.0
    iterations: int = 1


class CorrectiveRAG:
    """Self-healing RAG that evaluates and corrects retrieval quality.

    When retrieval is poor, CRAG doesn't just return bad results — it
    actively corrects the retrieval through query refinement, knowledge
    decomposition, or alternative source queries.

    Usage:
        crag = CorrectiveRAG(
            retrieve_fn=my_search,
            generate_fn=my_generate,
            llm_fn=my_llm,
        )
        result = crag.retrieve_and_generate(query, initial_chunks)
    """

    # Relevance scoring thresholds
    CORRECT_THRESHOLD = 0.65
    AMBIGUOUS_THRESHOLD = 0.35

    def __init__(
        self,
        retrieve_fn: Optional[Callable] = None,
        generate_fn: Optional[Callable] = None,
        llm_fn: Optional[Callable] = None,
        embed_fn: Optional[Callable] = None,
        max_corrections: int = 2,
    ):
        """
        Args:
            retrieve_fn: function(query, top_k) -> List[Dict]
            generate_fn: function(query, chunks) -> str
            llm_fn: function(prompt) -> str for evaluation/refinement
            embed_fn: function(text) -> List[float] for relevance scoring
            max_corrections: max correction attempts
        """
        self.retrieve_fn = retrieve_fn
        self.generate_fn = generate_fn
        self.llm_fn = llm_fn
        self.embed_fn = embed_fn
        self.max_corrections = max_corrections

    def retrieve_and_generate(
        self,
        query: str,
        initial_chunks: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
    ) -> CRAGResult:
        """Run the full CRAG pipeline: retrieve → evaluate → correct → generate."""
        if not self.generate_fn:
            return CRAGResult(answer="", grade=RetrievalGrade.INCORRECT)

        # Step 1: Get initial chunks
        chunks = list(initial_chunks or [])
        if not chunks and self.retrieve_fn:
            try:
                chunks = self.retrieve_fn(query, top_k)
            except Exception as e:
                logger.warning(f"[CRAG] Initial retrieval failed: {e}")

        result = CRAGResult(
            original_chunks=list(chunks),
            grade=RetrievalGrade.CORRECT,
        )

        # Step 2: Grade retrieved documents
        grade, confidence = self._grade_retrieval(query, chunks)
        result.grade = grade
        result.confidence = confidence

        # Step 3: Apply corrections based on grade
        corrected_chunks = chunks
        if grade == RetrievalGrade.CORRECT:
            logger.info(f"[CRAG] Retrieval grade: CORRECT ({confidence:.2f})")
            corrected_chunks = self._filter_relevant(query, chunks)
            result.corrections_applied.append("filtered_irrelevant")

        elif grade == RetrievalGrade.AMBIGUOUS:
            logger.info(f"[CRAG] Retrieval grade: AMBIGUOUS ({confidence:.2f}), refining...")
            corrected_chunks = self._correct_ambiguous(query, chunks, top_k)
            result.corrections_applied.append("query_refined")
            result.iterations += 1

        elif grade == RetrievalGrade.INCORRECT:
            logger.info(f"[CRAG] Retrieval grade: INCORRECT ({confidence:.2f}), correcting...")
            corrected_chunks = self._correct_incorrect(query, chunks, top_k)
            result.corrections_applied.append("knowledge_decomposition")
            result.iterations += 1

        result.corrected_chunks = corrected_chunks

        # Step 4: Generate answer with corrected context
        try:
            answer = self.generate_fn(query, corrected_chunks)
            result.answer = answer or ""
        except Exception as e:
            logger.warning(f"[CRAG] Generation failed: {e}")
            result.answer = ""

        return result

    def _grade_retrieval(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
    ) -> tuple[RetrievalGrade, float]:
        """Grade the quality of retrieved documents relative to the query.

        Uses a combination of:
          1. Keyword overlap scoring
          2. LLM-based relevance evaluation (if available)
          3. Score distribution analysis
        """
        if not chunks:
            return RetrievalGrade.INCORRECT, 0.0

        scores = []

        # Signal 1: Keyword overlap
        query_words = set(
            w.lower() for w in re.findall(r"\b\w{3,}\b", query)
        )
        for chunk in chunks:
            text = chunk.get("text", "").lower()
            chunk_words = set(re.findall(r"\b\w{3,}\b", text))
            if query_words:
                overlap = len(query_words & chunk_words) / len(query_words)
            else:
                overlap = 0.0
            scores.append(overlap)

        # Signal 2: Retrieval scores (if available)
        retrieval_scores = [
            chunk.get("score", 0.0) for chunk in chunks
            if chunk.get("score", 0.0) > 0
        ]

        # Signal 3: LLM-based evaluation (lightweight)
        llm_score = self._llm_grade(query, chunks[:3]) if self.llm_fn else None

        # Combine signals
        keyword_avg = sum(scores) / len(scores) if scores else 0.0
        retrieval_avg = sum(retrieval_scores) / len(retrieval_scores) if retrieval_scores else 0.5

        if llm_score is not None:
            combined = 0.3 * keyword_avg + 0.3 * retrieval_avg + 0.4 * llm_score
        else:
            combined = 0.5 * keyword_avg + 0.5 * retrieval_avg

        # Classify
        if combined >= self.CORRECT_THRESHOLD:
            return RetrievalGrade.CORRECT, combined
        elif combined >= self.AMBIGUOUS_THRESHOLD:
            return RetrievalGrade.AMBIGUOUS, combined
        else:
            return RetrievalGrade.INCORRECT, combined

    def _llm_grade(self, query: str, chunks: List[Dict[str, Any]]) -> Optional[float]:
        """Use LLM to grade retrieval relevance (lightweight prompt)."""
        try:
            context = "\n".join(
                c.get("text", "")[:200] for c in chunks[:3]
            )
            prompt = (
                f"Rate how relevant the following context is to answering the query.\n"
                f"Query: {query}\n"
                f"Context (first 3 chunks):\n{context}\n\n"
                f"Reply with only a number from 0 to 1 (e.g. 0.7):"
            )
            response = self.llm_fn(prompt)
            # Extract number from response
            match = re.search(r"(0\.\d+|1\.0|0|1)", response.strip())
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return None

    def _filter_relevant(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """For CORRECT grade: filter out clearly irrelevant chunks."""
        if not chunks:
            return chunks

        query_words = set(w.lower() for w in re.findall(r"\b\w{3,}\b", query))
        filtered = []

        for chunk in chunks:
            text = chunk.get("text", "").lower()
            chunk_words = set(re.findall(r"\b\w{3,}\b", text))
            overlap = len(query_words & chunk_words) / max(len(query_words), 1)

            # Keep chunks with any query word overlap, or high retrieval score
            if overlap > 0.1 or chunk.get("score", 0) > 0.5:
                filtered.append(chunk)

        return filtered if filtered else chunks

    def _correct_ambiguous(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """For AMBIGUOUS grade: refine query and re-retrieve.

        Strategy: Keep good chunks, supplement with refined query results.
        """
        good_chunks = self._filter_relevant(query, chunks)

        if not self.retrieve_fn:
            return good_chunks

        # Refine query using existing chunks as hints
        refined_query = self._refine_query(query, chunks)

        try:
            new_chunks = self.retrieve_fn(refined_query, top_k)
        except Exception as e:
            logger.warning(f"[CRAG] Refined retrieval failed: {e}")
            return good_chunks

        # Merge: good originals + new results
        seen = {c.get("text", "")[:100] for c in good_chunks}
        for c in new_chunks:
            if c.get("text", "")[:100] not in seen:
                good_chunks.append(c)
                seen.add(c.get("text", "")[:100])

        return good_chunks

    def _correct_incorrect(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """For INCORRECT grade: decompose query and search sub-questions.

        Strategy: Break complex query into simpler sub-queries,
        retrieve for each, and merge results.
        """
        sub_queries = self._decompose_query(query)

        if not sub_queries or not self.retrieve_fn:
            return chunks  # Fall back to original

        all_chunks: List[Dict[str, Any]] = []
        seen = set()

        for sub_q in sub_queries:
            try:
                results = self.retrieve_fn(sub_q, max(top_k // len(sub_queries), 3))
                for c in results:
                    text_key = c.get("text", "")[:100]
                    if text_key not in seen:
                        all_chunks.append(c)
                        seen.add(text_key)
            except Exception:
                continue

        return all_chunks if all_chunks else chunks

    def _refine_query(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """Refine query based on partial context from chunks."""
        if self.llm_fn:
            try:
                context_hint = " ".join(
                    c.get("text", "")[:100] for c in chunks[:2]
                )
                prompt = (
                    f"The following search query didn't get great results:\n"
                    f"Query: {query}\n"
                    f"Partial context found: {context_hint[:300]}\n\n"
                    f"Rewrite the query to be more specific and likely to find "
                    f"relevant information. Output only the refined query:"
                )
                refined = self.llm_fn(prompt)
                if refined and len(refined.strip()) > 5:
                    return refined.strip()[:200]
            except Exception:
                pass

        # Heuristic: add specificity markers
        if "?" in query:
            return query.replace("?", "") + " explanation details"
        return f"{query} detailed information"

    def _decompose_query(self, query: str) -> List[str]:
        """Decompose a complex query into simpler sub-queries."""
        if self.llm_fn:
            try:
                prompt = (
                    f"Break this question into 2-3 simpler sub-questions that "
                    f"together would answer the original:\n\n"
                    f"Question: {query}\n\n"
                    f"Sub-questions (one per line):"
                )
                response = self.llm_fn(prompt)
                if response:
                    lines = [
                        l.strip().lstrip("0123456789.-) ")
                        for l in response.strip().split("\n")
                    ]
                    sub_qs = [l for l in lines if l and len(l) > 10]
                    if sub_qs:
                        return sub_qs[:3]
            except Exception:
                pass

        # Heuristic decomposition
        sub_queries = [query]
        # If query has "and" → split
        if " and " in query.lower():
            parts = re.split(r"\s+and\s+", query, flags=re.IGNORECASE)
            sub_queries = [p.strip() for p in parts if len(p.strip()) > 10]

        return sub_queries[:3]
