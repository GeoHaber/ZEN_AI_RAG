"""
Core/answer_refinement.py — Post-Generation Quality Pipeline.

Stages:
  1. Hallucination fix (detect → regenerate flagged claims)
  2. Completeness check (ensure all query aspects addressed)
  3. Consistency check (internal contradictions)
  4. Quality scoring (overall quality assessment)

Ported from ZEN_RAG.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RefinementResult:
    """Result of the answer refinement pipeline."""

    original_answer: str
    refined_answer: str
    was_refined: bool = False
    quality_score: float = 0.0
    hallucination_probability: float = 0.0
    completeness_score: float = 0.0
    stages_applied: List[str] = field(default_factory=list)
    refinement_notes: List[str] = field(default_factory=list)


class AnswerRefinementEngine:
    """Post-generation quality pipeline for RAG answers.

    Usage:
        engine = AnswerRefinementEngine(llm_fn=my_llm_generate)
        result = await engine.refine(answer, query, source_chunks)
        if result.was_refined:
            use result.refined_answer
    """

    def __init__(
        self,
        llm_fn: Optional[Callable] = None,
        max_refinement_rounds: int = 2,
        quality_threshold: float = 0.7,
    ):
        """
        Args:
            llm_fn: async or sync function(prompt, system_prompt=None) -> str
            max_refinement_rounds: max refinement iterations
            quality_threshold: minimum quality score to accept
        """
        self.llm_fn = llm_fn
        self.max_rounds = max_refinement_rounds
        self.quality_threshold = quality_threshold
        self._hallucination_detector = None

    @property
    def hallucination_detector(self):
        if self._hallucination_detector is None:
            try:
                from Core.hallucination_detector_v2 import AdvancedHallucinationDetector
                self._hallucination_detector = AdvancedHallucinationDetector()
            except Exception as e:
                logger.warning(f"[Refinement] Hallucination detector not available: {e}")
        return self._hallucination_detector

    async def refine(
        self,
        answer: str,
        query: str,
        source_chunks: List[Dict[str, Any]],
    ) -> RefinementResult:
        """Run the full refinement pipeline."""
        result = RefinementResult(
            original_answer=answer,
            refined_answer=answer,
        )

        if not answer or not source_chunks:
            return result

        current = answer

        # Stage 1: Hallucination detection & fix
        current, halluc_prob = await self._stage_hallucination_fix(current, query, source_chunks)
        result.hallucination_probability = halluc_prob
        if current != answer:
            result.stages_applied.append("hallucination_fix")
            result.refinement_notes.append(f"Hallucination probability: {halluc_prob:.0%}")

        # Stage 2: Completeness check
        completeness = self._stage_completeness_check(current, query, source_chunks)
        result.completeness_score = completeness
        if completeness < 0.6 and self.llm_fn:
            enhanced = await self._enhance_completeness(current, query, source_chunks)
            if enhanced and len(enhanced) > len(current):
                current = enhanced
                result.stages_applied.append("completeness_enhancement")

        # Stage 3: Consistency check
        inconsistencies = self._stage_consistency_check(current)
        if inconsistencies:
            result.refinement_notes.extend(inconsistencies)
            result.stages_applied.append("consistency_flagged")

        # Stage 4: Quality score
        result.quality_score = self._compute_quality_score(
            current, query, source_chunks, halluc_prob, completeness
        )

        result.refined_answer = current
        result.was_refined = current != answer

        return result

    # ─── Stage 1: Hallucination Fix ────────────────────────────────────────

    async def _stage_hallucination_fix(
        self,
        answer: str,
        query: str,
        source_chunks: List[Dict],
    ) -> tuple:
        """Detect hallucinations and attempt to fix via LLM re-generation."""
        detector = self.hallucination_detector
        if not detector:
            return answer, 0.0

        report = detector.detect(answer, source_chunks, query)

        if report.is_clean:
            return answer, report.probability

        if not self.llm_fn:
            return answer, report.probability

        # Build a corrective prompt
        flagged_text = "\n".join(f"- {c.claim}" for c in report.flagged_claims[:5])
        sources_text = "\n".join(c.get("text", "")[:300] for c in source_chunks[:3])

        prompt = (
            f"The following answer has potential hallucinations:\n\n"
            f"ANSWER: {answer}\n\n"
            f"FLAGGED CLAIMS:\n{flagged_text}\n\n"
            f"VERIFIED SOURCES:\n{sources_text}\n\n"
            f"QUESTION: {query}\n\n"
            f"Rewrite the answer using ONLY information from the verified sources. "
            f"Remove or correct any flagged claims. Keep the same structure and tone."
        )

        try:
            if asyncio.iscoroutinefunction(self.llm_fn):
                refined = await self.llm_fn(prompt)
            else:
                refined = self.llm_fn(prompt)

            if refined and len(refined) > 20:
                return refined, report.probability
        except Exception as e:
            logger.warning(f"[Refinement] LLM re-generation failed: {e}")

        return answer, report.probability

    # ─── Stage 2: Completeness Check ───────────────────────────────────────

    @staticmethod
    def _stage_completeness_check(
        answer: str,
        query: str,
        source_chunks: List[Dict],
    ) -> float:
        """Check how well the answer addresses the query."""
        # Extract keywords from query
        query_words = set(re.findall(r"\b\w{4,}\b", query.lower()))
        if not query_words:
            return 1.0

        answer_lower = answer.lower()
        covered = sum(1 for w in query_words if w in answer_lower)
        return covered / len(query_words)

    async def _enhance_completeness(
        self,
        answer: str,
        query: str,
        source_chunks: List[Dict],
    ) -> Optional[str]:
        """Use LLM to enhance an incomplete answer."""
        if not self.llm_fn:
            return None

        sources_text = "\n".join(c.get("text", "")[:300] for c in source_chunks[:3])
        prompt = (
            f"The following answer may be incomplete:\n\n"
            f"QUESTION: {query}\n"
            f"CURRENT ANSWER: {answer}\n\n"
            f"AVAILABLE SOURCES:\n{sources_text}\n\n"
            f"Enhance the answer to fully address the question using the sources. "
            f"Keep what's already correct and add missing information."
        )

        try:
            if asyncio.iscoroutinefunction(self.llm_fn):
                return await self.llm_fn(prompt)
            else:
                return self.llm_fn(prompt)
        except Exception as e:
            logger.warning(f"[Refinement] Completeness enhancement failed: {e}")
            return None

    # ─── Stage 3: Consistency Check ────────────────────────────────────────

    @staticmethod
    def _stage_consistency_check(answer: str) -> List[str]:
        """Check for internal contradictions in the answer."""
        issues = []
        sentences = re.split(r"(?<=[.!?])\s+", answer)

        for i, s1 in enumerate(sentences):
            for s2 in sentences[i + 1:]:
                # Simple negation check
                s1_lower = s1.lower()
                s2_lower = s2.lower()

                # Check for "X is Y" vs "X is not Y"
                for pattern in [r"(\w+)\s+is\s+(\w+)", r"(\w+)\s+are\s+(\w+)"]:
                    m1 = re.search(pattern, s1_lower)
                    if m1:
                        negated = f"{m1.group(1)} is not {m1.group(2)}"
                        if negated in s2_lower:
                            issues.append(f"Internal contradiction: '{s1[:50]}' vs '{s2[:50]}'")
                            break

        return issues

    # ─── Stage 4: Quality Score ────────────────────────────────────────────

    @staticmethod
    def _compute_quality_score(
        answer: str,
        query: str,
        source_chunks: List[Dict],
        hallucination_prob: float,
        completeness: float,
    ) -> float:
        """Compute overall quality score [0-1]."""
        # Base: inverse of hallucination probability (weight 40%)
        halluc_score = max(0, 1.0 - hallucination_prob)

        # Completeness (weight 30%)
        complete_score = completeness

        # Length appropriateness (weight 15%)
        word_count = len(answer.split())
        if 20 <= word_count <= 300:
            length_score = 1.0
        elif word_count < 20:
            length_score = 0.5
        else:
            length_score = max(0.3, 1.0 - (word_count - 300) / 500)

        # Source coverage (weight 15%)
        if source_chunks:
            source_text = " ".join(c.get("text", "").lower() for c in source_chunks[:3])
            answer_words = set(re.findall(r"\b\w{4,}\b", answer.lower()))
            source_words = set(re.findall(r"\b\w{4,}\b", source_text))
            if answer_words:
                source_score = len(answer_words & source_words) / len(answer_words)
            else:
                source_score = 0.5
        else:
            source_score = 0.5

        return (
            halluc_score * 0.40
            + complete_score * 0.30
            + length_score * 0.15
            + source_score * 0.15
        )
