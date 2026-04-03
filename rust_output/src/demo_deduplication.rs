/// Demo: Deduplication System
/// 
/// Demonstrates content-based and similarity-based deduplication.

use anyhow::{Result, Context};
use crate::deduplication::{ContentDeduplicator, SimilarityDeduplicator};

pub static DEDUPLICATOR: std::sync::LazyLock<ContentDeduplicator> = std::sync::LazyLock::new(|| Default::default());

pub static DOCUMENTS: std::sync::LazyLock<Vec<HashMap<String, serde_json::Value>>> = std::sync::LazyLock::new(|| Vec::new());

pub static DUPLICATES: std::sync::LazyLock<String /* deduplicator.find_duplicates */> = std::sync::LazyLock::new(|| Default::default());

pub static STRATEGIES: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static STATS: std::sync::LazyLock<String /* deduplicator.get_statistics */> = std::sync::LazyLock::new(|| Default::default());

pub static SIM_DEDUP: std::sync::LazyLock<SimilarityDeduplicator> = std::sync::LazyLock::new(|| Default::default());

pub static NEAR_DUPLICATE_DOCS: std::sync::LazyLock<Vec<HashMap<String, serde_json::Value>>> = std::sync::LazyLock::new(|| Vec::new());

pub static SIMILAR_PAIRS: std::sync::LazyLock<String /* sim_dedup.find_similar_pairs */> = std::sync::LazyLock::new(|| Default::default());
