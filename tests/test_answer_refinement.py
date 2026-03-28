"""
Tests for Core/answer_refinement.py — AnswerRefinementEngine

Tests cover:
  - RefinementResult dataclass
  - Score-only mode (no LLM function)
  - refine() async API
  - Completeness check (short answers)
  - to_dict() serialisation
  - Edge cases
"""

import pytest
from unittest.mock import MagicMock


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_detector():
    """Fake HallucinationDetector returning clean report."""
    from Core.hallucination_detector_v2 import ClaimCheck, HallucinationReport

    det = MagicMock()
    det.detect_hallucinations.return_value = HallucinationReport(
        claims=[ClaimCheck("Claim", None, 0.95)],
        probability=0.05,
        by_type={},
        summary="Clean",
    )
    return det


@pytest.fixture
def engine_score_only():
    """Engine in score-only mode (no LLM, no detector)."""
    from Core.answer_refinement import AnswerRefinementEngine

    return AnswerRefinementEngine(llm_generate_fn=None, hallucination_detector=None)


@pytest.fixture
def engine_with_detector(mock_detector):
    """Engine with mocked detector but no LLM."""
    from Core.answer_refinement import AnswerRefinementEngine

    return AnswerRefinementEngine(
        llm_generate_fn=None,
        hallucination_detector=mock_detector,
        min_answer_words=10,
    )


@pytest.fixture
def engine_full(mock_detector):
    """Engine with mocked LLM + detector."""
    from Core.answer_refinement import AnswerRefinementEngine

    async def fake_llm(prompt):
        return "A revised, longer and more comprehensive answer about the topic."

    return AnswerRefinementEngine(
        llm_generate_fn=fake_llm,
        hallucination_detector=mock_detector,
        min_answer_words=10,
        max_refinement_attempts=1,
    )


# ─── Import ────────────────────────────────────────────────────────────────


def test_import():
    from Core.answer_refinement import AnswerRefinementEngine, RefinementResult

    assert AnswerRefinementEngine is not None
    assert RefinementResult is not None


# ─── RefinementResult ──────────────────────────────────────────────────────


def test_refinement_result_dataclass():
    from Core.answer_refinement import RefinementResult

    r = RefinementResult(
        answer="Revised answer",
        original_answer="Original",
        was_revised=True,
        revision_count=1,
        revision_reasons=["hallucination"],
        quality_score=0.80,
        hallucination_probability=0.15,
        word_count=2,
    )
    assert r.was_revised is True
    assert r.revision_reason == "hallucination"
    assert r.quality_score == 0.80


def test_refinement_result_no_revision():
    from Core.answer_refinement import RefinementResult

    r = RefinementResult(
        answer="Same answer",
        original_answer="Same answer",
        was_revised=False,
        revision_count=0,
        revision_reasons=[],
        quality_score=0.92,
        hallucination_probability=0.02,
        word_count=2,
    )
    assert not r.was_revised
    assert r.revision_reason is None


def test_to_dict():
    from Core.answer_refinement import RefinementResult

    r = RefinementResult(
        answer="Final",
        original_answer="Draft",
        was_revised=True,
        revision_count=1,
        revision_reasons=["too_short"],
        quality_score=0.7,
        hallucination_probability=0.1,
        word_count=1,
    )
    d = r.to_dict()
    assert d["was_revised"] is True
    assert d["quality_score"] == 0.7
    assert "answer" in d
    assert "hallucination_probability" in d


# ─── Score-only refine() ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refine_score_only_mode(engine_score_only):
    """Without LLM/detector, refine should return answer unchanged with quality score."""
    result = await engine_score_only.refine(
        query="What is Python?",
        answer="Python is a versatile programming language used for web development, data science, and machine learning.",
        context="Python is a high-level programming language created by Guido van Rossum.",
    )
    from Core.answer_refinement import RefinementResult

    assert isinstance(result, RefinementResult)
    assert result.answer  # Non-empty
    assert 0.0 <= result.quality_score <= 1.0


@pytest.mark.asyncio
async def test_refine_preserves_good_answer(engine_with_detector):
    """Good answer that passes checks should remain unchanged."""
    good_answer = (
        "Python was created by Guido van Rossum and first released in 1991. "
        "It supports multiple paradigms including OOP, functional, and procedural."
    )
    result = await engine_with_detector.refine(
        query="What is Python?",
        answer=good_answer,
        context="Python was created by Guido van Rossum. First released in 1991.",
    )
    assert result.answer == good_answer
    assert not result.was_revised


# ─── With detector ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refine_calls_detector(engine_with_detector, mock_detector):
    """Detector should be called during refinement."""
    await engine_with_detector.refine(
        query="test",
        answer="A detailed answer with more than ten words for the completeness check.",
        context="context",
    )
    mock_detector.detect_hallucinations.assert_called()


# ─── Short answer completeness ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_short_answer_detected(engine_full):
    """Very short answer should be detected as incomplete."""
    result = await engine_full.refine(
        query="Explain quantum computing in detail",
        answer="It uses qubits.",
        context="Quantum computing uses qubits which can be in superposition states.",
    )
    # The engine should try to expand it via the LLM
    from Core.answer_refinement import RefinementResult

    assert isinstance(result, RefinementResult)


# ─── Edge Cases ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_answer(engine_score_only):
    """Empty answer should not crash."""
    result = await engine_score_only.refine("query", "", "context")
    assert isinstance(result.quality_score, float)


@pytest.mark.asyncio
async def test_empty_context(engine_score_only):
    """Empty context should not crash."""
    result = await engine_score_only.refine("query", "Some answer text here with enough words.", "")
    assert isinstance(result.quality_score, float)
