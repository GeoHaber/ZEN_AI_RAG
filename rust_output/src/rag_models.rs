/// Core/rag_models::py — Pydantic validation models for RAG data pipeline.
/// 
/// Provides validated dataclasses for:
/// - ChunkPayload: what gets stored in Qdrant per chunk
/// - RAGSearchResult: what hybrid_search() returns per result
/// - QueryRewriteResult: multi-query expansion output
/// - EvalSample: evaluation harness sample
/// 
/// Ported from ZEN_RAG.

use anyhow::{Result, Context};
use std::collections::HashSet;

/// Validated payload stored in Qdrant for each chunk.
#[derive(Debug, Clone)]
pub struct ChunkPayload {
    pub text: String,
    pub url: Option<String>,
    pub title: Option<String>,
    pub scan_root: Option<String>,
    pub chunk_index: i64,
    pub is_table: bool,
    pub sheet_name: Option<String>,
    pub parent_id: Option<String>,
    pub doc_type: Option<String>,
}

impl ChunkPayload {
    pub fn text_not_blank(v: String) -> Result<String> {
        if !v.trim().to_string() {
            return Err(anyhow::anyhow!("ValueError('Chunk text must not be blank')"));
        }
        Ok(v.trim().to_string())
    }
}

/// Validated search result returned by hybrid_search / search.
#[derive(Debug, Clone)]
pub struct RAGSearchResult {
    pub text: String,
    pub url: Option<String>,
    pub title: Option<String>,
    pub score: f64,
    pub rerank_score: Option<f64>,
    pub fusion_score: Option<f64>,
    pub is_cached: bool,
    pub parent_text: Option<String>,
    pub is_table: bool,
}

impl RAGSearchResult {
    pub fn text_not_blank(v: String) -> Result<String> {
        if !v.trim().to_string() {
            return Err(anyhow::anyhow!("ValueError('SearchResult text must not be blank')"));
        }
        Ok(v.trim().to_string())
    }
    pub fn coerce_float(v: Box<dyn std::any::Any>) -> Result<Option<f64>> {
        if v.is_none() {
            None
        }
        // try:
        {
            v.to_string().parse::<f64>().unwrap_or(0.0)
        }
        // except (TypeError, ValueError) as _e:
    }
}

/// Output of multi-query expansion.
#[derive(Debug, Clone)]
pub struct QueryRewriteResult {
    pub original: String,
    pub rewrites: Vec<String>,
    pub strategy: String,
}

impl QueryRewriteResult {
    /// Original + all rewrites (deduplicated).
    pub fn all_queries(&self) -> Vec<String> {
        // Original + all rewrites (deduplicated).
        let mut seen = HashSet::from([self.original.to_lowercase()]);
        let mut result = vec![self.original];
        for q in self.rewrites.iter() {
            if !seen.contains(&q.to_lowercase()) {
                seen.insert(q.to_lowercase());
                result.push(q);
            }
        }
        result
    }
}

/// A single evaluation sample with ground truth.
#[derive(Debug, Clone)]
pub struct EvalSample {
    pub query: String,
    pub expected_answer: String,
    pub retrieved_texts: Vec<String>,
    pub generated_answer: Option<String>,
    pub relevance_scores: Vec<f64>,
    pub ndcg: Option<f64>,
    pub mrr: Option<f64>,
}
