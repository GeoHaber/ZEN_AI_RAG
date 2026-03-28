"""
Confidence Scorer & Hallucination Detector

Combines multiple signals to estimate answer quality and detect hallucinated claims:
- Self-RAG principles: Does LLM score its own output?
- Source agreement: Do sources agree on key facts?
- Claim-evidence alignment: Are claims actually in the evidence?
- Semantic consistency: Are claims internally contradictory?
"""

import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)


class AnswerQuality(str, Enum):
    """Quality assessment of answer"""

    EXCELLENT = "excellent"  # >0.85 confidence, no hallucinations
    GOOD = "good"  # >0.70, few issues
    FAIR = "fair"  # >0.50, some concerns
    POOR = "poor"  # <0.50, significant issues
    UNRELIABLE = "unreliable"  # Multiple red flags


@dataclass
class ConfidenceBreakdown:
    """Detailed confidence score breakdown"""

    source_alignment: float  # Do sources agree? (0-1)
    claim_support: float  # Are claims in evidence? (0-1)
    semantic_consistency: float  # No contradictions? (0-1)
    source_credibility: float  # Quality of sources used (0-1)
    overall: float  # Weighted average


class HallucinationDetector:
    """Detect claims that are likely unsupported or contradicted (hallucinations)"""

    # Patterns that indicate likely hallucinations
    HALLUCINATION_INDICATORS = {
        "specific_numbers": r"\b(19\d{2}|20\d{2}|\d{1,3}[.,]\d+)\b",  # Specific years/numbers
        "absolute_claims": r"\b(all|every|always|never|must|definitely|certainly)\b",  # Absolute language
        "attribution": r"\b(said|stated|claimed|argued|wrote|according to)\b",  # Attributions need sources
        "comparative": r"\b(more|less|better|worse|greater|smaller)\b\s+than",  # Comparisons need basis
        "quotes": r"['\"](.+?)['\"]",  # Direct quotes (must be verbatim in source)
    }

    def detect_hallucinations(
        self,
        answer: str,
        evidence: List[Dict[str, Any]],
        claims: List[Any],
    ) -> Tuple[List[str], float]:
        """
        Detect hallucinated claims.

        Returns:
            (hallucinated_claims, hallucination_probability)
        """
        if not claims:
            return [], 0.0

        evidence_text = " ".join(e.get("text", "") for e in evidence).lower()
        hallucinated = []
        score_sum = 0.0

        for claim in claims:
            claim_text = claim.text if hasattr(claim, "text") else str(claim)
            score = self._hallucination_likelihood(claim, evidence_text)
            score_sum += score
            if score > 0.6:  # Likely hallucinated
                hallucinated.append(claim_text)

        # Probability = average likelihood across all claims (0-1, probabilistic interpretation)
        hallucination_probability = score_sum / len(claims)

        return hallucinated, hallucination_probability

    def _hallucination_likelihood(self, claim: Any, evidence_text: str) -> float:
        """Score likelihood that a claim is hallucinated (0-1)"""
        claim_text = (claim.text if hasattr(claim, "text") else str(claim)).lower()

        # Base score: is claim in evidence?
        in_evidence = self._token_overlap(claim_text, evidence_text)

        if not in_evidence:
            return 0.95  # Not in evidence = very likely hallucinated

        # Check for red flag indicators
        red_flags = 0
        total_indicators = 0

        for indicator_type, pattern in self.HALLUCINATION_INDICATORS.items():
            matches = len(re.findall(pattern, claim_text, re.IGNORECASE))
            if matches > 0:
                total_indicators += 1

                # Check if these specific elements are in evidence
                if indicator_type == "specific_numbers":
                    # Specific numbers should be explicitly in evidence
                    if not any(m.group() in evidence_text for m in re.finditer(pattern, claim_text)):
                        red_flags += 1

                elif indicator_type == "quotes":
                    # Direct quotes MUST be in evidence verbatim
                    quote_match = re.search(r'["\'](.+?)["\']', claim_text)
                    if quote_match and quote_match.group(1) not in evidence_text:
                        red_flags += 1

        # Calculate final score
        if total_indicators == 0:
            return 0.1 * (1.0 - in_evidence)  # Simple claim, low risk

        red_flag_ratio = red_flags / total_indicators
        return 0.2 + (0.8 * red_flag_ratio) * (1.0 - in_evidence)

    def _token_overlap(self, claim: str, evidence: str) -> float:
        """Calculate token overlap between claim and evidence"""
        claim_tokens = set(claim.split())
        evidence_tokens = set(evidence.split())

        if not claim_tokens:
            return 0.0

        overlap = len(claim_tokens & evidence_tokens)
        return overlap / len(claim_tokens)


class SemanticConsistencyChecker:
    """Check for internal contradictions within answer"""

    def check_consistency(self, claims: List[Any]) -> Tuple[List[Tuple[str, str]], float]:
        """
        Find internal contradictions.

        Returns:
            (contradictory_pairs, consistency_score)
        """
        contradictions = []
        consistency_score = 1.0

        # Simple contradiction detection — handle both objects and plain strings
        for i, claim1 in enumerate(claims):
            claim1_text = claim1.text if hasattr(claim1, "text") else str(claim1)
            for claim2 in claims[i + 1 :]:
                claim2_text = claim2.text if hasattr(claim2, "text") else str(claim2)
                if self._are_contradictory(claim1_text, claim2_text):
                    contradictions.append((claim1_text, claim2_text))
                    consistency_score -= 0.2

        return contradictions, max(0.0, consistency_score)

    def _are_contradictory(self, claim1: str, claim2: str) -> bool:
        """Check if two claims contradict each other"""
        negations = ["not", "no", "never", "isn't", "wasn't", "doesn't", "didn't"]

        claim1_lower = claim1.lower()
        claim2_lower = claim2.lower()

        # Same subject, opposite properties — use word boundary matching
        for neg in negations:
            # Use word boundary to avoid matching "not" inside "nothing", "note", etc.
            pattern = r"\b" + re.escape(neg) + r"\b"
            if re.search(pattern, claim2_lower):
                # Extract core claim (remove only the exact negation word)
                core = re.sub(pattern, "", claim2_lower).strip()
                core = re.sub(r"\s+", " ", core)  # Collapse extra spaces
                # Match core phrase: word boundaries only at first/last word; allow flexible whitespace between
                if len(core) > 5:
                    parts = core.split()
                    if parts:
                        core_pattern = r"\b" + r"\s+".join(re.escape(p) for p in parts) + r"\b"
                        if re.search(core_pattern, claim1_lower):
                            return True
            # Use word boundary to avoid matching "not" inside "nothing", "note", etc.
            pattern = r"\b" + re.escape(neg) + r"\b"
            if re.search(pattern, claim2_lower):
                # Extract core claim (remove only the exact negation word)
                core = re.sub(pattern, "", claim2_lower).strip()
                core = re.sub(r"\s+", " ", core)  # Collapse extra spaces
                # Match core phrase: word boundaries only at first/last word; allow flexible whitespace between
                if len(core) > 5:
                    parts = core.split()
                    if parts:
                        core_pattern = r"\b" + r"\s+".join(re.escape(p) for p in parts) + r"\b"
                        if re.search(core_pattern, claim1_lower):
                            return True

        return False


class AnswerQualityAssessor:
    """Combine multiple signals into overall quality assessment"""

    def __init__(self):
        self.hallucination_detector = HallucinationDetector()
        self.consistency_checker = SemanticConsistencyChecker()

    def assess_answer_quality(
        self,
        answer: str,
        evidence: List[Dict[str, Any]],
        claims: List[Any],
        verification_results: Any = None,  # From FactChecker
    ) -> Tuple[AnswerQuality, ConfidenceBreakdown, List[str]]:
        """
        Comprehensive quality assessment of answer.

        Returns:
            (quality_level, confidence_breakdown, warnings)
        """

        # Component 1: Hallucination risk
        hallucinated, hallucination_prob = self.hallucination_detector.detect_hallucinations(answer, evidence, claims)

        # Component 2: Semantic consistency
        contradictions, consistency_score = self.consistency_checker.check_consistency(claims)

        # Component 3: Source credibility
        source_credibility = self._score_source_credibility(evidence)

        # Component 4: Claim support (from verification if available)
        if verification_results:
            supported_ratio = sum(1 for v in verification_results if str(v.label) == "SUPPORTED") / max(
                len(verification_results), 1
            )
        else:
            supported_ratio = 1.0 - hallucination_prob

        # Component 5: Source agreement
        source_agreement = self._score_source_agreement(evidence)

        # Combine into overall confidence
        confidence = ConfidenceBreakdown(
            source_alignment=source_agreement,
            claim_support=1.0 - hallucination_prob,
            semantic_consistency=consistency_score,
            source_credibility=source_credibility,
            overall=(
                (source_agreement * 0.2)
                + ((1.0 - hallucination_prob) * 0.3)
                + (consistency_score * 0.2)
                + (source_credibility * 0.2)
                + (supported_ratio * 0.1)
            ),
        )

        # Determine quality level
        quality = self._determine_quality(confidence.overall, hallucination_prob, contradictions)

        # Generate warnings
        warnings = self._generate_warnings(hallucinated, contradictions, hallucination_prob, confidence)

        return quality, confidence, warnings

    def _score_source_credibility(self, evidence: List[Dict[str, Any]]) -> float:
        """Score credibility of sources used"""
        if not evidence:
            return 0.0

        credibility_scores = []
        type_scores = {
            "official": 0.95,
            "academic": 0.90,
            "news": 0.75,
            "wiki": 0.65,
            "pdf": 0.60,
            "web": 0.50,
        }

        for ev in evidence:
            source_type = ev.get("type", "unknown").lower()
            score = type_scores.get(source_type, 0.4)
            credibility_scores.append(score * ev.get("score", 0.5))  # Weight by relevance

        return sum(credibility_scores) / len(credibility_scores) if credibility_scores else 0.5

    def _score_source_agreement(self, evidence: List[Dict[str, Any]]) -> float:
        """Score how much sources agree (vs conflict)"""
        if len(evidence) < 2:
            return 0.5  # Uncertain with single source

        # Simple heuristic: similar sources likely agree
        types = [ev.get("type", "unknown") for ev in evidence]
        unique_types = len(set(types))

        # More type diversity = potentially more conflict
        agreement = 1.0 - (unique_types / max(len(types), 1)) * 0.3

        return agreement

    def _determine_quality(
        self,
        overall_confidence: float,
        hallucination_prob: float,
        contradictions: List[Tuple[str, str]],
    ) -> AnswerQuality:
        """Determine overall quality level"""
        if overall_confidence > 0.85 and hallucination_prob < 0.1 and not contradictions:
            return AnswerQuality.EXCELLENT
        elif overall_confidence > 0.70 and hallucination_prob < 0.2:
            return AnswerQuality.GOOD
        elif overall_confidence > 0.50 and hallucination_prob < 0.4:
            return AnswerQuality.FAIR
        elif overall_confidence > 0.30 and hallucination_prob < 0.6:
            return AnswerQuality.POOR
        else:
            return AnswerQuality.UNRELIABLE

    def _generate_warnings(
        self,
        hallucinated: List[str],
        contradictions: List[Tuple[str, str]],
        hallucination_prob: float,
        confidence: ConfidenceBreakdown,
    ) -> List[str]:
        """Generate actionable warnings"""
        warnings = []

        if hallucination_prob > 0.5:
            warnings.append(
                f"🚨 **HIGH HALLUCINATION RISK ({hallucination_prob:.0%})**: "
                f"Some claims may not be supported by sources"
            )

        if hallucinated:
            warnings.append(
                f"⚠️ **Unsupported claims detected**: {len(hallucinated)} claim(s) not clearly found in evidence"
            )

        if contradictions:
            warnings.append(
                f"⚠️ **Internal contradictions**: {len(contradictions)} inconsistency/ies found within answer"
            )

        if confidence.source_credibility < 0.6:
            warnings.append("ℹ️ **Source quality lower**: Sources have mixed credibility")

        if confidence.source_alignment < 0.5:
            warnings.append("ℹ️ **Sources disagree**: Retrieved sources may have conflicting info")

        return warnings
