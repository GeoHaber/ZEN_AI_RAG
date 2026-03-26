"""
Fact Checker - FEVER-inspired fact verification system

Based on:
- FEVER: Fact Extraction and VERification (Thorne et al., 2018)
- Self-RAG: Learning to Retrieve, Generate, and Critique (Asai et al., 2023)
- Modern hallucination detection techniques

Verifies claims against retrieved evidence with confidence scoring.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class VerificationLabel(str, Enum):
    """FEVER-style verification labels"""

    SUPPORTED = "SUPPORTED"  # Evidence directly supports claim
    REFUTED = "REFUTED"  # Evidence contradicts claim
    NOT_ENOUGH_INFO = "NOT_ENOUGH_INFO"  # No evidence either way
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"  # Some support, some contradiction
    UNVERIFIABLE = "UNVERIFIABLE"  # Claim can't be verified from evidence


class HallucinationLevel(str, Enum):
    """Likelihood that a claim is hallucinated (not in evidence)"""

    SUPPORTED = "supported"  # Clearly in evidence
    LIKELY_SUPPORTED = "likely_supported"  # Inferred from evidence
    UNCERTAIN = "uncertain"  # Could be inferred
    LIKELY_HALLUCINATED = "likely_hallucinated"  # Probably made up
    CLEARLY_HALLUCINATED = "clearly_hallucinated"  # Definitely made up


@dataclass
class Claim:
    """Single factual claim extracted from answer"""

    text: str
    subject: str  # Entity being described
    predicate: str  # What property/relation
    object_value: str  # The value/property
    sentence_idx: int


@dataclass
class Evidence:
    """Source evidence for evaluating a claim"""

    text: str
    source_name: str
    source_type: str
    source_date: Optional[str] = None
    relevance_score: float = 1.0


@dataclass
class VerificationResult:
    """Result of verifying a single claim"""

    claim: Claim
    label: VerificationLabel
    confidence: float  # 0-1
    supporting_evidence: List[Evidence] = field(default_factory=list)
    contradicting_evidence: List[Evidence] = field(default_factory=list)
    reasoning: str = ""
    hallucination_level: HallucinationLevel = HallucinationLevel.SUPPORTED


@dataclass
class AnswerVerification:
    """Complete verification for an answer"""

    answer: str
    claims: List[Claim]
    verifications: List[VerificationResult] = field(default_factory=list)
    overall_label: VerificationLabel = VerificationLabel.SUPPORTED
    confidence_score: float = 1.0  # Average confidence across claims
    hallucination_risk: float = 0.0  # 0-1 probability of hallucination
    key_supported_facts: List[str] = field(default_factory=list)
    key_unsupported_facts: List[str] = field(default_factory=list)
    critical_warnings: List[str] = field(default_factory=list)


class ClaimExtractor:
    """Extract factual claims from answer text using simple patterns"""

    # Sentence patterns that usually contain factual claims
    CLAIM_PATTERNS = [
        r"^(.+?)\s+(?:is|are|was|were)\s+(.+?)$",  # X is Y
        r"^(.+?)\s+(?:founded|created|born|died)\s+(?:in|on)?\s+(.+?)$",  # X founded in Y
        r"^(?:The|A)\s+(.+?)\s+(?:has|have|had)\s+(.+?)$",  # The X has Y
        r"^(.+?)\s+(?:said|stated|claims?|argues?)\s+(.+?)$",  # X said Y
    ]

    def extract_claims(self, answer: str) -> List[Claim]:
        """Extract individual factual claims from answer text"""
        claims = []
        sentences = re.split(r"[.!?]+", answer)

        for sent_idx, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:  # Skip short sentences
                continue

            # Try to match patterns
            for pattern in self.CLAIM_PATTERNS:
                match = re.match(pattern, sentence, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        claim = Claim(
                            text=sentence,
                            subject=groups[0].strip(),
                            predicate=pattern.split("\\s+")[1],
                            object_value=groups[1].strip(),
                            sentence_idx=sent_idx,
                        )
                        claims.append(claim)
                        break

        return claims


class FactChecker:
    """FEVER-style fact verification against evidence"""

    def __init__(self):
        self.claim_extractor = ClaimExtractor()
        self.evidence_threshold = 0.3  # Minimum relevance to consider evidence

    def verify_answer(
        self,
        answer: str,
        evidence: List[Dict[str, Any]],
    ) -> AnswerVerification:
        """Verify all claims in answer against evidence"""

        # Extract claims
        claims = self.claim_extractor.extract_claims(answer)

        # Convert evidence to Evidence objects
        evidence_objects = [
            Evidence(
                text=e.get("text", ""),
                source_name=e.get("source", "Unknown"),
                source_type=e.get("type", "unknown"),
                source_date=e.get("date"),
                relevance_score=e.get("score", 0.5),
            )
            for e in evidence
        ]

        # Verify each claim
        verifications = []
        labels = []
        confidences = []
        hallucination_risks = []

        for claim in claims:
            verification = self._verify_claim(claim, evidence_objects)
            verifications.append(verification)
            labels.append(verification.label)
            confidences.append(verification.confidence)
            hallucination_risks.append(
                1.0
                if verification.hallucination_level
                in [
                    HallucinationLevel.CLEARLY_HALLUCINATED,
                    HallucinationLevel.LIKELY_HALLUCINATED,
                ]
                else 0.0
                if verification.hallucination_level == HallucinationLevel.SUPPORTED
                else 0.3
            )

        # Overall assessment
        overall_label = self._aggregate_labels(labels)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 1.0
        avg_hallucination_risk = sum(hallucination_risks) / len(hallucination_risks) if hallucination_risks else 0.0

        # Identify key facts
        supported_facts = [
            v.claim.text
            for v in verifications
            if v.label in [VerificationLabel.SUPPORTED, VerificationLabel.PARTIALLY_SUPPORTED]
        ]
        unsupported_facts = [
            v.claim.text
            for v in verifications
            if v.label in [VerificationLabel.NOT_ENOUGH_INFO, VerificationLabel.UNVERIFIABLE]
        ]

        # Critical warnings
        critical_warnings = self._generate_warnings(verifications)

        return AnswerVerification(
            answer=answer,
            claims=claims,
            verifications=verifications,
            overall_label=overall_label,
            confidence_score=avg_confidence,
            hallucination_risk=avg_hallucination_risk,
            key_supported_facts=supported_facts[:5],
            key_unsupported_facts=unsupported_facts[:5],
            critical_warnings=critical_warnings,
        )

    def _verify_claim(
        self,
        claim: Claim,
        evidence: List[Evidence],
    ) -> VerificationResult:
        """Verify a single claim against evidence"""

        if not evidence:
            return VerificationResult(
                claim=claim,
                label=VerificationLabel.NOT_ENOUGH_INFO,
                confidence=0.0,
                hallucination_level=HallucinationLevel.CLEARLY_HALLUCINATED,
                reasoning="No evidence provided to verify claim",
            )

        supporting = []
        contradicting = []
        uncertain = []

        # Score claim against each piece of evidence
        for ev in evidence:
            score = self._similarity_score(claim, ev)

            if score > 0.7:  # Strong match
                supporting.append(ev)
            elif score > 0.4:  # Partial match
                uncertain.append(ev)
            elif self._is_contradictory(claim, ev):
                contradicting.append(ev)

        # Determine label
        if supporting:
            label = VerificationLabel.SUPPORTED
            hallucination_level = HallucinationLevel.SUPPORTED
            confidence = min(0.95, 0.5 + len(supporting) * 0.15)
        elif contradicting:
            label = VerificationLabel.REFUTED
            hallucination_level = HallucinationLevel.CLEARLY_HALLUCINATED
            confidence = 0.8
        elif uncertain:
            label = VerificationLabel.PARTIALLY_SUPPORTED
            hallucination_level = HallucinationLevel.LIKELY_SUPPORTED
            confidence = 0.5
        else:
            label = VerificationLabel.NOT_ENOUGH_INFO
            hallucination_level = HallucinationLevel.LIKELY_HALLUCINATED
            confidence = 0.2

        return VerificationResult(
            claim=claim,
            label=label,
            confidence=confidence,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            hallucination_level=hallucination_level,
            reasoning=self._generate_reasoning(claim, supporting, contradicting, uncertain),
        )

    def _similarity_score(self, claim: Claim, evidence: Evidence) -> float:
        """Score how much evidence supports a claim (0-1)"""
        # Simple token overlap + subject matching
        claim_tokens = set(claim.text.lower().split())
        evidence_tokens = set(evidence.text.lower().split())

        overlap = len(claim_tokens & evidence_tokens) / max(len(claim_tokens), 1)
        subject_match = 1.0 if claim.subject.lower() in evidence.text.lower() else 0.0

        # Weighted combination
        return (overlap * 0.5 + subject_match * 0.5) * evidence.relevance_score

    def _is_contradictory(self, claim: Claim, evidence: Evidence) -> bool:
        """Check if evidence contradicts claim"""
        # Look for explicit negations
        negation_words = ["not", "no", "never", "didn't", "doesn't", "won't"]

        claim.text.lower()
        evidence_lower = evidence.text.lower()

        # Very basic contradiction detection
        if claim.subject.lower() in evidence_lower:
            for neg in negation_words:
                if neg in evidence_lower and claim.predicate in evidence_lower:
                    return True

        return False

    def _aggregate_labels(self, labels: List[VerificationLabel]) -> VerificationLabel:
        """Aggregate multiple labels into overall label"""
        if not labels:
            return VerificationLabel.UNVERIFIABLE

        # Count label types
        from collections import Counter

        counts = Counter(labels)

        # REFUTED takes priority (direct contradiction)
        if counts.get(VerificationLabel.REFUTED, 0) > 0:
            return VerificationLabel.REFUTED

        # Then SUPPORTED
        if counts.get(VerificationLabel.SUPPORTED, 0) >= len(labels) * 0.6:
            return VerificationLabel.SUPPORTED

        # Then PARTIALLY_SUPPORTED
        if counts.get(VerificationLabel.PARTIALLY_SUPPORTED, 0) > 0:
            return VerificationLabel.PARTIALLY_SUPPORTED

        # Default to NOT_ENOUGH_INFO
        return VerificationLabel.NOT_ENOUGH_INFO

    def _generate_reasoning(
        self,
        claim: Claim,
        supporting: List[Evidence],
        contradicting: List[Evidence],
        uncertain: List[Evidence],
    ) -> str:
        """Generate human-readable reasoning"""
        if supporting:
            return f"Supported by {len(supporting)} source(s): {supporting[0].source_name}"
        elif contradicting:
            return f"Contradicted by {len(contradicting)} source(s): {contradicting[0].source_name}"
        elif uncertain:
            return f"Partially supported by {len(uncertain)} source(s)"
        else:
            return "No evidence found to verify this claim"

    def _generate_warnings(self, verifications: List[VerificationResult]) -> List[str]:
        """Generate critical warnings about answer quality"""
        warnings = []

        refuted = [v for v in verifications if v.label == VerificationLabel.REFUTED]
        unsupported = [v for v in verifications if v.label == VerificationLabel.NOT_ENOUGH_INFO]
        hallucinated = [
            v
            for v in verifications
            if v.hallucination_level
            in [
                HallucinationLevel.CLEARLY_HALLUCINATED,
                HallucinationLevel.LIKELY_HALLUCINATED,
            ]
        ]

        if refuted:
            warnings.append(f"⚠️ **CRITICAL**: {len(refuted)} claim(s) are directly contradicted by evidence!")

        if hallucinated:
            warnings.append(f"⚠️ **HIGH RISK**: {len(hallucinated)} claim(s) may be unsupported or hallucinated")

        if unsupported and len(unsupported) > len(verifications) * 0.3:
            warnings.append(f"⚠️ **Low Evidence**: {len(unsupported)} claim(s) have insufficient evidence")

        return warnings
