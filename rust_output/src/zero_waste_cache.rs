/// Core/zero_waste_cache::py — Zero-Waste Two-Tier Validation-Aware Cache
/// 
/// Inspired by: "Zero-Waste Agentic RAG: Designing Caching Architectures to
/// Minimize Latency and LLM Costs at Scale" (Partha Sarkar, TDS 2026)
/// 
/// Architecture:
/// ┌────────────────────────────────────────────────────────┐
/// │                   User Query                           │
/// │                      │                                 │
/// │          ┌───── Temporal Check ─────┐                  │
/// │          │ "latest"/"current"?      │                  │
/// │          │ YES → BYPASS all cache   │                  │
/// │          └──────────┬───────────────┘                  │
/// │                     │ NO                               │
/// │          ┌──── Tier 1: Answer Cache ────┐              │
/// │          │ cosine ≥ 0.95 against query  │              │
/// │          │ + Validate fingerprint       │              │
/// │          │ HIT → return cached answer   │              │
/// │          └──────────┬───────────────────┘              │
/// │                     │ MISS                             │
/// │          ┌──── Tier 2: Context Cache ───┐              │
/// │          │ cosine ≥ 0.70 against topic  │              │
/// │          │ + Sufficiency check          │              │
/// │          │ HIT → return cached CHUNKS   │              │
/// │          │   (skip Qdrant, re-run LLM)  │              │
/// │          └──────────┬───────────────────┘              │
/// │                     │ MISS                             │
/// │          ┌──── Full Retrieval ──────────┐              │
/// │          │ Qdrant + BM25 + Rerank       │              │
/// │          │ Store in both tiers          │              │
/// │          └──────────────────────────────┘              │
/// └────────────────────────────────────────────────────────┘
/// 
/// Staleness Prevention:
/// - Fingerprint validation: SHA-256 of source chunk texts
/// - Collection version tracking: bump on every write/delete
/// - TTL expiry: configurable per tier
/// - Temporal bypass: freshness-oriented queries skip cache
/// 
/// Usage:
/// cache = ZeroWasteCache(model, max_entries=1000)
/// 
/// # Check Tier 1 (answer-level)
/// result = cache::get_answer(query)
/// if result:
/// return result  # instant, zero LLM cost
/// 
/// # Check Tier 2 (context-level)
/// context = cache::get_context(query)
/// if context:
/// answer = llm.generate(query, context)  # fresh LLM, cached context
/// cache::set_answer(query, answer, context)
/// return answer
/// 
/// # Full retrieval
/// context = qdrant.search(query)
/// answer = llm.generate(query, context)
/// cache::set_answer(query, answer, context)
/// cache::set_context(query, context)
/// return answer

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static TEMPORAL_KEYWORDS: std::sync::LazyLock<frozenset> = std::sync::LazyLock::new(|| Default::default());

pub static _TEMPORAL_PATTERN: std::sync::LazyLock<String /* re::compile */> = std::sync::LazyLock::new(|| Default::default());

/// How to validate a cache entry before serving.
#[derive(Debug, Clone)]
pub struct CacheValidationStrategy {
}

/// SHA-256 fingerprint of source chunks for staleness detection.
/// 
/// Stores source URLs and Qdrant point IDs so validate_fn can do
/// *surgical* Qdrant queries instead of full-collection scans
/// (Article Scenario 4-6).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheFingerprint {
    pub chunk_hashes: (String, serde_json::Value),
    pub combined_hash: String,
    pub collection_version: i64,
    pub source_urls: (String, serde_json::Value),
    pub source_point_ids: (String, serde_json::Value),
    pub created_at: f64,
}

impl CacheFingerprint {
    /// Create fingerprint from a list of chunk dicts.
    /// 
    /// Extracts source URLs and point IDs when available so that
    /// the validate_fn callback can surgically query Qdrant for
    /// only the affected documents.
    pub fn from_chunks(chunks: Vec<HashMap>, collection_version: i64) -> () {
        // Create fingerprint from a list of chunk dicts.
        // 
        // Extracts source URLs and point IDs when available so that
        // the validate_fn callback can surgically query Qdrant for
        // only the affected documents.
        let mut texts = chunks.iter().map(|c| c.get(&"text".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>();
        let mut individual = /* tuple */ (texts.iter().map(|t| hashlib::sha256(t.encode("utf-8".to_string())).hexdigest()[..16]).collect::<Vec<_>>());
        let mut combined = hashlib::sha256(texts.join(&"|".to_string()).encode("utf-8".to_string())).hexdigest()[..24];
        let mut seen_urls = HashSet::new();
        let mut urls = vec![];
        for c in chunks.iter() {
            let mut u = (c.get(&"url".to_string()).cloned() || "".to_string());
            if (u && !seen_urls.contains(&u)) {
                seen_urls.insert(u);
                urls.push(u);
            }
        }
        let mut point_ids = /* tuple */ (chunks.iter().filter(|c| c.get(&"qdrant_id".to_string()).cloned()).map(|c| c["qdrant_id".to_string()].to_string()).collect::<Vec<_>>());
        cls(/* chunk_hashes= */ individual, /* combined_hash= */ combined, /* collection_version= */ collection_version, /* source_urls= */ /* tuple */ (urls), /* source_point_ids= */ point_ids)
    }
}

/// Answer-level cache entry (Tier 1).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tier1Entry {
    pub query_norm: String,
    pub query_embedding: Box<dyn std::any::Any>,
    pub results: Vec<HashMap>,
    pub fingerprint: CacheFingerprint,
    pub validation_strategy: CacheValidationStrategy,
    pub created_at: f64,
    pub hit_count: i64,
}

/// Context-level cache entry (Tier 2).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tier2Entry {
    pub query_norm: String,
    pub query_embedding: Box<dyn std::any::Any>,
    pub topic_keywords: HashSet<String>,
    pub context_chunks: Vec<HashMap>,
    pub fingerprint: CacheFingerprint,
    pub created_at: f64,
    pub hit_count: i64,
}

/// Two-tier validation-aware cache for RAG pipelines.
/// 
/// Tier 1 (Answer Cache):  cosine ≥ 0.95  → return cached final results
/// Tier 2 (Context Cache): cosine ≥ 0.70  → return cached chunks (skip Qdrant)
/// 
/// Validation: fingerprinting, temporal bypass, collection versioning, TTL.
#[derive(Debug, Clone)]
pub struct ZeroWasteCache {
    pub model: String,
    pub max_entries: String,
    pub tier1_ttl: String,
    pub tier2_ttl: String,
    pub tier1_threshold: String,
    pub tier2_threshold: String,
    pub _exact_cache: HashMap<String, Tier1Entry>,
    pub _semantic_cache: Vec<Tier1Entry>,
    pub _context_cache: Vec<Tier2Entry>,
    pub _collection_version: i64,
    pub stats: HashMap<String, serde_json::Value>,
    pub _lock: std::sync::Mutex<()>,
    pub _np: Option<serde_json::Value>,
}

impl ZeroWasteCache {
    /// Args:
    /// model: SentenceTransformer instance for embedding queries
    /// max_entries: Max entries per tier
    /// tier1_ttl: Seconds before Tier 1 entries expire (default: 1 hour)
    /// tier2_ttl: Seconds before Tier 2 entries expire (default: 2 hours)
    /// tier1_threshold: Cosine similarity threshold for answer-level cache
    /// tier2_threshold: Cosine similarity threshold for context-level cache
    pub fn new(model: String, max_entries: i64, tier1_ttl: i64, tier2_ttl: i64, tier1_threshold: f64, tier2_threshold: f64) -> Self {
        Self {
            model,
            max_entries,
            tier1_ttl,
            tier2_ttl,
            tier1_threshold,
            tier2_threshold,
            _exact_cache: HashMap::new(),
            _semantic_cache: Vec::new(),
            _context_cache: Vec::new(),
            _collection_version: 0,
            stats: HashMap::from([("tier1_exact_hits".to_string(), 0), ("tier1_semantic_hits".to_string(), 0), ("tier1_misses".to_string(), 0), ("tier2_hits".to_string(), 0), ("tier2_partial_hits".to_string(), 0), ("tier2_misses".to_string(), 0), ("temporal_bypasses".to_string(), 0), ("fingerprint_invalidations".to_string(), 0), ("version_invalidations".to_string(), 0), ("surgical_invalidations".to_string(), 0), ("aggregate_queries".to_string(), 0), ("total_queries".to_string(), 0), ("total_llm_savings".to_string(), 0), ("total_retrieval_savings".to_string(), 0)]),
            _lock: std::sync::Mutex::new(()),
            _np: None,
        }
    }
    /// Return adaptive TTL: popular entries get up to 3× the base TTL.
    pub fn _effective_ttl(&self, base_ttl: f64, hit_count: i64) -> f64 {
        // Return adaptive TTL: popular entries get up to 3× the base TTL.
        let mut boost = (hit_count * 120).min((base_ttl * 2));
        (base_ttl + boost)
    }
    /// Classify the optimal validation strategy for a query.
    /// 
    /// - TEMPORAL: freshness queries (bypass all cache)
    /// - VERSION: aggregate queries (invalidate on any collection change)
    /// - FINGERPRINT: specific queries (use chunk-level SHA-256)
    pub fn classify_strategy(&self, query: String) -> CacheValidationStrategy {
        // Classify the optimal validation strategy for a query.
        // 
        // - TEMPORAL: freshness queries (bypass all cache)
        // - VERSION: aggregate queries (invalidate on any collection change)
        // - FINGERPRINT: specific queries (use chunk-level SHA-256)
        if self.is_temporal_query(query) {
            CacheValidationStrategy.TEMPORAL
        }
        if self._AGGREGATE_PATTERN.search(query) {
            CacheValidationStrategy.VERSION
        }
        CacheValidationStrategy.FINGERPRINT
    }
    /// Surgically evict cache entries whose source docs overlap *urls*.
    /// 
    /// Returns the number of evicted entries.
    pub fn invalidate_urls(&mut self, urls: HashSet<String>) -> i64 {
        // Surgically evict cache entries whose source docs overlap *urls*.
        // 
        // Returns the number of evicted entries.
        if !urls {
            0
        }
        let mut evicted = 0;
        let _ctx = self._lock;
        {
            let mut stale_keys = self._exact_cache.iter().iter().filter(|(k, entry)| (entry.fingerprint.source_urls.into_iter().collect::<HashSet<_>>() & urls)).map(|(k, entry)| k).collect::<Vec<_>>();
            for k in stale_keys.iter() {
                drop(self._exact_cache[k]);
            }
            evicted += stale_keys.len();
            let mut before = self._semantic_cache.len();
            self._semantic_cache = self._semantic_cache.iter().filter(|e| !(e.fingerprint.source_urls.into_iter().collect::<HashSet<_>>() & urls)).map(|e| e).collect::<Vec<_>>();
            evicted += (before - self._semantic_cache.len());
            let mut before = self._context_cache.len();
            self._context_cache = self._context_cache.iter().filter(|e| !(e.fingerprint.source_urls.into_iter().collect::<HashSet<_>>() & urls)).map(|e| e).collect::<Vec<_>>();
            evicted += (before - self._context_cache.len());
            if evicted {
                logger.debug(format!("[Cache] Surgical invalidation: {} entries evicted for URLs {}...", evicted, urls.into_iter().collect::<Vec<_>>()[..3]));
            }
        }
        evicted
    }
    pub fn np(&self) -> &String {
        if self._np.is_none() {
            // TODO: import numpy as np
            self._np = np;
        }
        self._np
    }
    /// Detect if query asks for fresh/latest/current data.
    /// These queries ALWAYS bypass cache to prevent stale answers.
    /// 
    /// Scenario 3 from the article: Agentic Cache Bypass
    pub fn is_temporal_query(&self, query: String) -> bool {
        // Detect if query asks for fresh/latest/current data.
        // These queries ALWAYS bypass cache to prevent stale answers.
        // 
        // Scenario 3 from the article: Agentic Cache Bypass
        (_TEMPORAL_PATTERN.search(query) != 0)
    }
    /// Check Tier 1 (answer-level cache).
    /// 
    /// Returns cached search results if query is ≥95% similar AND source
    /// fingerprints are still valid. Returns None on miss.
    /// 
    /// Args:
    /// query: User query string
    /// validate_fn: Optional callable(fingerprint) -> bool to validate
    /// source data hasn't changed. If None, skips validation.
    /// 
    /// Returns:
    /// List of result dicts (same format as search() output) or None
    pub fn get_answer(&mut self, query: String, validate_fn: Option<callable>) -> Result<Option<Vec<HashMap>>> {
        // Check Tier 1 (answer-level cache).
        // 
        // Returns cached search results if query is ≥95% similar AND source
        // fingerprints are still valid. Returns None on miss.
        // 
        // Args:
        // query: User query string
        // validate_fn: Optional callable(fingerprint) -> bool to validate
        // source data hasn't changed. If None, skips validation.
        // 
        // Returns:
        // List of result dicts (same format as search() output) or None
        let _ctx = self._lock;
        {
            self.stats["total_queries".to_string()] += 1;
            let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            if self.is_temporal_query(query) {
                self.stats["temporal_bypasses".to_string()] += 1;
                logger.debug(format!("[Cache] Temporal bypass: '{}...'", query[..50]));
                None
            }
            let mut q_norm = query.trim().to_string().to_lowercase();
            if self._exact_cache.contains(&q_norm) {
                let mut entry = self._exact_cache[&q_norm];
                let mut effective = self._effective_ttl(self.tier1_ttl, entry.hit_count);
                if (now - entry.created_at) > effective {
                    drop(self._exact_cache[q_norm]);
                } else if self._validate_entry(entry.fingerprint, validate_fn) {
                    entry.hit_count += 1;
                    self.stats["tier1_exact_hits".to_string()] += 1;
                    self.stats["total_llm_savings".to_string()] += 1;
                    logger.debug(format!("[Cache] T1 Exact Hit: '{}...'", q_norm[..40]));
                    self._tag_results(entry.results, "tier1_exact".to_string())
                } else {
                    drop(self._exact_cache[q_norm]);
                    self.stats["fingerprint_invalidations".to_string()] += 1;
                }
            }
            if self._semantic_cache {
                // try:
                {
                    let mut q_vec = self.model.encode(vec![query], /* normalize_embeddings= */ true)[0];
                    let mut best_score = 0.0_f64;
                    let mut best_idx = -1;
                    for (i, entry) in self._semantic_cache.iter().enumerate().iter() {
                        let mut effective = self._effective_ttl(self.tier1_ttl, entry.hit_count);
                        if (now - entry.created_at) > effective {
                            continue;
                        }
                        let mut score = self.np.dot(q_vec, entry.query_embedding).to_string().parse::<f64>().unwrap_or(0.0);
                        if score > best_score {
                            let mut best_score = score;
                            let mut best_idx = i;
                        }
                    }
                    if (best_score >= self.tier1_threshold && best_idx >= 0) {
                        let mut entry = self._semantic_cache[&best_idx];
                        if self._validate_entry(entry.fingerprint, validate_fn) {
                            entry.hit_count += 1;
                            self.stats["tier1_semantic_hits".to_string()] += 1;
                            self.stats["total_llm_savings".to_string()] += 1;
                            logger.debug(format!("[Cache] T1 Semantic Hit ({:.3}): '{}' ≈ '{}'", best_score, query[..40], entry.query_norm[..40]));
                            self._tag_results(entry.results, "tier1_semantic".to_string())
                        } else {
                            self._semantic_cache.remove(&best_idx);
                            self.stats["fingerprint_invalidations".to_string()] += 1;
                        }
                    }
                }
                // except Exception as e:
            }
            self.stats["tier1_misses".to_string()] += 1;
            None
        }
    }
    /// Store answer in Tier 1 cache.
    /// 
    /// Args:
    /// query: Original user query
    /// results: Final search results to cache
    /// source_chunks: The chunks used to build this answer (for fingerprinting)
    pub fn set_answer(&mut self, query: String, results: Vec<HashMap>, source_chunks: Option<Vec<HashMap>>) -> Result<()> {
        // Store answer in Tier 1 cache.
        // 
        // Args:
        // query: Original user query
        // results: Final search results to cache
        // source_chunks: The chunks used to build this answer (for fingerprinting)
        let _ctx = self._lock;
        {
            let mut q_norm = query.trim().to_string().to_lowercase();
            let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            let mut fp = CacheFingerprint.from_chunks((source_chunks || results), /* collection_version= */ self._collection_version);
            let mut strategy = self.classify_strategy(query);
            // try:
            {
                let mut q_vec = self.model.encode(vec![query], /* normalize_embeddings= */ true)[0];
            }
            // except Exception as _e:
            let mut entry = Tier1Entry(/* query_norm= */ q_norm, /* query_embedding= */ q_vec, /* results= */ results, /* fingerprint= */ fp, /* validation_strategy= */ strategy, /* created_at= */ now);
            self._exact_cache[q_norm] = entry;
            if q_vec.is_some() {
                self._semantic_cache.push(entry);
            }
            self._prune_tier1();
        }
    }
    /// Check Tier 2 (context-level cache).
    /// 
    /// Returns cached raw chunks if query topic is ≥70% similar AND
    /// the cached context is SUFFICIENT for the new query.
    /// Returns None on miss.
    /// 
    /// This is the KEY innovation from the article: even when the specific
    /// question is different, the underlying documents are often the same.
    /// Skip Qdrant, feed cached chunks directly to LLM.
    /// 
    /// Scenario 2 + Scenario 7 from the article.
    pub fn get_context(&mut self, query: String, validate_fn: Option<callable>) -> Result<Option<Vec<HashMap>>> {
        // Check Tier 2 (context-level cache).
        // 
        // Returns cached raw chunks if query topic is ≥70% similar AND
        // the cached context is SUFFICIENT for the new query.
        // Returns None on miss.
        // 
        // This is the KEY innovation from the article: even when the specific
        // question is different, the underlying documents are often the same.
        // Skip Qdrant, feed cached chunks directly to LLM.
        // 
        // Scenario 2 + Scenario 7 from the article.
        let _ctx = self._lock;
        {
            let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            if self.is_temporal_query(query) {
                None
            }
            if !self._context_cache {
                self.stats["tier2_misses".to_string()] += 1;
                None
            }
            // try:
            {
                let mut q_vec = self.model.encode(vec![query], /* normalize_embeddings= */ true)[0];
                let mut best_score = 0.0_f64;
                let mut best_idx = -1;
                for (i, entry) in self._context_cache.iter().enumerate().iter() {
                    let mut effective = self._effective_ttl(self.tier2_ttl, entry.hit_count);
                    if (now - entry.created_at) > effective {
                        continue;
                    }
                    let mut score = self.np.dot(q_vec, entry.query_embedding).to_string().parse::<f64>().unwrap_or(0.0);
                    if score > best_score {
                        let mut best_score = score;
                        let mut best_idx = i;
                    }
                }
                if (best_score >= self.tier2_threshold && best_idx >= 0) {
                    let mut entry = self._context_cache[&best_idx];
                    if !self._validate_entry(entry.fingerprint, validate_fn) {
                        self._context_cache.remove(&best_idx);
                        self.stats["fingerprint_invalidations".to_string()] += 1;
                        self.stats["tier2_misses".to_string()] += 1;
                        None
                    }
                    if !self._is_context_sufficient(query, entry) {
                        entry.hit_count += 1;
                        self.stats["tier2_partial_hits".to_string()] += 1;
                        logger.debug(format!("[Cache] T2 Partial Hit ({:.3}): insufficient context for '{}'", best_score, query[..40]));
                        None
                    }
                    entry.hit_count += 1;
                    self.stats["tier2_hits".to_string()] += 1;
                    self.stats["total_retrieval_savings".to_string()] += 1;
                    logger.debug(format!("[Cache] T2 Context Hit ({:.3}): reusing {} chunks from '{}'", best_score, entry.context_chunks.len(), entry.query_norm[..40]));
                    entry.context_chunks.iter().map(|c| HashMap::from([("_cache_tier".to_string(), "tier2_context".to_string()), ("_cache_score".to_string(), best_score)])).collect::<Vec<_>>()
                }
            }
            // except Exception as e:
            self.stats["tier2_misses".to_string()] += 1;
            None
        }
    }
    /// Store retrieved context in Tier 2 cache.
    /// 
    /// Args:
    /// query: Original user query
    /// chunks: Raw retrieved chunks from Qdrant/BM25 (before reranking)
    pub fn set_context(&mut self, query: String, chunks: Vec<HashMap>) -> Result<()> {
        // Store retrieved context in Tier 2 cache.
        // 
        // Args:
        // query: Original user query
        // chunks: Raw retrieved chunks from Qdrant/BM25 (before reranking)
        let _ctx = self._lock;
        {
            let mut q_norm = query.trim().to_string().to_lowercase();
            let mut fp = CacheFingerprint.from_chunks(chunks, /* collection_version= */ self._collection_version);
            // try:
            {
                let mut q_vec = self.model.encode(vec![query], /* normalize_embeddings= */ true)[0];
            }
            // except Exception as _e:
            let mut keywords = self._extract_topic_keywords(query, chunks);
            let mut entry = Tier2Entry(/* query_norm= */ q_norm, /* query_embedding= */ q_vec, /* topic_keywords= */ keywords, /* context_chunks= */ chunks, /* fingerprint= */ fp);
            self._context_cache.push(entry);
            self._prune_tier2();
        }
    }
    /// Validate a cache entry's fingerprint.
    /// 
    /// Scenarios 4-6 from the article:
    /// - Collection version check (fast, O(1))
    /// - SHA-256 fingerprint comparison (via validate_fn callback)
    pub fn _validate_entry(&mut self, fingerprint: CacheFingerprint, validate_fn: Option<callable>) -> Result<bool> {
        // Validate a cache entry's fingerprint.
        // 
        // Scenarios 4-6 from the article:
        // - Collection version check (fast, O(1))
        // - SHA-256 fingerprint comparison (via validate_fn callback)
        if fingerprint.collection_version < self._collection_version {
            if validate_fn {
                // try:
                {
                    validate_fn(fingerprint)
                }
                // except Exception as _e:
            }
            self.stats["version_invalidations".to_string()] += 1;
            false
        }
        if validate_fn {
            // try:
            {
                validate_fn(fingerprint)
            }
            // except Exception as _e:
        }
        Ok(true)
    }
    /// Context Sufficiency Check (Scenario 7).
    /// 
    /// Verify that the cached context chunks contain enough information
    /// to answer the NEW query. If the new query asks about topics not
    /// covered by the cached context, return false → force fresh retrieval.
    /// 
    /// Strategy: Extract key nouns/entities from the new query and check
    /// if they appear in the cached chunks' text.
    pub fn _is_context_sufficient(&mut self, query: String, entry: Tier2Entry) -> bool {
        // Context Sufficiency Check (Scenario 7).
        // 
        // Verify that the cached context chunks contain enough information
        // to answer the NEW query. If the new query asks about topics not
        // covered by the cached context, return false → force fresh retrieval.
        // 
        // Strategy: Extract key nouns/entities from the new query and check
        // if they appear in the cached chunks' text.
        let mut new_keywords = self._extract_query_keywords(query);
        if !new_keywords {
            true
        }
        let mut cached_text = entry.context_chunks.iter().map(|c| c.get(&"text".to_string()).cloned().unwrap_or("".to_string()).to_lowercase()).collect::<Vec<_>>().join(&" ".to_string());
        let mut covered = new_keywords.iter().filter(|kw| cached_text.contains(&kw)).map(|kw| 1).collect::<Vec<_>>().iter().sum::<i64>();
        let mut coverage_ratio = if new_keywords { (covered / new_keywords.len()) } else { 1.0_f64 };
        let mut original_keywords = entry.topic_keywords;
        let mut keyword_overlap = if new_keywords { ((new_keywords & original_keywords).len() / new_keywords.len()) } else { 1.0_f64 };
        let mut is_sufficient = (coverage_ratio >= 0.6_f64 || keyword_overlap >= 0.7_f64);
        if !is_sufficient {
            logger.debug(format!("[Cache] Sufficiency FAIL: {}/{} terms covered (ratio={:.2}), keyword overlap={:.2}", covered, new_keywords.len(), coverage_ratio, keyword_overlap));
        }
        is_sufficient
    }
    /// Extract meaningful keywords from a query.
    pub fn _extract_query_keywords(&mut self, query: String) -> HashSet<String> {
        // Extract meaningful keywords from a query.
        let mut words = self._WORD_PATTERN.findall(query.to_lowercase()).into_iter().collect::<HashSet<_>>();
        (words - self._STOPWORDS)
    }
    /// Extract topic keywords from query + chunk texts.
    pub fn _extract_topic_keywords(&mut self, query: String, chunks: Vec<HashMap>) -> HashSet<String> {
        // Extract topic keywords from query + chunk texts.
        let mut keywords = self._extract_query_keywords(query);
        let mut all_text = chunks[..5].iter().map(|c| c.get(&"text".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&" ".to_string());
        let mut chunk_words = self._WORD_PATTERN.findall(all_text.to_lowercase());
        let mut chunk_words = chunk_words.iter().filter(|w| !self._STOPWORDS.contains(&w)).map(|w| w).collect::<Vec<_>>();
        if chunk_words {
            // TODO: from collections import Counter
            let mut freq = Counter(chunk_words);
            keywords.extend(freq.most_common(10).iter().map(|(w, _)| w).collect::<Vec<_>>());
        }
        keywords
    }
    /// Increment collection version after any write/delete to Qdrant.
    /// Called by build_index(), add_chunks(), delete_document_by_url().
    pub fn bump_version(&mut self) -> () {
        // Increment collection version after any write/delete to Qdrant.
        // Called by build_index(), add_chunks(), delete_document_by_url().
        let _ctx = self._lock;
        {
            self._collection_version += 1;
            logger.debug(format!("[Cache] Collection version → {}", self._collection_version));
        }
    }
    pub fn collection_version(&self) -> i64 {
        self._collection_version
    }
    /// Evict oldest entries if over capacity.
    pub fn _prune_tier1(&mut self) -> () {
        // Evict oldest entries if over capacity.
        if self._exact_cache.len() > self.max_entries {
            let mut oldest_key = self._exact_cache.min(/* key= */ |k| self._exact_cache[&k].created_at);
            drop(self._exact_cache[oldest_key]);
        }
        let mut max_semantic = (self.max_entries / 5).max(50);
        if self._semantic_cache.len() > max_semantic {
            let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            self._semantic_cache = self._semantic_cache.iter().filter(|e| (now - e.created_at) < self.tier1_ttl).map(|e| e).collect::<Vec<_>>();
            if self._semantic_cache.len() > max_semantic {
                self._semantic_cache.sort(/* key= */ |e| e.hit_count);
                self._semantic_cache = self._semantic_cache[-max_semantic..];
            }
        }
    }
    /// Evict oldest Tier 2 entries if over capacity.
    pub fn _prune_tier2(&mut self) -> () {
        // Evict oldest Tier 2 entries if over capacity.
        let mut max_context = (self.max_entries / 3).max(100);
        if self._context_cache.len() > max_context {
            let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            self._context_cache = self._context_cache.iter().filter(|e| (now - e.created_at) < self.tier2_ttl).map(|e| e).collect::<Vec<_>>();
            if self._context_cache.len() > max_context {
                self._context_cache.sort(/* key= */ |e| e.hit_count);
                self._context_cache = self._context_cache[-max_context..];
            }
        }
    }
    /// Clear all cache tiers. Called on full index rebuild.
    pub fn clear(&self) -> () {
        // Clear all cache tiers. Called on full index rebuild.
        let _ctx = self._lock;
        {
            self._exact_cache.clear();
            self._semantic_cache.clear();
            self._context_cache.clear();
            logger.debug("[Cache] All tiers cleared".to_string());
        }
    }
    /// Tag results with cache metadata for UI/logging.
    pub fn _tag_results(&self, results: Vec<HashMap>, cache_tier: String) -> Vec<HashMap> {
        // Tag results with cache metadata for UI/logging.
        results.iter().map(|r| HashMap::from([("_is_cached".to_string(), true), ("_cache_tier".to_string(), cache_tier)])).collect::<Vec<_>>()
    }
    /// Return cache performance statistics.
    pub fn get_stats(&mut self) -> HashMap {
        // Return cache performance statistics.
        let mut total = (self.stats["total_queries".to_string()] || 1);
        let mut t1_hits = (self.stats["tier1_exact_hits".to_string()] + self.stats["tier1_semantic_hits".to_string()]);
        let mut t2_hits = self.stats["tier2_hits".to_string()];
        HashMap::from([("tier1_entries".to_string(), self._exact_cache.len()), ("tier1_semantic_entries".to_string(), self._semantic_cache.len()), ("tier2_entries".to_string(), self._context_cache.len()), ("collection_version".to_string(), self._collection_version), ("tier1_hit_rate".to_string(), (t1_hits / total)), ("tier2_hit_rate".to_string(), (t2_hits / total)), ("overall_hit_rate".to_string(), ((t1_hits + t2_hits) / total)), ("cost_reduction_pct".to_string(), ((self.stats["total_llm_savings".to_string()] / total) * 100)), ("retrieval_reduction_pct".to_string(), (((self.stats["total_llm_savings".to_string()] + self.stats["total_retrieval_savings".to_string()]) / total) * 100))])
    }
    /// Human-readable cache performance summary.
    pub fn get_summary(&mut self) -> String {
        // Human-readable cache performance summary.
        let mut s = self.get_stats();
        format!("Zero-Waste Cache │ T1 hits: {}+{} │ T2 hits: {} │ Bypassed: {} │ Invalidated: {}+{} │ LLM savings: {:.1}% │ Retrieval savings: {:.1}%", s["tier1_exact_hits".to_string()], s["tier1_semantic_hits".to_string()], s["tier2_hits".to_string()], s["temporal_bypasses".to_string()], s["fingerprint_invalidations".to_string()], s["version_invalidations".to_string()], s["cost_reduction_pct".to_string()], s["retrieval_reduction_pct".to_string()])
    }
}

/// Drop-in replacement for the old SemanticCache interface.
/// 
/// The old code calls:
/// cache::get(query) → results or None
/// cache::set(query, results)
/// cache::clear()
/// 
/// This adapter maps those to ZeroWasteCache methods while enabling
/// the new Tier 2 functionality and forwarding validate_fn / source_chunks.
#[derive(Debug, Clone)]
pub struct ZeroWasteCacheAdapter {
    pub _zw: String,
}

impl ZeroWasteCacheAdapter {
    pub fn new(zero_waste: ZeroWasteCache) -> Self {
        Self {
            _zw: zero_waste,
        }
    }
    /// Tier 1 answer lookup with optional fingerprint validation.
    pub fn get(&mut self, query: String, validate_fn: Option<callable>) -> Option<Vec<HashMap>> {
        // Tier 1 answer lookup with optional fingerprint validation.
        self._zw.get_answer(query, /* validate_fn= */ validate_fn)
    }
    /// Store in Tier 1, forwarding source_chunks for proper fingerprinting.
    pub fn set(&mut self, query: String, results: Vec<HashMap>, source_chunks: Option<Vec<HashMap>>) -> () {
        // Store in Tier 1, forwarding source_chunks for proper fingerprinting.
        self._zw.set_answer(query, results, /* source_chunks= */ source_chunks);
    }
    /// Old-style clear → clear all tiers.
    pub fn clear(&self) -> () {
        // Old-style clear → clear all tiers.
        self._zw.clear();
    }
    pub fn get_context(&mut self, query: String, validate_fn: Option<callable>) -> Option<Vec<HashMap>> {
        self._zw.get_context(query, /* validate_fn= */ validate_fn)
    }
    pub fn set_context(&self, query: String, chunks: Vec<HashMap>) -> () {
        self._zw.set_context(query, chunks);
    }
    pub fn bump_version(&self) -> () {
        self._zw.bump_version();
    }
    /// Surgically invalidate cache entries whose source URLs overlap *urls*.
    /// 
    /// Returns the number of entries removed. This is much cheaper than
    /// clear() because only affected entries are evicted.
    pub fn invalidate_urls(&self, urls: HashSet<String>) -> i64 {
        // Surgically invalidate cache entries whose source URLs overlap *urls*.
        // 
        // Returns the number of entries removed. This is much cheaper than
        // clear() because only affected entries are evicted.
        self._zw.invalidate_urls(urls)
    }
    pub fn get_stats(&self) -> HashMap {
        self._zw.get_stats()
    }
    pub fn get_summary(&self) -> String {
        self._zw.get_summary()
    }
    pub fn is_zero_waste(&self) -> bool {
        true
    }
}
