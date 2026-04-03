/// Core/query_rewriter::py — LLM-powered query expansion and multi-query generation.
/// 
/// Phase 1.3 improvement: Instead of searching with the raw user query only,
/// we generate 3-5 semantically diverse reformulations and merge the result sets
/// via Reciprocal Rank Fusion. This dramatically improves recall for:
/// - Ambiguous queries ("it" / "this" / pronouns)
/// - Multi-hop questions that benefit from decomposition
/// - Non-native language queries with imprecise phrasing
/// 
/// Usage:
/// rewriter = QueryRewriter(llm_adapter=my_llm)
/// result = rewriter.rewrite("tell me about hospital beds")
/// for q in result.all_queries:
/// results_i = rag.hybrid_search(q, k=10)
/// merged = rewriter.merge_results(per_query_results, top_k=5)

use anyhow::{Result, Context};
use regex::Regex;
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _TEMPLATE_EXPANSIONS: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub const _CURRENT_YEAR: &str = "2026";

/// Generates diverse query reformulations via:
/// 1. LLM-based expansion (primary, highest recall boost)
/// 2. Template-based expansion (fast fallback)
/// 3. Passthrough (original query only, if all fails)
/// 
/// Then merges multi-query results via Reciprocal Rank Fusion.
#[derive(Debug, Clone)]
pub struct QueryRewriter {
    pub llm: String,
    pub n_rewrites: String,
    pub timeout: String,
}

impl QueryRewriter {
    /// Args:
    /// llm_adapter: Any LLM adapter with .generate(prompt) or .query_sync(prompt) method.
    /// n_rewrites: Number of reformulations to generate (default 3).
    /// timeout: Max seconds to wait for LLM response.
    pub fn new(llm_adapter: Box<dyn std::any::Any>, n_rewrites: i64, timeout: f64) -> Self {
        Self {
            llm: llm_adapter,
            n_rewrites,
            timeout,
        }
    }
    /// Generate query reformulations.
    /// 
    /// Returns QueryRewriteResult with .all_queries property for iteration.
    pub fn rewrite(&mut self, query: String) -> Result<()> {
        // Generate query reformulations.
        // 
        // Returns QueryRewriteResult with .all_queries property for iteration.
        // TODO: from Core.rag_models import QueryRewriteResult
        if (!query || !query.trim().to_string()) {
            QueryRewriteResult(/* original= */ query, /* rewrites= */ vec![], /* strategy= */ "passthrough".to_string())
        }
        if self.llm.is_some() {
            // try:
            {
                let mut rewrites = self._llm_rewrite(query);
                if rewrites {
                    QueryRewriteResult(/* original= */ query, /* rewrites= */ rewrites, /* strategy= */ "llm".to_string())
                }
            }
            // except Exception as e:
        }
        let mut rewrites = _template_rewrite(query);
        if rewrites {
            QueryRewriteResult(/* original= */ query, /* rewrites= */ rewrites, /* strategy= */ "template".to_string())
        }
        Ok(QueryRewriteResult(/* original= */ query, /* rewrites= */ vec![], /* strategy= */ "passthrough".to_string()))
    }
    /// Call LLM to generate reformulations.
    pub fn _llm_rewrite(&mut self, query: String) -> Vec<String> {
        // Call LLM to generate reformulations.
        let mut prompt = format!(self.REWRITE_PROMPT, /* query= */ query, /* n= */ self.n_rewrites);
        let mut response = "".to_string();
        if /* hasattr(self.llm, "query_sync".to_string()) */ true {
            let mut response = self.llm.query_sync(prompt, /* max_tokens= */ 200, /* temperature= */ 0.7_f64);
        } else if /* hasattr(self.llm, "generate".to_string()) */ true {
            let mut response = self.llm.generate(prompt);
        } else if callable(self.llm) {
            let mut response = self.llm(prompt);
        }
        if (!response || !response.trim().to_string()) {
            vec![]
        }
        let mut lines = response.trim().to_string().split("\n".to_string()).map(|s| s.to_string()).collect::<Vec<String>>().iter().map(|line| line.trim().to_string()).collect::<Vec<_>>();
        let mut rewrites = lines.iter().filter(|line| (line && line.len() > 5 && line.to_lowercase() != query.to_lowercase() && !line.starts_with(&*("#".to_string(), "-".to_string(), "*".to_string(), "•".to_string(), "1.".to_string(), "2.".to_string(), "3.".to_string())))).map(|line| line).collect::<Vec<_>>();
        let mut cleaned = vec![];
        for r in rewrites.iter() {
            let mut r = regex::Regex::new(&"^[\\d]+[\\.\\)]\\s*".to_string()).unwrap().replace_all(&"".to_string(), r).to_string().trim().to_string();
            let mut r = regex::Regex::new(&"^[-*•]\\s*".to_string()).unwrap().replace_all(&"".to_string(), r).to_string().trim().to_string();
            if (r && r.to_lowercase() != query.to_lowercase()) {
                cleaned.push(r);
            }
        }
        cleaned[..self.n_rewrites]
    }
    /// Merge multiple ranked result lists into one via Reciprocal Rank Fusion.
    /// 
    /// Args:
    /// per_query_results: List of result lists (one per query variant).
    /// top_k: Final number of results to return.
    /// rrf_k: RRF smoothing constant (default 60, same as pipeline).
    /// 
    /// Returns:
    /// Deduplicated, merged, and re-ranked result list.
    pub fn merge_results(per_query_results: Vec<Vec<HashMap>>, top_k: i64, rrf_k: i64) -> Vec<HashMap> {
        // Merge multiple ranked result lists into one via Reciprocal Rank Fusion.
        // 
        // Args:
        // per_query_results: List of result lists (one per query variant).
        // top_k: Final number of results to return.
        // rrf_k: RRF smoothing constant (default 60, same as pipeline).
        // 
        // Returns:
        // Deduplicated, merged, and re-ranked result list.
        if !per_query_results {
            vec![]
        }
        let mut scores = HashMap::new();
        let mut chunks_by_key = HashMap::new();
        for result_list in per_query_results.iter() {
            for (rank, chunk) in result_list.iter().enumerate().iter() {
                let mut text = chunk.get(&"text".to_string()).cloned().unwrap_or("".to_string());
                if !text {
                    continue;
                }
                let mut key = text[..200];
                let mut rrf_score = (1.0_f64 / ((rrf_k + rank) + 1));
                scores[key] = (scores.get(&key).cloned().unwrap_or(0.0_f64) + rrf_score);
                if !chunks_by_key.contains(&key) {
                    chunks_by_key[key] = chunk;
                }
            }
        }
        let mut sorted_keys = { let mut v = scores.keys().clone(); v.sort(); v };
        let mut results = vec![];
        for key in sorted_keys[..top_k].iter() {
            let mut chunk = chunks_by_key[&key].clone();
            chunk["_multi_query_rrf_score".to_string()] = scores[&key];
            results.push(chunk);
        }
        results
    }
}

/// Fast template-based rewrite when no LLM is available.
pub fn _template_rewrite(query: String) -> Vec<String> {
    // Fast template-based rewrite when no LLM is available.
    let mut rewrites = vec![];
    let mut q_lower = query.to_lowercase();
    for (pattern, templates) in _TEMPLATE_EXPANSIONS.iter().iter() {
        if regex::Regex::new(&pattern).unwrap().is_match(&q_lower) {
            let mut rest = regex::Regex::new(&pattern).unwrap().replace_all(&"".to_string(), query).to_string().trim().to_string();
            for t in templates.iter() {
                let mut rw = format!(t, /* q= */ query, /* rest= */ (rest || query), /* year= */ _CURRENT_YEAR).trim().to_string();
                if rw.to_lowercase() != query.to_lowercase() {
                    rewrites.push(rw);
                }
            }
            break;
        }
    }
    rewrites[..3]
}
