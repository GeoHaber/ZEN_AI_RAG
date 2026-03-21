"""
Core/evaluation.py — Answer & Retrieval Quality Evaluation.

AnswerEvaluator:
  - Faithfulness (answer grounded in sources)
  - Relevance (answer addresses the query)
  - Completeness (all aspects of query covered)
  - Conciseness (appropriate length)

RetrievalEvaluator:
  - Precision@K, Recall@K, MRR, F1

Ported from ZEN_RAG.
"""

from __future__ import annotations

import logging
import re
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AnswerEvaluator:
    """Evaluate RAG answer quality on multiple dimensions.

    Usage:
        evaluator = get_answer_evaluator()
        scores = evaluator.evaluate(question, answer, source_texts)
    """

    def __init__(self, llm_config: Optional[Dict] = None):
        self.llm_config = llm_config or {}
        self.evaluation_history: deque = deque(maxlen=100)

    def evaluate(
        self,
        question: str,
        answer: str,
        source_texts: List[str],
    ) -> Dict[str, float]:
        """Evaluate answer quality. Returns dict with scores [0-1]."""
        if not answer or not question:
            return {"overall": 0.0, "faithfulness": 0.0, "relevance": 0.0,
                    "completeness": 0.0, "conciseness": 0.0}

        faithfulness = self._score_faithfulness(answer, source_texts)
        relevance = self._score_relevance(answer, question)
        completeness = self._score_completeness(answer, question)
        conciseness = self._score_conciseness(answer)

        overall = (
            faithfulness * 0.35
            + relevance * 0.30
            + completeness * 0.20
            + conciseness * 0.15
        )

        scores = {
            "overall": round(overall, 3),
            "faithfulness": round(faithfulness, 3),
            "relevance": round(relevance, 3),
            "completeness": round(completeness, 3),
            "conciseness": round(conciseness, 3),
        }

        self.evaluation_history.append({
            "question": question[:100],
            "scores": scores,
        })

        return scores

    def _score_faithfulness(self, answer: str, source_texts: List[str]) -> float:
        """Score how well the answer is grounded in sources."""
        if not source_texts:
            return 0.5

        key_words = self._extract_key_words(answer)
        if not key_words:
            return 0.5

        combined_source = " ".join(source_texts).lower()
        found = sum(1 for w in key_words if w in combined_source)
        return found / len(key_words) if key_words else 0.5

    def _score_relevance(self, answer: str, question: str) -> float:
        """Score answer relevance to the question."""
        q_keywords = self._extract_key_words(question)
        if not q_keywords:
            return 0.5

        answer_lower = answer.lower()
        found = sum(1 for w in q_keywords if w in answer_lower)
        base_score = found / len(q_keywords)

        # Bonus for direct answer patterns
        if self._has_direct_answer_pattern(answer, question):
            base_score = min(1.0, base_score + 0.1)

        return base_score

    def _score_completeness(self, answer: str, question: str) -> float:
        """Score how completely the answer addresses the question."""
        sentences = self._split_sentences(answer)
        if not sentences:
            return 0.0

        q_aspects = set(re.findall(r"\b\w{4,}\b", question.lower()))
        if not q_aspects:
            return 0.7

        answer_lower = answer.lower()
        covered = sum(1 for w in q_aspects if w in answer_lower)
        return covered / len(q_aspects)

    @staticmethod
    def _score_conciseness(answer: str) -> float:
        """Score answer conciseness (optimal: 20-200 words)."""
        word_count = len(answer.split())
        if 20 <= word_count <= 200:
            return 1.0
        if word_count < 20:
            return 0.7
        if word_count > 200:
            penalty = min(0.5, (word_count - 200) / 400)
            return max(0.3, 1.0 - penalty)
        return 0.5

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        from Core.constants import split_sentences
        return split_sentences(text)

    def _extract_key_words(self, text: str) -> List[str]:
        from Core.constants import extract_key_words
        return extract_key_words(text, min_length=3)

    @staticmethod
    def _has_direct_answer_pattern(answer: str, question: str) -> bool:
        answer_lower = answer.lower()
        patterns = [r"^yes[,.]", r"^no[,.]", r"^the answer is", r"^it is", r"^they are"]
        return any(re.search(p, answer_lower) for p in patterns)

    def get_statistics(self) -> Dict[str, Any]:
        if not self.evaluation_history:
            return {"message": "No evaluations yet"}

        scores = [e["scores"] for e in self.evaluation_history]
        avg_scores = {
            "overall": sum(s["overall"] for s in scores) / len(scores),
            "faithfulness": sum(s["faithfulness"] for s in scores) / len(scores),
            "relevance": sum(s["relevance"] for s in scores) / len(scores),
            "completeness": sum(s["completeness"] for s in scores) / len(scores),
            "conciseness": sum(s["conciseness"] for s in scores) / len(scores),
        }
        return {
            "total_evaluations": len(self.evaluation_history),
            "average_scores": avg_scores,
            "recent_evaluations": list(self.evaluation_history)[-10:],
        }


class RetrievalEvaluator:
    """Evaluate retrieval quality (Precision@K, Recall@K, MRR, F1)."""

    def calculate_metrics(
        self,
        retrieved_docs: List[str],
        relevant_docs: List[str],
        k: int = 5,
    ) -> Dict[str, float]:
        top_k = retrieved_docs[:k]
        relevant_in_top_k = len(set(top_k) & set(relevant_docs))
        precision_at_k = relevant_in_top_k / k if k > 0 else 0.0
        recall_at_k = relevant_in_top_k / len(relevant_docs) if relevant_docs else 0.0

        mrr = 0.0
        for i, doc in enumerate(retrieved_docs):
            if doc in relevant_docs:
                mrr = 1.0 / (i + 1)
                break

        f1 = 0.0
        if precision_at_k + recall_at_k > 0:
            f1 = 2 * (precision_at_k * recall_at_k) / (precision_at_k + recall_at_k)

        return {
            f"precision@{k}": precision_at_k,
            f"recall@{k}": recall_at_k,
            "mrr": mrr,
            "f1": f1,
        }


# Singleton instances
_answer_evaluator = None
_retrieval_evaluator = None


def get_answer_evaluator(llm_config: Optional[Dict] = None) -> AnswerEvaluator:
    global _answer_evaluator
    if _answer_evaluator is None:
        _answer_evaluator = AnswerEvaluator(llm_config)
    return _answer_evaluator


def get_retrieval_evaluator() -> RetrievalEvaluator:
    global _retrieval_evaluator
    if _retrieval_evaluator is None:
        _retrieval_evaluator = RetrievalEvaluator()
    return _retrieval_evaluator
