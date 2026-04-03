/// tests/test_core_deduplication::py — Unit tests for Core/deduplication::py
/// 
/// Tests ContentDeduplicator and SimilarityDeduplicator.

use anyhow::{Result, Context};
use crate::deduplication::{ContentDeduplicator, SimilarityDeduplicator};
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct TestContentDeduplicator {
}

impl TestContentDeduplicator {
    pub fn setup_method(&mut self) -> () {
        self.dedup = ContentDeduplicator();
    }
    pub fn test_hash_deterministic(&mut self) -> () {
        let mut h1 = self.dedup::compute_hash("hello world".to_string());
        let mut h2 = self.dedup::compute_hash("hello world".to_string());
        assert!(h1 == h2);
    }
    pub fn test_hash_case_insensitive(&mut self) -> () {
        let mut h1 = self.dedup::compute_hash("Hello World".to_string());
        let mut h2 = self.dedup::compute_hash("hello world".to_string());
        assert!(h1 == h2);
    }
    pub fn test_hash_different_texts(&mut self) -> () {
        let mut h1 = self.dedup::compute_hash("alpha".to_string());
        let mut h2 = self.dedup::compute_hash("beta".to_string());
        assert!(h1 != h2);
    }
    pub fn test_normalize_whitespace(&mut self) -> () {
        let mut result = self.dedup::_normalize_text("  hello   world  ".to_string());
        assert!(result == "hello world".to_string());
    }
    pub fn test_normalize_line_endings(&mut self) -> () {
        let mut result = self.dedup::_normalize_text("a\r\nb\rc".to_string());
        assert!(!result.contains(&"\r".to_string()));
    }
    pub fn test_add_unique(&mut self) -> () {
        self.dedup::add_document("d1".to_string(), "unique text".to_string());
        assert!(self.dedup::stats["total_processed".to_string()] == 1);
    }
    pub fn test_add_duplicate(&mut self) -> () {
        self.dedup::add_document("d1".to_string(), "same text".to_string());
        self.dedup::add_document("d2".to_string(), "same text".to_string());
        let mut dupes = self.dedup::find_duplicates();
        assert!(dupes.len() >= 1);
    }
    pub fn test_find_duplicates_none(&mut self) -> () {
        self.dedup::add_document("d1".to_string(), "alpha".to_string());
        self.dedup::add_document("d2".to_string(), "beta".to_string());
        let mut dupes = self.dedup::find_duplicates();
        assert!(dupes.len() == 0);
    }
    pub fn test_deduplicate_keep_first(&mut self) -> () {
        self.dedup::add_document("d1".to_string(), "dup text".to_string());
        self.dedup::add_document("d2".to_string(), "dup text".to_string());
        self.dedup::add_document("d3".to_string(), "unique".to_string());
        let (mut unique, mut removed) = self.dedup::deduplicate("keep_first".to_string());
        assert!(unique.len() == 2);
        assert!(removed.len() == 1);
        assert!(("d1".to_string(), "d3".to_string()).contains(&unique[0]["id".to_string()]));
    }
    pub fn test_deduplicate_keep_last(&mut self) -> () {
        self.dedup::add_document("d1".to_string(), "dup text".to_string());
        self.dedup::add_document("d2".to_string(), "dup text".to_string());
        let (mut unique, mut removed) = self.dedup::deduplicate("keep_last".to_string());
        assert!(unique.len() == 1);
        assert!(unique[0]["id".to_string()] == "d2".to_string());
    }
    pub fn test_deduplicate_keep_best(&mut self) -> () {
        self.dedup::add_document("d1".to_string(), "short".to_string(), /* metadata= */ HashMap::new());
        self.dedup::add_document("d2".to_string(), "short".to_string(), /* metadata= */ HashMap::from([("title".to_string(), "Better".to_string()), ("source".to_string(), "web".to_string())]));
        let (mut unique, mut removed) = self.dedup::deduplicate("keep_best".to_string());
        assert!(unique.len() == 1);
        assert!(unique[0]["id".to_string()] == "d2".to_string());
    }
    /// Invalid strategy falls back to default behaviour.
    pub fn test_deduplicate_invalid_strategy(&mut self) -> () {
        // Invalid strategy falls back to default behaviour.
        self.dedup::add_document("d1".to_string(), "text".to_string());
        let mut result = self.dedup::deduplicate("invalid".to_string());
        assert!(/* /* isinstance(result, tuple) */ */ true);
        assert!(result.len() == 2);
    }
    pub fn test_score_document_with_metadata(&mut self) -> () {
        let mut doc = HashMap::from([("text".to_string(), ("x".to_string() * 500)), ("metadata".to_string(), HashMap::from([("title".to_string(), "T".to_string()), ("source".to_string(), "S".to_string())]))]);
        let mut score = self.dedup::_score_document(doc);
        assert!(score > 0);
    }
    pub fn test_get_statistics(&mut self) -> () {
        self.dedup::add_document("d1".to_string(), "text".to_string());
        let mut stats = self.dedup::get_statistics();
        assert!(stats.contains(&"total_processed".to_string()));
        assert!(stats.contains(&"deduplication_rate".to_string()));
    }
}

#[derive(Debug, Clone)]
pub struct TestSimilarityDeduplicator {
}

impl TestSimilarityDeduplicator {
    pub fn test_init_threshold(&self) -> () {
        let mut sd = SimilarityDeduplicator(/* similarity_threshold= */ 0.8_f64);
        assert!(sd.threshold == 0.8_f64);
    }
    pub fn test_add_document_with_embedding(&self) -> () {
        let mut sd = SimilarityDeduplicator();
        sd.add_document("d1".to_string(), "text".to_string(), vec![0.1_f64, 0.2_f64, 0.3_f64]);
        assert!(sd.documents.len() == 1);
        assert!(sd.embeddings::len() == 1);
    }
    pub fn test_find_similar_above_threshold(&self) -> () {
        let mut sd = SimilarityDeduplicator(/* similarity_threshold= */ 0.9_f64);
        sd.add_document("d1".to_string(), "text1".to_string(), vec![1.0_f64, 0.0_f64, 0.0_f64]);
        sd.add_document("d2".to_string(), "text2".to_string(), vec![0.99_f64, 0.01_f64, 0.0_f64]);
        let mut pairs = sd.find_similar_pairs();
        assert!(pairs.len() >= 1);
    }
    pub fn test_find_similar_below_threshold(&self) -> () {
        let mut sd = SimilarityDeduplicator(/* similarity_threshold= */ 0.99_f64);
        sd.add_document("d1".to_string(), "text1".to_string(), vec![1.0_f64, 0.0_f64, 0.0_f64]);
        sd.add_document("d2".to_string(), "text2".to_string(), vec![0.0_f64, 1.0_f64, 0.0_f64]);
        let mut pairs = sd.find_similar_pairs();
        assert!(pairs.len() == 0);
    }
    pub fn test_cosine_similarity_identical(&self) -> () {
        let mut sd = SimilarityDeduplicator();
        let mut score = sd._cosine_similarity(vec![1, 0, 0], vec![1, 0, 0]);
        assert!(((score - 1.0_f64)).abs() < 0.001_f64);
    }
    pub fn test_cosine_similarity_orthogonal(&self) -> () {
        let mut sd = SimilarityDeduplicator();
        let mut score = sd._cosine_similarity(vec![1, 0, 0], vec![0, 1, 0]);
        assert!((score).abs() < 0.001_f64);
    }
    pub fn test_deduplicate_clusters(&self) -> () {
        let mut sd = SimilarityDeduplicator(/* similarity_threshold= */ 0.9_f64);
        sd.add_document("d1".to_string(), "text1".to_string(), vec![1.0_f64, 0.0_f64]);
        sd.add_document("d2".to_string(), "text2".to_string(), vec![0.99_f64, 0.01_f64]);
        sd.add_document("d3".to_string(), "text3".to_string(), vec![0.0_f64, 1.0_f64]);
        let (mut unique, mut removed) = sd.deduplicate_clusters();
        assert!((unique.len() + removed.len()) >= 0);
    }
}
