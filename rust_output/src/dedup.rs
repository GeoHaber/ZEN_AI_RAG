/// rag_core.dedup — Deduplication Manager
/// ========================================
/// 
/// Hash-based and vector-based near-duplicate detection for indexed content.

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Handles deduplication of chunks/documents before indexing.
/// 
/// Two tiers:
/// 1. **Exact** — SHA-256 content hash
/// 2. **Near-duplicate** — cosine similarity above threshold
#[derive(Debug, Clone)]
pub struct DeduplicationManager {
    pub similarity_threshold: String,
    pub _seen_hashes: HashSet<String>,
}

impl DeduplicationManager {
    pub fn new(similarity_threshold: f64) -> Self {
        Self {
            similarity_threshold,
            _seen_hashes: HashSet::new(),
        }
    }
    pub fn seen_count(&self) -> i64 {
        self._seen_hashes.len()
    }
    /// SHA-256 hash of text content.
    pub fn content_hash(&self, text: String) -> String {
        // SHA-256 hash of text content.
        hashlib::sha256(text.trim().to_string().as_bytes().to_vec()).hexdigest()
    }
    /// Check if text has been seen before (exact match).
    pub fn is_duplicate_hash(&mut self, text: String) -> bool {
        // Check if text has been seen before (exact match).
        let mut h = self.content_hash(text);
        if self._seen_hashes.contains(&h) {
            true
        }
        self._seen_hashes.insert(h);
        false
    }
    /// Check if a vector is near-duplicate of any existing vector.
    /// 
    /// Args:
    /// embedding: numpy array of shape (dim,).
    /// existing_embeddings: numpy array of shape (n, dim).
    /// 
    /// Returns:
    /// true if a near-duplicate is found.
    pub fn find_near_duplicates(&mut self, embedding: String, existing_embeddings: String) -> bool {
        // Check if a vector is near-duplicate of any existing vector.
        // 
        // Args:
        // embedding: numpy array of shape (dim,).
        // existing_embeddings: numpy array of shape (n, dim).
        // 
        // Returns:
        // true if a near-duplicate is found.
        if (existing_embeddings.is_none() || existing_embeddings.len() == 0) {
            false
        }
        // TODO: import numpy as np
        let mut sims = (existing_embeddings /* op */ embedding);
        (np.max(sims) >= self.similarity_threshold != 0)
    }
    /// Remove exact-duplicate chunks from a list.
    pub fn deduplicate_chunks(&mut self, chunks: Vec<HashMap<String, Box<dyn std::any::Any>>>) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Remove exact-duplicate chunks from a list.
        let mut unique = vec![];
        for chunk in chunks.iter() {
            let mut text = chunk.get(&"text".to_string()).cloned().unwrap_or("".to_string());
            if !self.is_duplicate_hash(text) {
                unique.push(chunk);
            }
        }
        unique
    }
    /// Clear the dedup state.
    pub fn reset(&self) -> () {
        // Clear the dedup state.
        self._seen_hashes.clear();
    }
}
