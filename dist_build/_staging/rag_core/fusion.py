"""
rag_core.fusion — Reciprocal Rank Fusion
==========================================

Combines rankings from multiple retrieval systems (dense + sparse)
into a single fused ranking using RRF.
"""

from __future__ import annotations

from typing import Dict, List, Optional


def reciprocal_rank_fusion(
    *rankings: Dict[int, float],
    k: int = 60,
    weights: Optional[List[float]] = None,
) -> Dict[int, float]:
    """
    Reciprocal Rank Fusion across multiple score dicts.

    Each ranking is ``{doc_index: score}`` where higher = better.
    The fused score is a weighted sum of ``1/(k + rank_i)``.

    Args:
        *rankings: One or more ``{doc_index: score}`` dicts.
        k: RRF constant (default 60 following standard).
        weights: Per-ranking weights (default: equal).  Typical usage:
                 ``[0.6, 0.4]`` for [dense, sparse] — prefer semantic.

    Returns:
        ``{doc_index: fused_score}`` dict sorted by score desc.
    """
    if not rankings:
        return {}

    n = len(rankings)
    if weights is None:
        weights = [1.0 / n] * n
    elif len(weights) != n:
        raise ValueError(f"Expected {n} weights, got {len(weights)}")

    # Normalise weights
    total_w = sum(weights)
    if total_w > 0:
        weights = [w / total_w for w in weights]

    def _to_ranks(scores: Dict[int, float]) -> Dict[int, int]:
        sorted_ids = sorted(scores, key=lambda idx: scores[idx], reverse=True)
        return {idx: rank + 1 for rank, idx in enumerate(sorted_ids)}

    # Clamp k to minimum 1 to avoid division-by-zero
    if k < 1:
        k = 1

    all_ranks = [_to_ranks(r) for r in rankings]

    all_ids: set = set()
    for r in rankings:
        all_ids.update(r.keys())

    fused: Dict[int, float] = {}
    for idx in all_ids:
        score = 0.0
        for i, ranks in enumerate(all_ranks):
            if idx in ranks:
                score += weights[i] * (1.0 / (k + ranks[idx]))
        fused[idx] = score

    return fused
