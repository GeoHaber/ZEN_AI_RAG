/// Demo: Quick Wins Features
/// 
/// Demonstrates the new query expansion, semantic caching, and evaluation features.

use anyhow::{Result, Context};
use crate::evaluation::{AnswerEvaluator};
use crate::query_processor::{QueryProcessor};
use crate::semantic_cache::{SemanticCache};

pub static PROCESSOR: std::sync::LazyLock<QueryProcessor> = std::sync::LazyLock::new(|| Default::default());

pub static TEST_QUERIES: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static CACHE: std::sync::LazyLock<SemanticCache> = std::sync::LazyLock::new(|| Default::default());

pub static QUERIES_AND_EMBEDDINGS: std::sync::LazyLock<Vec<serde_json::Value>> = std::sync::LazyLock::new(|| Vec::new());

pub static STATS: std::sync::LazyLock<String /* cache::get_stats */> = std::sync::LazyLock::new(|| Default::default());

pub static EVALUATOR: std::sync::LazyLock<AnswerEvaluator> = std::sync::LazyLock::new(|| Default::default());

pub static TEST_CASES: std::sync::LazyLock<Vec<HashMap<String, serde_json::Value>>> = std::sync::LazyLock::new(|| Vec::new());

pub static EVAL_STATS: std::sync::LazyLock<String /* evaluator.get_statistics */> = std::sync::LazyLock::new(|| Default::default());
