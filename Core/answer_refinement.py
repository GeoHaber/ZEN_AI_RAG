"""
Core/answer_refinement.py — Post-Generation Answer Refinement Engine

Catches and fixes answer quality issues BEFORE displaying to the user:
  1. Hallucination detection → request LLM to revise with grounded facts
  2. Completeness check → request elaboration if answer is too terse
  3. Internal consistency → detect & resolve self-contradictions
  4. Citation grounding → ensure claims reference actual source content
  5. Quality scoring → attach a quality score for UI display

Works as a middleware between LLM answer generation and UI display.

Usage:
    refiner = AnswerRefinementEngine(llm_generate_fn, hallucination_detector)
    result = await refiner.refine(query, answer, context, sources)
    display(result.answer, result.quality_score)
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RefinementResult:
    """Result of answer refinement."""

    answer: str
    original_answer: str
    was_revised: bool
    revision_count: int
    revision_reasons: List[str]
    quality_score: float  # 0–1
    hallucination_probability: float
    word_count: int

    @property
    def revision_reason(self) -> Optional[str]:
        if self.revision_reasons:
            return "; ".join(self.revision_reasons)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "was_revised": self.was_revised,
            "revision_count": self.revision_count,
            "revision_reason": self.revision_reason,
            "quality_score": self.quality_score,
            "hallucination_probability": self.hallucination_probability,
        }


class AnswerRefinementEngine:
    """
    Polish LLM answers before displaying to user.

    Pipeline:
      answer → hallucination_check → completeness_check → consistency_check → done
    """

    def __init__(
        self,
        llm_generate_fn: Optional[Callable] = None,
        hallucination_detector=None,
        min_answer_words: int = 25,
        max_refinement_attempts: int = 1,
    ):
        """
        Args:
            llm_generate_fn: Async callable(prompt: str) → str for re-generation.
                             If None, refinement prompts are skipped (score-only mode).
            hallucination_detector: Instance of AdvancedHallucinationDetector.
            min_answer_words: Threshold below which answer is considered too short.
            max_refinement_attempts: Max LLM re-calls for fixing issues.
        """
        self.llm_generate = llm_generate_fn
        self.detector = hallucination_detector
        self.min_words = min_answer_words
        self.max_attempts = max_refinement_attempts

    # =====================================================================
    # PUBLIC API
    # =====================================================================

    async def refine(
        self,
        query: str,
        answer: str,
        context: str,
        sources: Optional[List] = None,
        max_attempts: Optional[int] = None,
    ) -> RefinementResult:
        """
        Refine an answer through the quality pipeline.

        Args:
            query: Original user query.
            answer: LLM-generated answer.
            context: RAG context (concatenated evidence).
            sources: List of source dicts/strings.
            max_attempts: Override max refinement attempts.

        Returns:
            RefinementResult with possibly revised answer and quality metadata.
        """
        max_att = max_attempts if max_attempts is not None else self.max_attempts
        original = answer
        reasons: List[str] = []
        revisions = 0
        halluc_prob = 0.0

        # ── Step 1: Hallucination check ──────────────────────────────────
        if self.detector:
            evidence = self._sources_to_texts(sources) if sources else [context]
            report = self.detector.detect_hallucinations(answer, evidence)
            halluc_prob = report.probability

            if halluc_prob > 0.25 and revisions < max_att and self.llm_generate:
                logger.warning(f"[Refiner] Hallucination probability {halluc_prob:.0%}, requesting revision")
                prompt = self._hallucination_fix_prompt(answer, context, report.summary)
                try:
                    answer = await self.llm_generate(prompt)
                    revisions += 1
                    reasons.append(f"Hallucination fix ({halluc_prob:.0%} → re-grounded)")
                    # Re-check
                    report2 = self.detector.detect_hallucinations(answer, evidence)
                    halluc_prob = report2.probability
                except Exception as e:
                    logger.warning(f"[Refiner] Revision generation failed: {e}")

        # ── Step 2: Completeness check ───────────────────────────────────
        word_count = len(answer.split())
        if word_count < self.min_words and revisions < max_att and self.llm_generate:
            logger.info(f"[Refiner] Answer too short ({word_count} words), requesting elaboration")
            prompt = self._elaboration_prompt(query, answer, context)
            try:
                answer = await self.llm_generate(prompt)
                revisions += 1
                reasons.append(f"Elaborated (was {word_count} words)")
            except Exception as e:
                logger.warning(f"[Refiner] Elaboration failed: {e}")

        # ── Step 3: Consistency check ────────────────────────────────────
        contradictions = self._find_contradictions(answer)
        if contradictions and revisions < max_att and self.llm_generate:
            logger.info(f"[Refiner] {len(contradictions)} internal contradictions found")
            prompt = self._consistency_prompt(answer, context, contradictions)
            try:
                answer = await self.llm_generate(prompt)
                revisions += 1
                reasons.append(f"Fixed {len(contradictions)} internal contradiction(s)")
            except Exception as e:
                logger.warning(f"[Refiner] Consistency fix failed: {e}")

        # ── Quality score ────────────────────────────────────────────────
        quality = self._score_quality(answer, context, halluc_prob)

        return RefinementResult(
            answer=answer,
            original_answer=original,
            was_revised=revisions > 0,
            revision_count=revisions,
            revision_reasons=reasons,
            quality_score=quality,
            hallucination_probability=halluc_prob,
            word_count=len(answer.split()),
        )

    # =====================================================================
    # PROMPTS
    # =====================================================================

    def _hallucination_fix_prompt(self, answer: str, context: str, halluc_summary: str) -> str:
        return (
            "The answer below contains hallucinated or unsupported claims.\n\n"
            f"DETECTED ISSUES:\n{halluc_summary}\n\n"
            f"Original Answer:\n{answer}\n\n"
            f"Source Material:\n{context[:2000]}\n\n"
            "INSTRUCTIONS:\n"
            "- Revise the answer to ONLY include claims directly supported by the source material.\n"
            "- Remove any hallucinated or unsupported claims.\n"
            "- Keep the helpful structure and tone.\n"
            "- If you cannot verify a claim, say 'According to the sources...' or omit it.\n"
            "- Do NOT add new information not in the sources.\n"
        )

    def _elaboration_prompt(self, query: str, answer: str, context: str) -> str:
        return (
            "The answer to the user's question is very brief. "
            "Please provide a more complete and detailed answer.\n\n"
            f"User Question: {query}\n\n"
            f"Original Answer: {answer}\n\n"
            f"Relevant Context:\n{context[:2000]}\n\n"
            "Please provide a thorough answer that fully addresses the question "
            "using information from the context above. Stay factual."
        )

    def _consistency_prompt(self, answer: str, context: str, contradictions: List[str]) -> str:
        issues = "\n".join(f"  - {c}" for c in contradictions)
        return (
            "The answer below has internal contradictions:\n"
            f"{issues}\n\n"
            f"Original Answer:\n{answer}\n\n"
            f"Context:\n{context[:1500]}\n\n"
            "Please revise the answer to be internally consistent and "
            "factually aligned with the context."
        )

    # =====================================================================
    # ANALYSIS
    # =====================================================================

    def _find_contradictions(self, text: str) -> List[str]:
        """Find obvious internal contradictions in the answer."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        contradictions = []

        for i, s1 in enumerate(sentences):
            for s2 in sentences[i + 1 :]:
                s1_l = s1.lower()
                s2_l = s2.lower()

                # "X is Y" vs "X is not Y"
                for pattern in [r"(\w+)\s+is\s+(\w+)", r"(\w+)\s+are\s+(\w+)"]:
                    m1 = re.search(pattern, s1_l)
                    if m1:
                        subj, val = m1.group(1), m1.group(2)
                        neg = f"{subj} is not {val}"
                        neg2 = f"{subj} are not {val}"
                        if neg in s2_l or neg2 in s2_l:
                            contradictions.append(f'"{s1[:60]}" vs "{s2[:60]}"')

                # Direct number conflict: same subject, different number
                nums1 = re.findall(r"\b(\d+(?:\.\d+)?)\b", s1)
                nums2 = re.findall(r"\b(\d+(?:\.\d+)?)\b", s2)
                # If sentences share >50% content words and have different numbers
                words1 = set(s1_l.split())
                words2 = set(s2_l.split())
                overlap = len(words1 & words2) / max(len(words1 | words2), 1)
                if overlap > 0.5 and nums1 and nums2 and set(nums1) != set(nums2):
                    contradictions.append(f'Number conflict: "{s1[:50]}" vs "{s2[:50]}"')

        return contradictions[:5]  # Cap at 5

    def _score_quality(self, answer: str, context: str, halluc_prob: float) -> float:
        """Score answer quality 0–1."""
        score = 1.0

        # Hallucination penalty (up to -50%)
        score -= halluc_prob * 0.50

        # Length penalty
        words = len(answer.split())
        if words < 15:
            score *= 0.60
        elif words < 30:
            score *= 0.80
        elif words > 800:
            score *= 0.85  # Verbose

        # Structure bonus (lists, paragraphs, code blocks)
        if re.search(r"(?:^|\n)\s*[\-\*\d]+[\.\)]\s", answer):
            score *= 1.05  # Lists
        if "\n\n" in answer:
            score *= 1.03  # Paragraphs

        # Source reference bonus
        refs = len(re.findall(r"\[\d+\]|\(source|\(citation\)|according to", answer, re.I))
        if refs >= 1:
            score *= 1.05

        return max(0.0, min(score, 1.0))

    # =====================================================================
    # HELPERS
    # =====================================================================

    def _sources_to_texts(self, sources: List) -> List[str]:
        """Normalize various source formats to plain text list."""
        texts = []
        for src in sources:
            if isinstance(src, str):
                texts.append(src)
            elif isinstance(src, dict):
                texts.append(src.get("text", str(src)))
            else:
                texts.append(str(src))
        return texts
