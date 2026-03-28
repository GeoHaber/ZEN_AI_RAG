"""
Core/ir_metrics.py — Information Retrieval evaluation metrics.

Ported from main-app (George branch) test_oradea_rag_comparison.py and adapted
for ZEN_AI_RAG.  All functions are pure-Python + numpy, no external services.

Metrics:
  - precision_at_k   : fraction of top-k results deemed relevant
  - mrr              : Mean Reciprocal Rank of first relevant result
  - ndcg_at_k        : Normalised Discounted Cumulative Gain
  - grounding_score  : % of answer words found in retrieved context
  - latency_percentiles : p50 / p95 / p99 from a list of timings
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence


# ─────────────────────────────────────────────────────────────────────────────
# Romanian-aware tokenisation
# ─────────────────────────────────────────────────────────────────────────────

_RO_STOP = frozenset(
    "și sau că de la în cu pe din este sunt are ca acest această "
    "the is a of in to for and or what how where when who which".split()
)

_RO_PATTERN = re.compile(r"[a-zA-ZăâîșțĂÂÎȘȚ]+")


def tokenize_ro(text: str, min_len: int = 0) -> list[str]:
    """Tokenise text preserving Romanian diacritics, lowercase."""
    return [
        w
        for w in _RO_PATTERN.findall(text.lower())
        if len(w) >= min_len and w not in _RO_STOP
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Relevance helpers
# ─────────────────────────────────────────────────────────────────────────────

def is_relevant(text: str, keywords: Sequence[str]) -> bool:
    """True if *any* keyword appears (case-insensitive) in *text*."""
    low = text.lower()
    return any(kw.lower() in low for kw in keywords)


# ─────────────────────────────────────────────────────────────────────────────
# Core IR metrics
# ─────────────────────────────────────────────────────────────────────────────

def precision_at_k(
    retrieved_texts: Sequence[str],
    keywords: Sequence[str],
    k: int = 5,
) -> float:
    """Fraction of top-k retrieved texts containing a query keyword."""
    if k <= 0:
        return 0.0
    hits = sum(1 for t in retrieved_texts[:k] if is_relevant(t, keywords))
    return hits / k


def mrr(retrieved_texts: Sequence[str], keywords: Sequence[str]) -> float:
    """Mean Reciprocal Rank — 1/rank of first relevant result."""
    for rank, text in enumerate(retrieved_texts, start=1):
        if is_relevant(text, keywords):
            return 1.0 / rank
    return 0.0


def ndcg_at_k(
    retrieved_texts: Sequence[str],
    keywords: Sequence[str],
    k: int = 5,
) -> float:
    """Binary-relevance NDCG@k."""
    def _dcg(gains: Sequence[float]) -> float:
        return sum(g / math.log2(i + 2) for i, g in enumerate(gains))

    gains = [1.0 if is_relevant(t, keywords) else 0.0 for t in retrieved_texts[:k]]
    ideal = sorted(gains, reverse=True)
    dcg_val = _dcg(gains)
    idcg_val = _dcg(ideal)
    return dcg_val / idcg_val if idcg_val > 0 else 0.0


def grounding_score(answer: str, context_texts: Sequence[str]) -> float:
    """Fraction of answer content-words found in the concatenated context."""
    a_words = set(tokenize_ro(answer, min_len=4))
    if not a_words:
        return 0.0
    ctx = " ".join(context_texts).lower()
    grounded = sum(1 for w in a_words if w in ctx)
    return grounded / len(a_words)


# ─────────────────────────────────────────────────────────────────────────────
# Latency helpers
# ─────────────────────────────────────────────────────────────────────────────

def latency_percentiles(
    timings_ms: Sequence[float],
) -> dict[str, float]:
    """Compute p50, p95, p99, mean from a list of millisecond timings."""
    if not timings_ms:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}

    s = sorted(timings_ms)
    n = len(s)

    def _pct(p: float) -> float:
        idx = int(math.ceil(p / 100.0 * n)) - 1
        return s[max(0, min(idx, n - 1))]

    return {
        "mean": sum(s) / n,
        "p50": _pct(50),
        "p95": _pct(95),
        "p99": _pct(99),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Aggregation dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EvalRow:
    """Single-question evaluation across multiple retrievers."""
    question_id: str
    question: str
    difficulty: str
    scores: dict[str, dict[str, float]] = field(default_factory=dict)
    # scores["retriever_name"] = {
    #   "precision_k": ..., "mrr": ..., "ndcg_k": ...,
    #   "grounding": ..., "latency_ms": ...,
    # }


def summarise_eval(rows: list[EvalRow], retriever_names: list[str]) -> dict[str, dict[str, float]]:
    """Compute per-retriever averages across all questions.

    Returns {retriever_name: {metric_name: avg_value}}.
    """
    metrics = ("precision_k", "mrr", "ndcg_k", "grounding", "latency_ms")
    summary: dict[str, dict[str, float]] = {}
    for name in retriever_names:
        totals = {m: 0.0 for m in metrics}
        count = 0
        for row in rows:
            if name in row.scores:
                for m in metrics:
                    totals[m] += row.scores[name].get(m, 0.0)
                count += 1
        summary[name] = {m: (totals[m] / count if count else 0.0) for m in metrics}
    return summary
