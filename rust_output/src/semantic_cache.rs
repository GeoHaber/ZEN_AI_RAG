/// Core/semantic_cache::py - Semantic caching for query results
/// 
/// Features:
/// - Cache query results based on semantic similarity
/// - TTL (time-to-live) for cache entries
/// - Cache statistics and monitoring
/// - Automatic cleanup of expired entries

use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _SEMANTIC_CACHE: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

/// Cache query results based on semantic similarity
#[derive(Debug, Clone)]
pub struct SemanticCache {
    pub cache: Vec<(np::ndarray, String, HashMap<String, Box<dyn std::any::Any>>, datetime)>,
    pub threshold: String,
    pub ttl: timedelta,
    pub max_size: String,
    pub _cleanup_interval: i64,
    pub hits: i64,
    pub misses: i64,
    pub total_lookups: i64,
}

impl SemanticCache {
    /// Initialize semantic cache
    /// 
    /// Args:
    /// similarity_threshold: Minimum similarity to consider a cache hit (0-1)
    /// ttl_hours: Time-to-live for cache entries in hours
    /// max_size: Maximum number of entries to keep in cache
    pub fn new(similarity_threshold: f64, ttl_hours: i64, max_size: i64) -> Self {
        Self {
            cache: Vec::new(),
            threshold: similarity_threshold,
            ttl: timedelta(/* hours= */ ttl_hours),
            max_size,
            _cleanup_interval: 10,
            hits: 0,
            misses: 0,
            total_lookups: 0,
        }
    }
    /// Check if similar query exists in cache
    /// 
    /// Args:
    /// query: Query text
    /// query_embedding: Query embedding vector
    /// 
    /// Returns:
    /// Cached result if found, None otherwise
    pub fn lookup(&mut self, query: String, query_embedding: np::ndarray) -> Option<HashMap<String, Box<dyn std::any::Any>>> {
        // Check if similar query exists in cache
        // 
        // Args:
        // query: Query text
        // query_embedding: Query embedding vector
        // 
        // Returns:
        // Cached result if found, None otherwise
        self.total_lookups += 1;
        if (self.total_lookups % self._cleanup_interval) == 0 {
            self._cleanup_expired();
        }
        if !self.cache {
            self.misses += 1;
            None
        }
        let mut query_norm = (query_embedding / (numpy.linalg.norm(query_embedding) + 1e-10_f64));
        let mut best_match = None;
        let mut best_similarity = 0.0_f64;
        for (cached_emb, cached_query, cached_result, timestamp) in self.cache::iter() {
            let mut similarity = numpy.dot(query_norm, (cached_emb / (numpy.linalg.norm(cached_emb) + 1e-10_f64))).to_string().parse::<f64>().unwrap_or(0.0);
            let mut similarity = 0.0_f64.max(1.0_f64.min(similarity));
            if (similarity >= self.threshold && similarity > best_similarity) {
                let mut best_match = (cached_query, cached_result, similarity);
                let mut best_similarity = similarity;
            }
        }
        if best_match {
            let (mut cached_query, mut cached_result, mut similarity) = best_match;
            self.hits += 1;
            logger.info(format!("✅ Cache HIT: '{}' → '{}' (similarity: {:.3})", query, cached_query, similarity));
            let mut result = cached_result.clone();
            result["_cache_hit".to_string()] = true;
            result["_cached_query".to_string()] = cached_query;
            result["_similarity".to_string()] = similarity;
            result
        }
        self.misses += 1;
        logger.debug(format!("❌ Cache MISS: '{}'", query));
        None
    }
    /// Store query result in cache
    /// 
    /// Args:
    /// query: Query text
    /// query_embedding: Query embedding vector
    /// result: Query result to cache
    pub fn store(&mut self, query: String, query_embedding: np::ndarray, result: HashMap<String, Box<dyn std::any::Any>>) -> () {
        // Store query result in cache
        // 
        // Args:
        // query: Query text
        // query_embedding: Query embedding vector
        // result: Query result to cache
        let mut result_clean = result.iter().iter().filter(|(k, v)| !k.starts_with(&*"_cache".to_string())).map(|(k, v)| (k, v)).collect::<HashMap<_, _>>();
        let mut q_norm = (query_embedding / (numpy.linalg.norm(query_embedding) + 1e-10_f64));
        for (cached_emb, cached_query, _, _) in self.cache::iter() {
            let mut sim = numpy.dot(q_norm, (cached_emb / (numpy.linalg.norm(cached_emb) + 1e-10_f64))).to_string().parse::<f64>().unwrap_or(0.0);
            let mut sim = 0.0_f64.max(1.0_f64.min(sim));
            if sim >= 0.99_f64 {
                logger.debug(format!("Cache skip (duplicate): '{}' ≈ '{}'", query, cached_query));
                return;
            }
        }
        self.cache::push((query_embedding, query, result_clean, datetime::now()));
        logger.debug(format!("💾 Cached result for: '{}'", query));
        if self.cache::len() > self.max_size {
            let mut removed = (self.cache::len() - self.max_size);
            self.cache = self.cache[-self.max_size..];
            logger.debug(format!("Cache size limit reached, removed {} oldest entries", removed));
        }
    }
    /// Remove expired cache entries
    pub fn _cleanup_expired(&mut self) -> () {
        // Remove expired cache entries
        let mut now = datetime::now();
        let mut original_size = self.cache::len();
        self.cache = self.cache::iter().filter(|(emb, query, result, timestamp)| (now - timestamp) < self.ttl).map(|(emb, query, result, timestamp)| (emb, query, result, timestamp)).collect::<Vec<_>>();
        let mut removed = (original_size - self.cache::len());
        if removed > 0 {
            logger.debug(format!("Removed {} expired cache entries", removed));
        }
    }
    /// Calculate cosine similarity between two vectors
    pub fn _cosine_similarity(&self, vec1: np::ndarray, vec2: np::ndarray) -> Result<f64> {
        // Calculate cosine similarity between two vectors
        // try:
        {
            let mut vec1 = numpy.array(vec1);
            let mut vec2 = numpy.array(vec2);
            let mut dot_product = numpy.dot(vec1, vec2);
            let mut norm1 = numpy.linalg.norm(vec1);
            let mut norm2 = numpy.linalg.norm(vec2);
            if (norm1 == 0 || norm2 == 0) {
                0.0_f64
            }
            let mut similarity = (dot_product / (norm1 * norm2));
            0.0_f64.max(1.0_f64.min(similarity.to_string().parse::<f64>().unwrap_or(0.0)))
        }
        // except Exception as e:
    }
    /// Get cache statistics
    /// 
    /// Returns:
    /// Dict with cache performance metrics
    pub fn get_stats(&mut self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Get cache statistics
        // 
        // Returns:
        // Dict with cache performance metrics
        let mut hit_rate = if self.total_lookups > 0 { (self.hits / self.total_lookups) } else { 0.0_f64 };
        let mut miss_rate = if self.total_lookups > 0 { (self.misses / self.total_lookups) } else { 0.0_f64 };
        HashMap::from([("hits".to_string(), self.hits), ("misses".to_string(), self.misses), ("total_lookups".to_string(), self.total_lookups), ("hit_rate".to_string(), hit_rate), ("miss_rate".to_string(), miss_rate), ("cache_size".to_string(), self.cache::len()), ("max_size".to_string(), self.max_size), ("threshold".to_string(), self.threshold), ("ttl_hours".to_string(), (self.ttl.total_seconds() / 3600))])
    }
    /// Clear all cache entries
    pub fn clear(&self) -> () {
        // Clear all cache entries
        self.cache::clear();
        logger.info("Cache cleared".to_string());
    }
    /// Reset cache statistics
    pub fn reset_stats(&mut self) -> () {
        // Reset cache statistics
        self.hits = 0;
        self.misses = 0;
        self.total_lookups = 0;
        logger.info("Cache statistics reset".to_string());
    }
    /// Get list of cached queries for debugging
    /// 
    /// Args:
    /// limit: Maximum number of queries to return
    /// 
    /// Returns:
    /// List of cached query info
    pub fn get_cached_queries(&mut self, limit: i64) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Get list of cached queries for debugging
        // 
        // Args:
        // limit: Maximum number of queries to return
        // 
        // Returns:
        // List of cached query info
        let mut queries = vec![];
        for (emb, query, result, timestamp) in self.cache[-limit..].iter() {
            queries.push(HashMap::from([("query".to_string(), query), ("timestamp".to_string(), timestamp.isoformat()), ("age_hours".to_string(), ((datetime::now() - timestamp).total_seconds() / 3600))]));
        }
        queries
    }
}

/// Get or create semantic cache instance
pub fn get_semantic_cache(similarity_threshold: f64, ttl_hours: i64) -> SemanticCache {
    // Get or create semantic cache instance
    // global/nonlocal _semantic_cache
    if _semantic_cache.is_none() {
        let mut _semantic_cache = SemanticCache(similarity_threshold, ttl_hours);
    }
    _semantic_cache
}
