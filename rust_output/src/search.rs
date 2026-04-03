/// rag_core.search — Unified Search Result + Hybrid Searcher
/// ==========================================================
/// 
/// Combines dense retrieval, BM25, RRF fusion, and cross-encoder reranking
/// into a single, composable search pipeline.

use anyhow::{Result, Context};
use crate::bm25_index::{BM25Index};
use crate::embeddings::{EmbeddingManager};
use crate::fusion::{reciprocal_rank_fusion};
use crate::reranker::{RerankerManager};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Standard search result across all projects.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub text: String,
    pub score: f64,
    pub index: i64,
    pub metadata: HashMap<String, Box<dyn std::any::Any>>,
}

impl SearchResult {
    pub fn key(&self) -> &String {
        self.metadata.get(&"key".to_string()).cloned().unwrap_or(self.metadata.get(&"func_key".to_string()).cloned().unwrap_or("".to_string()))
    }
    pub fn name(&self) -> &String {
        self.metadata.get(&"name".to_string()).cloned().unwrap_or(self.metadata.get(&"title".to_string()).cloned().unwrap_or("".to_string()))
    }
    pub fn url(&self) -> &String {
        self.metadata.get(&"url".to_string()).cloned().unwrap_or(self.metadata.get(&"file_path".to_string()).cloned().unwrap_or("".to_string()))
    }
    pub fn to_dict(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        HashMap::from([("text".to_string(), self.text), ("score".to_string(), self.score), ("index".to_string(), self.index)])
    }
}

/// Composable hybrid search pipeline.
/// 
/// Uses whichever components are available::
/// 
/// Query  ─┬─► Dense (embedding)  ──► top-N ─┐
/// │                                   │
/// └─► BM25 (keyword)     ──► top-N ─┤
/// │
/// RRF Fusion ──► top-M
/// │
/// Cross-Encoder ──► top-K
/// 
/// All components are optional:
/// - No embeddings? BM25-only mode.
/// - No BM25? Dense-only mode.
/// - No reranker? Skip reranking.
#[derive(Debug, Clone)]
pub struct HybridSearcher {
    pub embeddings: String,
    pub bm25: String,
    pub reranker: String,
    pub rrf_k: String,
    pub dense_weight: String,
    pub _documents: Vec<HashMap<String, Box<dyn std::any::Any>>>,
    pub _doc_embeddings: Option<serde_json::Value>,
}

impl HybridSearcher {
    pub fn new(embeddings: Option<EmbeddingManager>, bm25: Option<BM25Index>, reranker: Option<RerankerManager>, rrf_k: i64, dense_weight: f64) -> Self {
        Self {
            embeddings,
            bm25,
            reranker,
            rrf_k,
            dense_weight,
            _documents: Vec::new(),
            _doc_embeddings: None,
        }
    }
    pub fn doc_count(&self) -> i64 {
        self._documents.len()
    }
    /// Index documents for searching.
    /// 
    /// Each document should have at least ``{"text": "..."}``.
    /// Additional keys become metadata.
    /// 
    /// Returns the number of documents indexed.
    pub fn index_documents(&mut self, documents: Vec<HashMap<String, Box<dyn std::any::Any>>>) -> i64 {
        // Index documents for searching.
        // 
        // Each document should have at least ``{"text": "..."}``.
        // Additional keys become metadata.
        // 
        // Returns the number of documents indexed.
        self._documents = documents;
        let mut texts = documents.iter().map(|d| d["text".to_string()]).collect::<Vec<_>>();
        if (self.embeddings && self.embeddings::is_loaded) {
            // TODO: import numpy as np
            if progress {
                progress("Encoding embeddings ...".to_string(), 0.3_f64);
            }
            let mut all_embs = vec![];
            let mut batch = 32;
            let mut total = texts.len();
            for i in (0..total).step_by(batch as usize).iter() {
                let mut chunk = texts[i..(i + batch)];
                let mut emb = self.embeddings::encode(chunk, /* batch_size= */ batch);
                all_embs.push(emb);
                if progress {
                    let mut pct = (0.3_f64 + ((0.4_f64 * (i + batch).min(total)) / total));
                    progress(format!("Embedding [{}/{}]", (i + batch).min(total), total), pct);
                }
            }
            self._doc_embeddings = if all_embs { np.vstack(all_embs) } else { None };
        }
        if self.bm25 {
            if progress {
                progress("Building BM25 index ...".to_string(), 0.75_f64);
            }
            self.bm25.build(texts);
        }
        if progress {
            progress(format!("Indexed {} documents", documents.len()), 1.0_f64);
        }
        documents.len()
    }
    /// Run the full hybrid search pipeline.
    /// 
    /// Args:
    /// query: Search query (natural language or code).
    /// top_k: Number of final results.
    /// use_reranking: Enable cross-encoder reranking.
    /// min_score: Minimum score threshold.
    /// filters: Metadata filters (exact match).
    /// 
    /// Returns:
    /// List of :class:`SearchResult` sorted by relevance.
    pub fn search(&mut self, query: String) -> Vec<SearchResult> {
        // Run the full hybrid search pipeline.
        // 
        // Args:
        // query: Search query (natural language or code).
        // top_k: Number of final results.
        // use_reranking: Enable cross-encoder reranking.
        // min_score: Minimum score threshold.
        // filters: Metadata filters (exact match).
        // 
        // Returns:
        // List of :class:`SearchResult` sorted by relevance.
        if !self._documents {
            vec![]
        }
        let mut retrieve_k = (top_k * 5).max(50);
        let mut rankings = vec![];
        let mut weights = vec![];
        if (self._doc_embeddings.is_some() && self.embeddings) {
            let mut q_vec = self.embeddings::encode_single(query, /* normalize= */ true);
            let mut sims = self.embeddings::cosine_similarity(q_vec, self._doc_embeddings);
            // TODO: import numpy as np
            let mut top_idx = np.argsort(sims)[..][..retrieve_k];
            let mut dense_scores = top_idx.iter().filter(|i| sims[&i] > 0).map(|i| (i.to_string().parse::<i64>().unwrap_or(0), sims[&i].to_string().parse::<f64>().unwrap_or(0.0))).collect::<HashMap<_, _>>();
            rankings.push(dense_scores);
            weights.push(self.dense_weight);
        }
        if (self.bm25 && self.bm25.indexed) {
            let mut bm25_scores = self.bm25.search(query, /* k= */ retrieve_k);
            rankings.push(bm25_scores);
            weights.push((1.0_f64 - self.dense_weight));
        }
        if !rankings {
            vec![]
        }
        if rankings.len() > 1 {
            let mut fused = reciprocal_rank_fusion(/* *rankings */, /* k= */ self.rrf_k, /* weights= */ weights);
        } else {
            let mut fused = rankings[0];
        }
        if filters {
            let mut fused = self._apply_filters(fused, filters);
        }
        let mut candidates_k = if use_reranking { (top_k * 3).min(20) } else { top_k };
        let mut top_indices = { let mut v = fused.clone(); v.sort(); v }[..candidates_k];
        if (use_reranking && self.reranker && self.reranker::is_loaded && top_indices.len() > top_k) {
            let mut docs_to_rerank = top_indices.iter().map(|i| self._documents[&i]["text".to_string()]).collect::<Vec<_>>();
            let mut reranked = self.reranker::rerank(query, docs_to_rerank, /* top_k= */ top_k);
            let mut top_indices = reranked.iter().map(|(orig_idx, _)| top_indices[&orig_idx]).collect::<Vec<_>>();
        }
        let mut results = vec![];
        for idx in top_indices[..top_k].iter() {
            let mut score = fused.get(&idx).cloned().unwrap_or(0.0_f64);
            if score < min_score {
                continue;
            }
            let mut doc = self._documents[&idx];
            let mut meta = doc.iter().iter().filter(|(k, v)| k != "text".to_string()).map(|(k, v)| (k, v)).collect::<HashMap<_, _>>();
            results.push(SearchResult(/* text= */ doc["text".to_string()], /* score= */ ((score as f64) * 10f64.powi(4)).round() / 10f64.powi(4), /* index= */ idx, /* metadata= */ meta));
        }
        results
    }
    /// Apply exact-match metadata filters.
    pub fn _apply_filters(&mut self, scores: HashMap<i64, f64>, filters: HashMap<String, Box<dyn std::any::Any>>) -> HashMap<i64, f64> {
        // Apply exact-match metadata filters.
        let mut filtered = HashMap::new();
        for (idx, score) in scores.iter().iter() {
            let mut doc = self._documents[&idx];
            let mut meta = doc.get(&"metadata".to_string()).cloned().unwrap_or(doc);
            let mut r#match = true;
            for (key, value) in filters.iter().iter() {
                if meta.contains(&key) {
                    if /* /* isinstance(meta[&key], list) */ */ true {
                        if !meta[&key].contains(&value) {
                            let mut r#match = false;
                        }
                    } else if meta[&key] != value {
                        let mut r#match = false;
                    }
                } else if doc.contains(&key) {
                    if doc[&key] != value {
                        let mut r#match = false;
                    }
                }
            }
            if r#match {
                filtered[idx] = score;
            }
        }
        filtered
    }
}
