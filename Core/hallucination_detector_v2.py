"""
Core/hallucination_detector_v2.py — Multi-Signal Hallucination Detection

Detects 5 types of hallucinations in LLM answers:
  1. Ungrounded claims   — claim not findable in source evidence
  2. NLI contradictions  — claim directly contradicts evidence (CrossEncoder)
  3. Numerical errors    — numbers in answer don't match evidence
  4. Causal fabrication  — false cause-effect not in evidence
  5. Reasoning errors    — invalid conditional logic

Designed to work alongside the existing Core/answer_verification_sota.py
(FEVER framework) — this module adds NLI and deeper signal detection.

Usage:
    detector = AdvancedHallucinationDetector()
    result = detector.detect_hallucinations(answer, evidence_texts)
    if result.probability > 0.20:
        st.warning(f"⚠️ {result.probability:.0%} hallucination risk")
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    np = None


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ClaimCheck:
    """Result of checking one claim."""

    claim_text: str
    hallucination_type: Optional[str]  # None = grounded, else type
    confidence: float  # How confident we are in the detection (0–1)
    evidence_snippet: Optional[str] = None  # Best matching evidence


@dataclass
class HallucinationReport:
    """Aggregate report for an answer."""

    claims: List[ClaimCheck]
    probability: float  # Overall hallucination probability (0–1)
    by_type: Dict[str, List[str]]  # {type: [claim_texts]}
    summary: str

    @property
    def has_hallucinations(self) -> bool:
        return self.probability > 0.10

    @property
    def hallucination_rate(self) -> float:
        return self.probability

    @property
    def total_claims(self) -> int:
        return len(self.claims)

    @property
    def hallucinated_claims(self) -> int:
        return sum(1 for c in self.claims if c.hallucination_type is not None)

    def to_legacy_dict(self) -> Dict:
        """Convert to format compatible with ui/answer_verification.py.

        The UI distinguishes between *refuted* claims (directly contradicted)
        and *unsupported* claims (not findable in sources).  We split based
        on the hallucination_type so show_hallucination_warning() renders
        both sections correctly.
        """
        refuted = []
        unsupported = []
        for c in self.claims:
            if c.hallucination_type is None:
                continue
            entry = {"claim": c.claim_text, "reasoning": c.hallucination_type}
            if c.hallucination_type in (
                "nli_contradiction",
                "numerical_error",
            ):
                refuted.append(entry)
            else:
                unsupported.append(entry)
        return {
            "has_hallucinations": self.has_hallucinations,
            "hallucination_rate": self.probability,
            "refuted_claims": refuted,
            "unsupported_claims": unsupported,
            "total_claims": self.total_claims,
            "summary": self.summary,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Detector
# ─────────────────────────────────────────────────────────────────────────────


class AdvancedHallucinationDetector:
    """
    Multi-signal hallucination detection.

    Uses NLI CrossEncoder when available (significantly more accurate for
    contradiction detection), with robust heuristic fallbacks.
    """

    def __init__(self, nli_model_name: str = "cross-encoder/nli-deberta-v3-small"):
        self.nli_model = None
        self.nli_available = False

        try:
            from sentence_transformers import CrossEncoder

            self.nli_model = CrossEncoder(nli_model_name)
            self.nli_available = True
            logger.info(f"[HallucinationDetector] NLI model loaded: {nli_model_name}")
        except Exception as e:
            logger.info(f"[HallucinationDetector] NLI model not available ({e}); using heuristic-only detection")

    # =====================================================================
    # PUBLIC API
    # =====================================================================

    def detect_hallucinations(
        self,
        answer: str,
        evidence_texts: List[str],
        claims: Optional[List[str]] = None,
    ) -> HallucinationReport:
        """
        Detect hallucinations in an LLM answer.

        Args:
            answer: The generated answer text.
            evidence_texts: List of source/evidence passages.
            claims: Pre-extracted claims. If None, auto-extracted from answer.

        Returns:
            HallucinationReport with per-claim analysis and overall probability.
        """
        if not evidence_texts:
            return HallucinationReport(
                claims=[],
                probability=0.5,
                by_type={},
                summary="No evidence provided — cannot verify",
            )

        # Combine evidence for searching
        evidence_combined = "\n\n".join(evidence_texts)

        # Extract claims
        if claims is None:
            claims = self._extract_claims(answer)

        if not claims:
            return HallucinationReport(
                claims=[],
                probability=0.0,
                by_type={},
                summary="No verifiable claims found",
            )

        # Check each claim
        checked: List[ClaimCheck] = []
        by_type: Dict[str, List[str]] = {
            "ungrounded": [],
            "nli_contradiction": [],
            "numerical": [],
            "causal": [],
            "reasoning": [],
        }

        for claim_text in claims:
            if isinstance(claim_text, dict):
                claim_text = claim_text.get("text", str(claim_text))
            claim_text = str(claim_text).strip()
            if not claim_text or len(claim_text) < 10:
                continue

            result = self._check_claim(claim_text, evidence_combined, evidence_texts)
            checked.append(result)

            if result.hallucination_type:
                by_type.setdefault(result.hallucination_type, []).append(claim_text)

        # Calculate probability
        if not checked:
            prob = 0.0
        else:
            # Weighted: high-confidence detections count more
            weighted_sum = sum(c.confidence for c in checked if c.hallucination_type is not None)
            prob = min(1.0, weighted_sum / len(checked))

        summary = self._build_summary(by_type, prob, len(checked))

        return HallucinationReport(
            claims=checked,
            probability=prob,
            by_type=by_type,
            summary=summary,
        )

    # Compatibility alias used by existing code
    def detect(self, answer: str, sources: List) -> Dict:
        """Legacy API compatible with Core/answer_verification_sota.py."""
        evidence = []
        for src in sources:
            if isinstance(src, str):
                evidence.append(src)
            elif isinstance(src, dict):
                evidence.append(src.get("text", str(src)))
            else:
                evidence.append(str(src))

        report = self.detect_hallucinations(answer, evidence)
        return report.to_legacy_dict()

    # =====================================================================
    # CLAIM EXTRACTION
    # =====================================================================

    def _extract_claims(self, text: str) -> List[str]:
        """Extract individual factual claims from answer text."""
        # Split on sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+", text)
        claims = []

        for sent in sentences:
            sent = sent.strip()
            if not sent or len(sent) < 15:
                continue

            # Skip conversational filler
            if re.match(
                r"^(I\s+(think|believe|am not sure)|Let me|Here|Note that|"
                r"In summary|Overall|To summarize|As mentioned|Please note)",
                sent,
                re.I,
            ):
                continue

            # Skip questions
            if sent.endswith("?"):
                continue

            claims.append(sent)

        return claims

    # =====================================================================
    # PER-CLAIM CHECKING
    # =====================================================================

    def _check_claim(self, claim: str, evidence_combined: str, evidence_list: List[str]) -> ClaimCheck:
        """Check one claim against all evidence."""

        # 1. Numerical error (highest confidence)
        num_err = self._check_numerical(claim, evidence_combined)
        if num_err:
            return ClaimCheck(claim, "numerical", 0.85, num_err)

        # 2. NLI contradiction
        if self.nli_available:
            nli_result = self._check_nli(claim, evidence_list)
            if nli_result:
                return ClaimCheck(claim, "nli_contradiction", 0.80, nli_result)

        # 3. Causal fabrication
        causal_err = self._check_causal(claim, evidence_combined)
        if causal_err:
            return ClaimCheck(claim, "causal", 0.70, causal_err)

        # 4. Reasoning error
        reasoning_err = self._check_reasoning(claim, evidence_combined)
        if reasoning_err:
            return ClaimCheck(claim, "reasoning", 0.65, reasoning_err)

        # 5. Ungrounded claim (lowest confidence — many false positives)
        if self._is_ungrounded(claim, evidence_combined):
            return ClaimCheck(claim, "ungrounded", 0.45)

        # Grounded
        return ClaimCheck(claim, None, 0.0)

    # ── Check: Numerical errors ──────────────────────────────────────────

    def _check_numerical(self, claim: str, evidence: str) -> Optional[str]:
        """Detect numbers in claim that don't appear in evidence."""
        claim_nums = re.findall(r"\b\d+(?:[.,]\d+)*\b", claim)
        if not claim_nums:
            return None

        evidence_nums = set(re.findall(r"\b\d+(?:[.,]\d+)*\b", evidence))

        for num_str in claim_nums:
            # Normalize
            normalized = num_str.replace(",", "")
            if normalized in {"0", "1", "2", "3", "4", "5", "10", "100"}:
                continue  # Skip trivial numbers

            try:
                num_val = float(normalized)
            except ValueError:
                continue

            # Allow ±2% tolerance for large numbers, ±1 for small
            matched = False
            for ev_str in evidence_nums:
                try:
                    ev_val = float(ev_str.replace(",", ""))
                    if num_val == 0 and ev_val == 0:
                        matched = True
                        break
                    tolerance = max(1.0, abs(ev_val) * 0.02)
                    if abs(num_val - ev_val) <= tolerance:
                        matched = True
                        break
                except ValueError:
                    continue

            if not matched:
                return f"Number {num_str} not found in evidence"

        return None

    # ── Check: NLI contradiction ─────────────────────────────────────────

    def _check_nli(self, claim: str, evidence_list: List[str]) -> Optional[str]:
        """Use NLI CrossEncoder to detect if any evidence contradicts the claim."""
        if not self.nli_model:
            return None

        try:
            # Check against each evidence passage (truncated for speed)
            for evidence in evidence_list:
                ev_trunc = evidence[:800]
                if len(ev_trunc) < 20:
                    continue

                scores = self.nli_model.predict([(ev_trunc, claim)])
                # Output format: [contradiction, neutral, entailment]
                if hasattr(scores[0], "__len__") and len(scores[0]) >= 3:
                    contradiction_score = float(scores[0][0])
                    if contradiction_score > 0.70:
                        snippet = ev_trunc[:150].strip()
                        return f"Contradicted by: {snippet}..."
                elif isinstance(scores[0], (int, float)):
                    # Some models output a single score
                    if float(scores[0]) < -0.5:
                        return "NLI contradiction detected"
        except Exception as e:
            logger.debug(f"[HallucinationDetector] NLI check error: {e}")

        return None

    # ── Check: Causal fabrication ────────────────────────────────────────

    def _check_causal(self, claim: str, evidence: str) -> Optional[str]:
        """Detect false cause-effect claims not supported by evidence."""
        causal_markers = [
            r"\bcaused?\s+(?:by|the)\b",
            r"\bresult(?:s|ed)?\s+in\b",
            r"\blead(?:s|ing)?\s+to\b",
            r"\bis\s+responsible\s+for\b",
            r"\bdue\s+to\b",
            r"\bbecause\s+of\b",
            r"\btriggered?\b",
        ]

        claim_has_causal = any(re.search(p, claim, re.I) for p in causal_markers)
        if not claim_has_causal:
            return None

        # Evidence should also express causation for the same entities
        evidence_has_causal = any(re.search(p, evidence, re.I) for p in causal_markers)
        if not evidence_has_causal:
            return "Claim asserts causation but evidence only shows correlation"

        return None

    # ── Check: Reasoning errors ──────────────────────────────────────────

    def _check_reasoning(self, claim: str, evidence: str) -> Optional[str]:
        """Detect invalid if-then or conditional reasoning."""
        match = re.search(r"\bif\s+(.+?),?\s+then\s+(.+)", claim, re.I)
        if not match:
            return None

        premise = match.group(1).strip().lower()

        # Premise must be present in evidence
        if premise not in evidence.lower() and len(premise) > 10:
            return f"Conditional premise '{premise[:50]}' not found in evidence"

        return None

    # ── Check: Ungrounded claim ──────────────────────────────────────────

    def _is_ungrounded(self, claim: str, evidence: str) -> bool:
        """
        Check if claim has no lexical grounding in evidence.
        Conservative: requires multiple content words to be missing.
        """
        stopwords = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "and",
            "or",
            "but",
            "if",
            "then",
            "than",
            "that",
            "this",
            "it",
            "its",
            "not",
            "no",
            "so",
            "very",
            "also",
            "just",
            "more",
            "most",
            "such",
            "other",
            "which",
            "who",
            "what",
            "when",
            "where",
            "how",
            "all",
            "any",
            "both",
            "each",
        }

        content_words = [w for w in re.findall(r"\b\w+\b", claim.lower()) if w not in stopwords and len(w) > 2]

        if len(content_words) < 3:
            return False  # Too few words to judge

        evidence_lower = evidence.lower()
        found = sum(1 for w in content_words if w in evidence_lower)
        coverage = found / len(content_words)

        # If <30% of content words appear in evidence → ungrounded
        return coverage < 0.30

    # =====================================================================
    # SUMMARY
    # =====================================================================

    def _build_summary(self, by_type: Dict[str, List[str]], probability: float, total_claims: int) -> str:
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
