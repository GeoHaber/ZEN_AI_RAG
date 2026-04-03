/// Core/ir_metrics::py — Information Retrieval evaluation metrics.
/// 
/// Ported from main-app (George branch) test_oradea_rag_comparison.py and adapted
/// for ZEN_AI_RAG.  All functions are pure-Python + numpy, no external services.
/// 
/// Metrics:
/// - precision_at_k   : fraction of top-k results deemed relevant
/// - mrr              : Mean Reciprocal Rank of first relevant result
/// - ndcg_at_k        : Normalised Discounted Cumulative Gain
/// - grounding_score  : % of answer words found in retrieved context
/// - latency_percentiles : p50 / p95 / p99 from a list of timings

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;

pub static _RO_STOP: std::sync::LazyLock<frozenset> = std::sync::LazyLock::new(|| Default::default());

pub static _RO_PATTERN: std::sync::LazyLock<String /* re::compile */> = std::sync::LazyLock::new(|| Default::default());

/// Single-question evaluation across multiple retrievers.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvalRow {
    pub question_id: String,
    pub question: String,
    pub difficulty: String,
    pub scores: HashMap<String, HashMap<String, f64>>,
}

/// Tokenise text preserving Romanian diacritics, lowercase.
pub fn tokenize_ro(text: String, min_len: i64) -> Vec<String> {
    // Tokenise text preserving Romanian diacritics, lowercase.
    _RO_PATTERN.findall(text.to_lowercase()).iter().filter(|w| (w.len() >= min_len && !_RO_STOP.contains(&w))).map(|w| w).collect::<Vec<_>>()
}

/// true if *any* keyword appears (case-insensitive) in *text*.
pub fn is_relevant(text: String, keywords: Sequence<String>) -> bool {
    // true if *any* keyword appears (case-insensitive) in *text*.
    let mut low = text.to_lowercase();
    keywords.iter().map(|kw| low.contains(&kw.to_lowercase())).collect::<Vec<_>>().iter().any(|v| *v)
}

/// Fraction of top-k retrieved texts containing a query keyword.
pub fn precision_at_k(retrieved_texts: Sequence<String>, keywords: Sequence<String>, k: i64) -> f64 {
    // Fraction of top-k retrieved texts containing a query keyword.
    if k <= 0 {
        0.0_f64
    }
    let mut hits = retrieved_texts[..k].iter().filter(|t| is_relevant(t, keywords)).map(|t| 1).collect::<Vec<_>>().iter().sum::<i64>();
    (hits / k)
}

/// Mean Reciprocal Rank — 1/rank of first relevant result.
pub fn mrr(retrieved_texts: Sequence<String>, keywords: Sequence<String>) -> f64 {
    // Mean Reciprocal Rank — 1/rank of first relevant result.
    for (rank, text) in retrieved_texts.iter().enumerate().iter() {
        if is_relevant(text, keywords) {
            (1.0_f64 / rank)
        }
    }
    0.0_f64
}

/// Binary-relevance NDCG@k.
pub fn ndcg_at_k(retrieved_texts: Sequence<String>, keywords: Sequence<String>, k: i64) -> f64 {
    // Binary-relevance NDCG@k.
    let _dcg = |gains| {
        gains.iter().enumerate().iter().map(|(i, g)| (g / math::log2((i + 2)))).collect::<Vec<_>>().iter().sum::<i64>()
    };
    let mut gains = retrieved_texts[..k].iter().map(|t| if is_relevant(t, keywords) { 1.0_f64 } else { 0.0_f64 }).collect::<Vec<_>>();
    let mut ideal = { let mut v = gains.clone(); v.sort(); v };
    let mut dcg_val = _dcg(gains);
    let mut idcg_val = _dcg(ideal);
    if idcg_val > 0 { (dcg_val / idcg_val) } else { 0.0_f64 }
}

/// Fraction of answer content-words found in the concatenated context.
pub fn grounding_score(answer: String, context_texts: Sequence<String>) -> f64 {
    // Fraction of answer content-words found in the concatenated context.
    let mut a_words = tokenize_ro(answer, /* min_len= */ 4).into_iter().collect::<HashSet<_>>();
    if !a_words {
        0.0_f64
    }
    let mut ctx = context_texts.join(&" ".to_string()).to_lowercase();
    let mut grounded = a_words.iter().filter(|w| ctx.contains(&w)).map(|w| 1).collect::<Vec<_>>().iter().sum::<i64>();
    (grounded / a_words.len())
}

/// Compute p50, p95, p99, mean from a list of millisecond timings.
pub fn latency_percentiles(timings_ms: Sequence<f64>) -> HashMap<String, f64> {
    // Compute p50, p95, p99, mean from a list of millisecond timings.
    if !timings_ms {
        HashMap::from([("mean".to_string(), 0.0_f64), ("p50".to_string(), 0.0_f64), ("p95".to_string(), 0.0_f64), ("p99".to_string(), 0.0_f64)])
    }
    let mut s = { let mut v = timings_ms.clone(); v.sort(); v };
    let mut n = s.len();
    let _pct = |p| {
        let mut idx = (math::ceil(((p / 100.0_f64) * n)).to_string().parse::<i64>().unwrap_or(0) - 1);
        s[&0.max(idx.min((n - 1)))]
    };
    HashMap::from([("mean".to_string(), (s.iter().sum::<i64>() / n)), ("p50".to_string(), _pct(50)), ("p95".to_string(), _pct(95)), ("p99".to_string(), _pct(99))])
}

/// Compute per-retriever averages across all questions.
/// 
/// Returns {retriever_name: {metric_name: avg_value}}.
pub fn summarise_eval(rows: Vec<EvalRow>, retriever_names: Vec<String>) -> HashMap<String, HashMap<String, f64>> {
    // Compute per-retriever averages across all questions.
    // 
    // Returns {retriever_name: {metric_name: avg_value}}.
    let mut metrics = ("precision_k".to_string(), "mrr".to_string(), "ndcg_k".to_string(), "grounding".to_string(), "latency_ms".to_string());
    let mut summary = HashMap::new();
    for name in retriever_names.iter() {
        let mut totals = metrics.iter().map(|m| (m, 0.0_f64)).collect::<HashMap<_, _>>();
        let mut count = 0;
        for row in rows.iter() {
            if row.scores.contains(&name) {
                for m in metrics.iter() {
                    totals[m] += row.scores[&name].get(&m).cloned().unwrap_or(0.0_f64);
                }
                count += 1;
            }
        }
        summary[name] = metrics.iter().map(|m| (m, if count { (totals[&m] / count) } else { 0.0_f64 })).collect::<HashMap<_, _>>();
    }
    summary
}
