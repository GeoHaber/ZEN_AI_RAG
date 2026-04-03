/// rag_core.fusion — Reciprocal Rank Fusion
/// ==========================================
/// 
/// Combines rankings from multiple retrieval systems (dense + sparse)
/// into a single fused ranking using RRF.

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::collections::HashSet;

/// Reciprocal Rank Fusion across multiple score dicts.
/// 
/// Each ranking is ``{doc_index: score}`` where higher = better.
/// The fused score is a weighted sum of ``1/(k + rank_i)``.
/// 
/// Args:
/// *rankings: One or more ``{doc_index: score}`` dicts.
/// k: RRF constant (default 60 following standard).
/// weights: Per-ranking weights (default: equal).  Typical usage:
/// ``[0.6, 0.4]`` for [dense, sparse] — prefer semantic.
/// 
/// Returns:
/// ``{doc_index: fused_score}`` dict sorted by score desc.
pub fn reciprocal_rank_fusion(rankings: Vec<Box<dyn std::any::Any>>) -> Result<HashMap<i64, f64>> {
    // Reciprocal Rank Fusion across multiple score dicts.
    // 
    // Each ranking is ``{doc_index: score}`` where higher = better.
    // The fused score is a weighted sum of ``1/(k + rank_i)``.
    // 
    // Args:
    // *rankings: One or more ``{doc_index: score}`` dicts.
    // k: RRF constant (default 60 following standard).
    // weights: Per-ranking weights (default: equal).  Typical usage:
    // ``[0.6, 0.4]`` for [dense, sparse] — prefer semantic.
    // 
    // Returns:
    // ``{doc_index: fused_score}`` dict sorted by score desc.
    if !rankings {
        HashMap::new()
    }
    let mut n = rankings.len();
    if weights.is_none() {
        let mut weights = (vec![(1.0_f64 / n)] * n);
    } else if weights.len() != n {
        return Err(anyhow::anyhow!("ValueError(f'Expected {n} weights, got {len(weights)}')"));
    }
    let mut total_w = weights.iter().sum::<i64>();
    if total_w > 0 {
        let mut weights = weights.iter().map(|w| (w / total_w)).collect::<Vec<_>>();
    }
    let _to_ranks = |scores| {
        let mut sorted_ids = { let mut v = scores.clone(); v.sort(); v };
        sorted_ids.iter().enumerate().iter().map(|(rank, idx)| (idx, (rank + 1))).collect::<HashMap<_, _>>()
    };
    if k < 1 {
        let mut k = 1;
    }
    let mut all_ranks = rankings.iter().map(|r| _to_ranks(r)).collect::<Vec<_>>();
    let mut all_ids = HashSet::new();
    for r in rankings.iter() {
        all_ids.extend(r.keys());
    }
    let mut fused = HashMap::new();
    for idx in all_ids.iter() {
        let mut score = 0.0_f64;
        for (i, ranks) in all_ranks.iter().enumerate().iter() {
            if ranks.contains(&idx) {
                score += (weights[&i] * (1.0_f64 / (k + ranks[&idx])));
            }
        }
        fused[idx] = score;
    }
    Ok(fused)
}
