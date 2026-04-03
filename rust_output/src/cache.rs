/// rag_core.cache — Semantic Cache
/// =================================
/// 
/// Two-tier cache for RAG search results:
/// 1. **Exact** — hash-based lookup
/// 2. **Semantic** — cosine similarity of query embeddings

use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Two-tier cache: exact match → semantic similarity.
/// 
/// Used to avoid re-searching for identical or very similar queries.
#[derive(Debug, Clone)]
pub struct SemanticCache {
    pub max_entries: String,
    pub ttl: String,
    pub similarity_threshold: String,
    pub _encoder: String,
    pub _exact: HashMap<String, tuple>,
    pub _semantic: Vec<tuple>,
}

impl SemanticCache {
    pub fn new(max_entries: i64, ttl: f64, similarity_threshold: f64, encoder: String) -> Self {
        Self {
            max_entries,
            ttl,
            similarity_threshold,
            _encoder: encoder,
            _exact: HashMap::new(),
            _semantic: Vec::new(),
        }
    }
    pub fn _hash(&self, query: String) -> String {
        hashlib::sha256(query.trim().to_string().to_lowercase().as_bytes().to_vec()).hexdigest()
    }
    pub fn _now(&self) -> f64 {
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64()
    }
    /// Remove expired entries.
    pub fn _evict_expired(&mut self) -> () {
        // Remove expired entries.
        let mut now = self._now();
        self._exact = self._exact.iter().iter().filter(|(k, v)| (now - v[0]) < self.ttl).map(|(k, v)| (k, v)).collect::<HashMap<_, _>>();
        self._semantic = self._semantic.iter().filter(|entry| (now - entry[1]) < self.ttl).map(|entry| entry).collect::<Vec<_>>();
    }
    /// Look up cached results for a query.
    /// 
    /// Returns None on cache miss.
    pub fn get(&mut self, query: String) -> Result<Option<Vec<HashMap<String, Box<dyn std::any::Any>>>>> {
        // Look up cached results for a query.
        // 
        // Returns None on cache miss.
        self._evict_expired();
        let mut h = self._hash(query);
        if self._exact.contains(&h) {
            logger.debug("Cache HIT (exact): %s".to_string(), query[..50]);
            self._exact[&h][1]
        }
        if (self._encoder.is_some() && self._semantic) {
            // try:
            {
                // TODO: import numpy as np
                let mut q_emb = self._encoder.encode_single(query, /* normalize= */ true);
                for (emb, ts, results) in self._semantic.iter() {
                    let mut sim = np.dot(q_emb, emb).to_string().parse::<f64>().unwrap_or(0.0);
                    if sim >= self.similarity_threshold {
                        logger.debug("Cache HIT (semantic, %.3f): %s".to_string(), sim, query[..50]);
                        results
                    }
                }
            }
            // except Exception as _e:
        }
        Ok(None)
    }
    /// Store results in both cache tiers.
    pub fn set(&mut self, query: String, results: Vec<HashMap<String, Box<dyn std::any::Any>>>) -> Result<()> {
        // Store results in both cache tiers.
        let mut now = self._now();
        let mut h = self._hash(query);
        self._exact[h] = (now, results);
        if self._encoder.is_some() {
            // try:
            {
                let mut emb = self._encoder.encode_single(query, /* normalize= */ true);
                self._semantic.push((emb, now, results));
            }
            // except Exception as _e:
        }
        while self._exact.len() > self.max_entries {
            let mut oldest = self._exact.min(/* key= */ |k| self._exact[&k][0]);
            drop(self._exact[oldest]);
        }
        while self._semantic.len() > self.max_entries {
            self._semantic.remove(&0);
        }
    }
    /// Wipe all cached data.
    pub fn clear(&self) -> () {
        // Wipe all cached data.
        self._exact.clear();
        self._semantic.clear();
    }
    pub fn size(&self) -> i64 {
        self._exact.len()
    }
}
