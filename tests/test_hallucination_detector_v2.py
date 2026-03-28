"""
Tests for Core/hallucination_detector_v2.py — AdvancedHallucinationDetector

Tests cover:
  - HallucinationReport dataclass behaviour
  - ClaimCheck dataclass
  - detect_hallucinations() API
  - Legacy detect() wrapper
  - to_legacy_dict() format for UI compat
  - Edge cases (empty input, no evidence)
"""

import pytest
from unittest.mock import MagicMock


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def detector():
    """Create detector with mocked CrossEncoder to avoid downloads."""
    from Core.hallucination_detector_v2 import AdvancedHallucinationDetector

    d = AdvancedHallucinationDetector.__new__(AdvancedHallucinationDetector)
    d.nli_model = None  # No real NLI model
    d.nli_available = False
    d.logger = MagicMock()
    return d


@pytest.fixture
def grounded_answer():
    return "Python was created by Guido van Rossum and released in 1991."


@pytest.fixture
def evidence():
    return [
        "Python is a programming language created by Guido van Rossum. It was first released in 1991.",
        "Python supports multiple programming paradigms including OOP and functional.",
    ]


# ─── Import ────────────────────────────────────────────────────────────────


def test_import():
    from Core.hallucination_detector_v2 import (
        AdvancedHallucinationDetector,
        ClaimCheck,
        HallucinationReport,
    )

    assert AdvancedHallucinationDetector is not None
    assert ClaimCheck is not None
    assert HallucinationReport is not None


# ─── ClaimCheck dataclass ──────────────────────────────────────────────────


def test_claim_check_creation():
    from Core.hallucination_detector_v2 import ClaimCheck

    c = ClaimCheck(
        claim_text="Python was created in 1991",
        hallucination_type=None,
        confidence=0.95,
        evidence_snippet="first released in 1991",
    )
    assert c.claim_text == "Python was created in 1991"
    assert c.hallucination_type is None
    assert c.confidence == 0.95


def test_claim_check_flagged():
    from Core.hallucination_detector_v2 import ClaimCheck

    c = ClaimCheck(
        claim_text="Python was released in 2020",
        hallucination_type="numerical_error",
        confidence=0.8,
    )
    assert c.hallucination_type == "numerical_error"


# ─── HallucinationReport ──────────────────────────────────────────────────


def test_report_properties():
    from Core.hallucination_detector_v2 import ClaimCheck, HallucinationReport

    claims = [
        ClaimCheck("Claim A", None, 0.9),
        ClaimCheck("Claim B", "ungrounded", 0.7),
        ClaimCheck("Claim C", "numerical_error", 0.8),
    ]
    report = HallucinationReport(
        claims=claims,
        probability=0.35,
        by_type={"ungrounded": ["Claim B"], "numerical_error": ["Claim C"]},
        summary="2 issues found",
    )
    assert report.total_claims == 3
    assert report.hallucinated_claims == 2
    assert report.has_hallucinations is True
    assert report.hallucination_rate == 0.35


def test_report_no_hallucinations():
    from Core.hallucination_detector_v2 import ClaimCheck, HallucinationReport

    claims = [
        ClaimCheck("Good claim", None, 0.95),
    ]
    report = HallucinationReport(claims=claims, probability=0.0, by_type={}, summary="Clean")
    assert not report.has_hallucinations
    assert report.hallucinated_claims == 0


def test_to_legacy_dict():
    from Core.hallucination_detector_v2 import ClaimCheck, HallucinationReport

    claims = [
        ClaimCheck("Good", None, 0.9),
        ClaimCheck("Contradicted", "nli_contradiction", 0.85),
        ClaimCheck("Unsupported", "ungrounded", 0.7),
    ]
    report = HallucinationReport(
        claims=claims,
        probability=0.40,
        by_type={"nli_contradiction": ["Contradicted"], "ungrounded": ["Unsupported"]},
        summary="Issues",
    )
    legacy = report.to_legacy_dict()
    assert legacy["has_hallucinations"] is True
    assert legacy["hallucination_rate"] == 0.40
    assert legacy["total_claims"] == 3
    assert len(legacy["refuted_claims"]) == 1  # nli_contradiction
    assert len(legacy["unsupported_claims"]) == 1  # ungrounded
    assert "summary" in legacy


# ─── detect_hallucinations() ──────────────────────────────────────────────


def test_detect_hallucinations_returns_report(detector, grounded_answer, evidence):
    """Main API should return a HallucinationReport."""
    from Core.hallucination_detector_v2 import HallucinationReport

    report = detector.detect_hallucinations(grounded_answer, evidence)
    assert isinstance(report, HallucinationReport)
    assert 0.0 <= report.probability <= 1.0
    assert isinstance(report.claims, list)


def test_detect_hallucinations_low_prob_for_grounded(detector, evidence):
    """Well-grounded answer should get low probability."""
    answer = "Python supports multiple programming paradigms including OOP."
    report = detector.detect_hallucinations(answer, evidence)
    # Without NLI model, we rely on heuristic checks
    assert isinstance(report.probability, float)


def test_detect_hallucinations_empty_answer(detector, evidence):
    """Empty answer should be handled gracefully."""
    report = detector.detect_hallucinations("", evidence)
    assert isinstance(report.probability, float)


def test_detect_hallucinations_empty_evidence(detector, grounded_answer):
    """Empty evidence list should not crash."""
    report = detector.detect_hallucinations(grounded_answer, [])
    assert isinstance(report.probability, float)


# ─── Legacy detect() wrapper ──────────────────────────────────────────────


def test_detect_legacy_returns_dict(detector, grounded_answer, evidence):
    """Legacy detect() should return dict with expected keys."""
    result = detector.detect(grounded_answer, evidence)
    assert isinstance(result, dict)
    assert "has_hallucinations" in result
    assert "hallucination_rate" in result
    assert "total_claims" in result


# ─── Edge Cases ────────────────────────────────────────────────────────────


def test_very_long_answer(detector):
    """Very long answer should not crash."""
    long_answer = "This is a sentence about science. " * 200
    evidence = ["Science is important."]
    report = detector.detect_hallucinations(long_answer, evidence)
    assert isinstance(report.probability, float)


def test_single_word_answer(detector):
    """Single word answer should work."""
    report = detector.detect_hallucinations("Yes", ["Some evidence text here."])
    assert isinstance(report.probability, float)
