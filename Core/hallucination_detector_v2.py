"""
Core/hallucination_detector_v2.py — Multi-Signal Hallucination Detector.

Detection signals:
  1. Ungrounded claims (keyword coverage < 30%)
  2. NLI contradiction (cross-encoder deberta-v3)
  3. Numerical inconsistency (numbers in answer vs sources)
  4. Causal hallucination (causal claims without evidence)
  5. Reasoning gaps (conditional premises not in sources)

Ported from ZEN_RAG.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ClaimCheck:
    """Result of checking a single claim."""

    claim: str
    hallucination_type: str  # "ungrounded", "contradiction", "numerical", "causal", "reasoning"
    confidence: float = 0.0
    evidence: str = ""


@dataclass
class HallucinationReport:
    """Full hallucination analysis of an answer."""

    flagged_claims: List[ClaimCheck] = field(default_factory=list)
    total_claims: int = 0
    probability: float = 0.0
    summary: str = ""
    by_type: Dict[str, List[str]] = field(default_factory=dict)

    @property
    def is_clean(self) -> bool:
        return self.probability < 0.20


class AdvancedHallucinationDetector:
    """Multi-signal hallucination detector for RAG answers.

    Usage:
        detector = AdvancedHallucinationDetector()
        report = detector.detect(answer, source_chunks)
        if not report.is_clean:
            # Flag or refine the answer
    """

    # NLI model for contradiction detection
    _NLI_MODEL_NAME = "cross-encoder/nli-deberta-v3-small"

    def __init__(self, nli_threshold: float = 0.70):
        self.nli_threshold = nli_threshold
        self._nli_model = None

    @property
    def nli_model(self):
        if self._nli_model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._nli_model = CrossEncoder(self._NLI_MODEL_NAME)
                logger.info(f"[HallucinationDetector] Loaded NLI model: {self._NLI_MODEL_NAME}")
            except Exception as e:
                logger.warning(f"[HallucinationDetector] NLI model not available: {e}")
        return self._nli_model

    def detect(
        self,
        answer: str,
        source_chunks: List[Dict[str, Any]],
        query: Optional[str] = None,
    ) -> HallucinationReport:
        """Run all hallucination signals on an answer."""
        if not answer or not source_chunks:
            return HallucinationReport(summary="No answer or sources to check")

        claims = self._extract_claims(answer)
        if not claims:
            return HallucinationReport(summary="No verifiable claims found")

        evidence_text = " ".join(c.get("text", "") for c in source_chunks)
        flagged: List[ClaimCheck] = []
        by_type: Dict[str, List[str]] = {
            "ungrounded": [],
            "contradiction": [],
            "numerical": [],
            "causal": [],
            "reasoning": [],
        }

        for claim in claims:
            # Signal 1: Ungrounded
            if self._is_ungrounded(claim, evidence_text):
                check = ClaimCheck(claim=claim, hallucination_type="ungrounded", confidence=0.7)
                flagged.append(check)
                by_type["ungrounded"].append(claim)
                continue

            # Signal 2: NLI contradiction
            nli_result = self._check_nli_contradiction(claim, source_chunks)
            if nli_result:
                flagged.append(nli_result)
                by_type["contradiction"].append(claim)
                continue

            # Signal 3: Numerical inconsistency
            if self._check_numerical(claim, evidence_text):
                check = ClaimCheck(claim=claim, hallucination_type="numerical", confidence=0.8)
                flagged.append(check)
                by_type["numerical"].append(claim)
                continue

            # Signal 4: Causal hallucination
            if self._check_causal(claim, evidence_text):
                check = ClaimCheck(claim=claim, hallucination_type="causal", confidence=0.6)
                flagged.append(check)
                by_type["causal"].append(claim)
                continue

            # Signal 5: Reasoning gap
            if self._check_reasoning(claim, evidence_text):
                check = ClaimCheck(claim=claim, hallucination_type="reasoning", confidence=0.5)
                flagged.append(check)
                by_type["reasoning"].append(claim)

        total = len(claims)
        probability = len(flagged) / total if total > 0 else 0.0
        summary = self._build_summary(by_type, probability, total)

        return HallucinationReport(
            flagged_claims=flagged,
            total_claims=total,
            probability=probability,
            summary=summary,
            by_type=by_type,
        )

    # ─── Claim Extraction ──────────────────────────────────────────────────

    @staticmethod
    def _extract_claims(text: str) -> List[str]:
        """Split answer into individual claims/sentences."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        claims = []
        for s in sentences:
            s = s.strip()
            if len(s) > 15 and not s.startswith(("Note:", "Disclaimer:", "Source:")):
                claims.append(s)
        return claims

    # ─── Signal 1: Ungrounded Claims ───────────────────────────────────────

    @staticmethod
    def _is_ungrounded(claim: str, evidence: str) -> bool:
        """Check if < 30% of content words appear in evidence."""
        stopwords = frozenset({
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "and", "or", "but", "if",
            "then", "than", "that", "this", "it", "its", "not", "no", "so",
            "very", "also", "just", "more", "most", "such", "other", "which",
            "who", "what", "when", "where", "how", "all", "any", "both", "each",
        })

        content_words = [w for w in re.findall(r"\b\w+\b", claim.lower())
                         if w not in stopwords and len(w) > 2]
        if len(content_words) < 3:
            return False

        evidence_lower = evidence.lower()
        found = sum(1 for w in content_words if w in evidence_lower)
        coverage = found / len(content_words)
        return coverage < 0.30

    # ─── Signal 2: NLI Contradiction ───────────────────────────────────────

    def _check_nli_contradiction(
        self,
        claim: str,
        source_chunks: List[Dict],
    ) -> Optional[ClaimCheck]:
        """Use NLI cross-encoder to detect contradictions."""
        if not self.nli_model:
            return None

        try:
            for chunk in source_chunks[:5]:
                text = chunk.get("text", "")
                if not text:
                    continue

                # NLI scores: [contradiction, entailment, neutral]
                scores = self.nli_model.predict([(text, claim)])
                if hasattr(scores, "__len__") and len(scores) > 0:
                    score = scores[0]
                    # Handle both single-value and multi-class outputs
                    if hasattr(score, "__len__") and len(score) >= 3:
                        contradiction_score = float(score[0])
                        if contradiction_score > self.nli_threshold:
                            return ClaimCheck(
                                claim=claim,
                                hallucination_type="contradiction",
                                confidence=contradiction_score,
                                evidence=text[:200],
                            )
        except Exception as e:
            logger.debug(f"[HallucinationDetector] NLI check error: {e}")

        return None

    # ─── Signal 3: Numerical Inconsistency ─────────────────────────────────

    @staticmethod
    def _check_numerical(claim: str, evidence: str) -> bool:
        """Check if numbers in claim appear in evidence."""
        claim_nums = set(re.findall(r"\b\d+\.?\d*%?\b", claim))
        if not claim_nums:
            return False

        evidence_nums = set(re.findall(r"\b\d+\.?\d*%?\b", evidence))
        unmatched = claim_nums - evidence_nums

        # If >50% of numbers in the claim don't appear in evidence
        if len(unmatched) > len(claim_nums) * 0.5:
            return True
        return False

    # ─── Signal 4: Causal Hallucination ────────────────────────────────────

    @staticmethod
    def _check_causal(claim: str, evidence: str) -> bool:
        """Check if causal claims have evidence support."""
        causal_patterns = [
            r"\b(because|caused?\s+by|leads?\s+to|results?\s+in|due\s+to)\b",
            r"\b(therefore|consequently|as\s+a\s+result|hence)\b",
        ]

        claim_has_causal = any(re.search(p, claim, re.IGNORECASE) for p in causal_patterns)
        if not claim_has_causal:
            return False

        evidence_has_causal = any(re.search(p, evidence, re.IGNORECASE) for p in causal_patterns)
        return not evidence_has_causal

    # ─── Signal 5: Reasoning Gap ───────────────────────────────────────────

    @staticmethod
    def _check_reasoning(claim: str, evidence: str) -> bool:
        """Check if conditional/reasoning premises exist in evidence."""
        reasoning_patterns = [
            r"\bif\s+.+then\b",
            r"\bassuming\s+that\b",
            r"\bgiven\s+that\b",
            r"\bprovided\s+that\b",
        ]

        has_reasoning = any(re.search(p, claim, re.IGNORECASE) for p in reasoning_patterns)
        if not has_reasoning:
            return False

        # Extract the premise (text after if/assuming/given)
        premise_match = re.search(r"\b(if|assuming|given|provided)\s+(?:that\s+)?(.+?)(?:,|then|\b$)", claim, re.IGNORECASE)
        if premise_match:
            premise = premise_match.group(2).strip()
            premise_words = [w for w in re.findall(r"\w+", premise.lower()) if len(w) > 3]
            if premise_words:
                evidence_lower = evidence.lower()
                found = sum(1 for w in premise_words if w in evidence_lower)
                coverage = found / len(premise_words) if premise_words else 1.0
                if coverage < 0.3:
                    return True

        return False

    # ─── Summary ───────────────────────────────────────────────────────────

    @staticmethod
    def _build_summary(by_type: Dict[str, List[str]], probability: float, total_claims: int) -> str:
        """Human-readable summary string."""
        parts = []
        for htype, claims in by_type.items():
            if claims:
                label = htype.replace("_", " ").title()
                parts.append(f"{len(claims)} {label}")

        if not parts:
            return f"All {total_claims} claims grounded in sources"

        detail = ", ".join(parts)
        return (
            f"{probability:.0%} hallucination risk detected "
            f"({sum(len(v) for v in by_type.values())}/{total_claims} claims): {detail}"
        )
