"""
Core/confidence_scorer.py — Multi-Signal Answer Quality Assessment.

Signals:
  1. Source alignment (claim ↔ source keyword overlap)
  2. Claim support (NLI entailment scoring)
  3. Semantic consistency (answer ↔ query embedding similarity)
  4. Source credibility (domain reputation scoring)

Ported from ZEN_RAG.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of confidence signals."""

    source_alignment: float = 0.0
    claim_support: float = 0.0
    semantic_consistency: float = 0.0
    source_credibility: float = 0.0
    overall: float = 0.0


@dataclass
class AnswerQuality:
    """Full quality assessment of a RAG answer."""

    confidence: float = 0.0
    breakdown: ConfidenceBreakdown = field(default_factory=ConfidenceBreakdown)
    risk_level: str = "unknown"  # "low", "medium", "high"
    explanation: str = ""


class AnswerQualityAssessor:
    """Multi-signal quality assessment for RAG answers.

    Usage:
        assessor = AnswerQualityAssessor()
        quality = assessor.assess(answer, query, source_chunks)
        if quality.risk_level == "high":
            # Flag for review
    """

    # Weights for each signal
    W_ALIGNMENT = 0.30
    W_SUPPORT = 0.25
    W_CONSISTENCY = 0.25
    W_CREDIBILITY = 0.20

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model = None
        self._model_name = model_name

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
            except Exception as e:
                logger.warning(f"[ConfidenceScorer] Model not available: {e}")
        return self._model

    def assess(
        self,
        answer: str,
        query: str,
        source_chunks: List[Dict[str, Any]],
    ) -> AnswerQuality:
        """Compute multi-signal confidence score."""
        if not answer or not source_chunks:
            return AnswerQuality(
                confidence=0.0,
                risk_level="high",
                explanation="No answer or sources to assess",
            )

        # Signal 1: Source alignment
        alignment = self._score_alignment(answer, source_chunks)

        # Signal 2: Claim support
        support = self._score_claim_support(answer, source_chunks)

        # Signal 3: Semantic consistency
        consistency = self._score_semantic_consistency(answer, query)

        # Signal 4: Source credibility
        credibility = self._score_credibility(source_chunks)

        breakdown = ConfidenceBreakdown(
            source_alignment=alignment,
            claim_support=support,
            semantic_consistency=consistency,
            source_credibility=credibility,
        )

        overall = (
            self.W_ALIGNMENT * alignment
            + self.W_SUPPORT * support
            + self.W_CONSISTENCY * consistency
            + self.W_CREDIBILITY * credibility
        )
        breakdown.overall = overall

        # Risk level
        if overall >= 0.75:
            risk = "low"
        elif overall >= 0.50:
            risk = "medium"
        else:
            risk = "high"

        explanation = (
            f"Confidence {overall:.0%} — "
            f"Alignment: {alignment:.0%}, Support: {support:.0%}, "
            f"Consistency: {consistency:.0%}, Credibility: {credibility:.0%}"
        )

        return AnswerQuality(
            confidence=overall,
            breakdown=breakdown,
            risk_level=risk,
            explanation=explanation,
        )

    # ─── Signal 1: Source Alignment ────────────────────────────────────────

    @staticmethod
    def _score_alignment(answer: str, source_chunks: List[Dict]) -> float:
        """Score how well answer keywords align with source texts."""
        from Core.constants import STOP_WORDS

        answer_words = set(
            w for w in re.findall(r"\b\w+\b", answer.lower())
            if w not in STOP_WORDS and len(w) > 2
        )
        if not answer_words:
            return 0.5

        source_text = " ".join(c.get("text", "").lower() for c in source_chunks)
        source_words = set(
            w for w in re.findall(r"\b\w+\b", source_text)
            if w not in STOP_WORDS and len(w) > 2
        )

        if not source_words:
            return 0.5

        overlap = len(answer_words & source_words)
        return overlap / len(answer_words)

    # ─── Signal 2: Claim Support ───────────────────────────────────────────

    @staticmethod
    def _score_claim_support(answer: str, source_chunks: List[Dict]) -> float:
        """Score how many answer sentences are supported by sources."""
        sentences = re.split(r"(?<=[.!?])\s+", answer)
        if not sentences:
            return 0.5

        source_text = " ".join(c.get("text", "").lower() for c in source_chunks)
        supported = 0

        for sent in sentences:
            words = [w for w in re.findall(r"\b\w{4,}\b", sent.lower())]
            if not words:
                continue
            found = sum(1 for w in words if w in source_text)
            if found / len(words) > 0.4:
                supported += 1

        return supported / len(sentences) if sentences else 0.5

    # ─── Signal 3: Semantic Consistency ────────────────────────────────────

    def _score_semantic_consistency(self, answer: str, query: str) -> float:
        """Score semantic similarity between answer and query."""
        if not self.model:
            return 0.5

        try:
            import numpy as np
            embeddings = self.model.encode([query, answer], normalize_embeddings=True)
            sim = float(np.dot(embeddings[0], embeddings[1]))
            return max(0, min(1, sim))
        except Exception:
            return 0.5

    # ─── Signal 4: Source Credibility ──────────────────────────────────────

    @staticmethod
    def _score_credibility(source_chunks: List[Dict]) -> float:
        """Average credibility score based on source domains."""
        CREDIBILITY = {
            ".gov": 0.93, ".edu": 0.90, ".org": 0.70,
            "wikipedia.org": 0.85, "arxiv.org": 0.90,
            "pubmed": 0.92, "nature.com": 0.95,
        }

        if not source_chunks:
            return 0.5

        scores = []
        for c in source_chunks:
            url = (c.get("url") or "").lower()
            best = 0.50
            for key, cred in CREDIBILITY.items():
                if key in url:
                    best = max(best, cred)
            scores.append(best)

        return sum(scores) / len(scores) if scores else 0.5
