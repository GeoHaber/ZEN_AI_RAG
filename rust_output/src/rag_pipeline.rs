/// rag_pipeline::py - RAG implementation with Qdrant + BM25 + Advanced Deduplication
/// 
/// Upgrades (v3.6):
/// - 4-tier SmartDeduplicator: hash + boilerplate + structural + semantic
/// - 5-factor AdvancedReranker: semantic + position + density + answer-type + source
/// - Ingestion conflict queue: HITL for conflicting chunks
/// 
/// Upgrades (v3.7 — Zero-Waste Cache, from TDS article):
/// - Tier 1 Answer Cache: cosine ≥0.95 → return cached results (zero LLM cost)
/// - Tier 2 Context Cache: cosine ≥0.70 → reuse chunks, skip Qdrant, re-rank only
/// - Temporal bypass: "latest"/"current" queries skip all cache
/// - Source fingerprinting: SHA-256 validation before serving cached data
/// - Collection version tracking: bump on write/delete for staleness detection
/// - Context sufficiency: verify cached context covers the new query's intent

use anyhow::{Result, Context};
use crate::chunker::{TextChunker, ChunkerConfig};
use crate::config_system::{config};
use crate::profiler::{profile_execution};
use regex::Regex;
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static SENTENCETRANSFORMER: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static CROSSENCODER: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static QDRANTCLIENT: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static DISTANCE: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static VECTORPARAMS: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static POINTSTRUCT: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static FILTER: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static FIELDCONDITION: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static MATCHVALUE: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static NP: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub const DEPS_AVAILABLE: bool = true;

/// Deduplication configuration - adjust per use case.
#[derive(Debug, Clone)]
pub struct DedupeConfig {
    pub SIMILARITY_THRESHOLD: f64,
    pub MIN_ENTROPY: f64,
    pub MAX_ENTROPY: f64,
    pub MIN_CHUNK_LENGTH: i64,
    pub BLACKLIST_KEYWORDS: HashSet<String>,
}

/// Multi-tier cache using both exact match and cosine similarity.
#[derive(Debug, Clone)]
pub struct SemanticCache {
    pub model: String,
    pub max_entries: String,
    pub ttl: String,
    pub threshold: String,
    pub _exact_cache: HashMap<String, serde_json::Value>,
    pub _semantic_cache: Vec<serde_json::Value>,
    pub _lock: std::sync::Mutex<()>,
}

impl SemanticCache {
    pub fn new(model: String, max_entries: i64, ttl: i64, threshold: f64) -> Self {
        Self {
            model,
            max_entries,
            ttl,
            threshold,
            _exact_cache: HashMap::new(),
            _semantic_cache: vec![],
            _lock: std::sync::Mutex::new(()),
        }
    }
    /// Retrieve results if query matches exact or semantic cache.
    /// If query_vec is provided, use it for Tier 2 to avoid encoding twice (faster).
    pub fn get(&mut self, query: String, query_vec: Box<dyn std::any::Any>) -> Result<Option<Vec<HashMap>>> {
        // Retrieve results if query matches exact or semantic cache.
        // If query_vec is provided, use it for Tier 2 to avoid encoding twice (faster).
        let _ctx = self._lock;
        {
            let mut q_norm = query.trim().to_string().to_lowercase();
            let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            if self._exact_cache.contains(&q_norm) {
                let mut entry = self._exact_cache[&q_norm];
                if (now - entry["timestamp".to_string()]) < self.ttl {
                    entry["results".to_string()]
                }
                drop(self._exact_cache[q_norm]);
            }
            if !self._semantic_cache {
                None
            }
            // try:
            {
                if query_vec.is_none() {
                    let mut query_vec = self.model.encode(vec![query], /* normalize_embeddings= */ true)[0];
                }
                for (i, (emb, _, results, ts)) in self._semantic_cache.iter().enumerate().iter() {
                    if (now - ts) > self.ttl {
                        continue;
                    }
                    let mut score = np.dot(query_vec, emb);
                    if score >= self.threshold {
                        logger.debug(format!("[Cache] Semantic Hit ({:.2}): '{}' ~= '{}'", score, query, _));
                        results
                    }
                }
            }
            // except Exception as e:
            None
        }
    }
    /// Store results in cache.
    pub fn set(&mut self, query: String, results: Vec<HashMap>) -> Result<()> {
        // Store results in cache.
        let _ctx = self._lock;
        {
            let mut q_norm = query.trim().to_string().to_lowercase();
            let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            self._exact_cache[q_norm] = HashMap::from([("results".to_string(), results), ("timestamp".to_string(), now)]);
            if self._exact_cache.len() > self.max_entries {
                drop(self._exact_cache[next(iter(self._exact_cache))]);
            }
            // try:
            {
                let mut q_vec = self.model.encode(vec![query], /* normalize_embeddings= */ true)[0];
                self._semantic_cache.push((q_vec, q_norm, results, now));
                if self._semantic_cache.len() > (self.max_entries / 5) {
                    self._semantic_cache.remove(&0);
                }
            }
            // except Exception as exc:
        }
    }
    pub fn clear(&self) -> () {
        let _ctx = self._lock;
        {
            self._exact_cache.clear();
            self._semantic_cache.clear();
        }
    }
}

/// Production-grade RAG system using Qdrant.
/// Combines Qdrant's high-performance vector search with BM25 keyword search.
#[derive(Debug, Clone)]
pub struct LocalRAG {
    pub cache_dir: String,
    pub _lock: std::sync::Mutex<()>,
    pub embedding_dim: String /* self.model.get_sentence_embedding_dimension */,
    pub collection_name: String,
    pub qdrant: String /* self._open_qdrant_with_retry */,
    pub _qdrant_is_local: bool,
    pub chunks: Vec<serde_json::Value>,
    pub chunk_hashes: HashSet<String>,
    pub bm25: Option<serde_json::Value>,
    pub cross_encoder: Option<serde_json::Value>,
    pub _tokenizer_pattern: String /* re::compile */,
    pub _ro_normalize_table: String /* str.maketrans */,
    pub chunker: TextChunker,
    pub smart_dedup: Option<serde_json::Value>,
    pub conflict_queue: Option<serde_json::Value>,
    pub advanced_reranker: Option<serde_json::Value>,
    pub index: String,
    pub model: SentenceTransformer,
    pub read_only: bool,
    pub cache: ZeroWasteCacheAdapter,
    pub _zero_waste: String,
    pub extractor: UniversalExtractor,
}

impl LocalRAG {
    pub fn new(cache_dir: Option<PathBuf>) -> Self {
        Self {
            cache_dir: (cache_dir || (config::BASE_DIR / "rag_storage".to_string())),
            _lock: std::sync::Mutex::new(()),
            embedding_dim: self.model.get_sentence_embedding_dimension(),
            collection_name: format!("zenai_knowledge_{}", self.embedding_dim),
            qdrant: self._open_qdrant_with_retry(),
            _qdrant_is_local: true,
            chunks: vec![],
            chunk_hashes: HashSet::new(),
            bm25: None,
            cross_encoder: None,
            _tokenizer_pattern: regex::Regex::new(&"\\w+".to_string()).unwrap(),
            _ro_normalize_table: str.maketrans("ăâîșțĂÂÎȘȚ".to_string(), "aaistAAIST".to_string()),
            chunker: TextChunker(),
            smart_dedup: None,
            conflict_queue: None,
            advanced_reranker: None,
            index: self,
            model: Default::default(),
            read_only: false,
            cache: Default::default(),
            _zero_waste: Default::default(),
            extractor: Default::default(),
        }
    }
    /// Lazy load heavy dependencies to prevent startup freeze.
    pub fn _lazy_load_deps(&self) -> Result<()> {
        // Lazy load heavy dependencies to prevent startup freeze.
        // global/nonlocal SentenceTransformer, CrossEncoder, QdrantClient, Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, np, DEPS_AVAILABLE
        if SentenceTransformer.is_some() {
            return;
        }
        // try:
        {
            logger.info("[RAG] Lazy loading heavy dependencies (SentenceTransformers, Qdrant)...".to_string());
            // TODO: from sentence_transformers import SentenceTransformer, CrossEncoder
            // TODO: from qdrant_client import QdrantClient
            // TODO: from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
            // TODO: import numpy as np
            let mut DEPS_AVAILABLE = true;
            logger.info("[RAG] Dependencies loaded.".to_string());
        }
        // except ImportError as e:
    }
    /// Pre-load embedding model. Reranker is lazy-loaded on first rerank() to speed up startup.
    /// 
    /// Args:
    /// include_reranker: If true, also load cross-encoder (adds ~5-15s). Default false for fast first response.
    pub fn warmup(&mut self, include_reranker: bool) -> Result<()> {
        // Pre-load embedding model. Reranker is lazy-loaded on first rerank() to speed up startup.
        // 
        // Args:
        // include_reranker: If true, also load cross-encoder (adds ~5-15s). Default false for fast first response.
        // try:
        {
            logger.info("[RAG] Warming up models...".to_string());
        }
        // except Exception as exc:
        let mut _ = self.model.encode(vec!["warmup".to_string()], /* normalize_embeddings= */ true);
        if (include_reranker && self.cross_encoder.is_none()) {
            let mut reranker_path = /* getattr */ None;
            if (reranker_path && PathBuf::from(reranker_path).expanduser().exists()) {
                let mut load_name = PathBuf::from(reranker_path).expanduser().canonicalize().unwrap_or_default().to_string();
                logger.info(format!("[RAG] Loading reranker from local path (no hub): {}", load_name));
            } else {
                let mut load_name = /* getattr */ "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1".to_string();
            }
            self.cross_encoder = CrossEncoder(load_name);
            let mut _ = self.cross_encoder.predict(vec![vec!["warmup query".to_string(), "warmup doc".to_string()]]);
        }
        Ok(logger.info("[RAG] Models warmed up and ready.".to_string()))
    }
    /// Compatibility shim for legacy FAISS tests.
    pub fn ntotal(&self) -> i64 {
        // Compatibility shim for legacy FAISS tests.
        // try:
        {
            self.qdrant.get_collection(self.collection_name).points_count
        }
        // except Exception as _e:
    }
    /// Explicitly close the Qdrant client to release storage locks.
    pub fn close(&self) -> Result<()> {
        // Explicitly close the Qdrant client to release storage locks.
        // try:
        {
            // TODO: import sys
            if sys::meta_path.is_none() {
                return;
            }
            if /* hasattr(self, "qdrant".to_string()) */ true {
                if /* hasattr(self.qdrant, "close".to_string()) */ true {
                    self.qdrant.close();
                } else if (/* hasattr(self.qdrant, "_client".to_string()) */ true && /* hasattr(self.qdrant._client, "close".to_string()) */ true) {
                    self.qdrant._client.close();
                }
                drop(self.qdrant);
            }
        }
        // except Exception as exc:
    }
    pub fn __del__(&self) -> () {
        self.close();
    }
    /// Open Qdrant local storage with retries. Handles stale lock from crashed runs.
    /// Returns QdrantClient or None if storage stays locked.
    pub fn _open_qdrant_with_retry(&mut self, max_retries: i64, retry_delay: f64) -> Result<()> {
        // Open Qdrant local storage with retries. Handles stale lock from crashed runs.
        // Returns QdrantClient or None if storage stays locked.
        let mut path_str = self.cache_dir.to_string();
        for attempt in 0..max_retries.iter() {
            // try:
            {
                QdrantClient(/* path= */ path_str)
            }
            // except Exception as e:
        }
        let mut lock_file = (self.cache_dir / ".lock".to_string());
        if lock_file.exists() {
            // try:
            {
                lock_file.remove_file().ok();
                QdrantClient(/* path= */ path_str)
            }
            // except Exception as exc:
        }
        logger.warning("[RAG] Storage LOCKED by another process; indexing disabled. Close other apps using RAG or restart.".to_string());
        Ok(None)
    }
    /// Return SearchParams(hnsw_ef=128 or 256) for better recall at search time, or None if not supported.
    pub fn _get_hnsw_ef_search(&self) -> Result<Option<Box<dyn std::any::Any>>> {
        // Return SearchParams(hnsw_ef=128 or 256) for better recall at search time, or None if not supported.
        // try:
        {
            // TODO: from qdrant_client.models import SearchParams
            let mut _big = ("1".to_string(), "true".to_string(), "yes".to_string()).contains(&std::env::var(&"RAG_RAT_QDRANT_HNSW_BIG".to_string()).unwrap_or_default().cloned().unwrap_or("".to_string()).trim().to_string().to_lowercase());
            SearchParams(/* hnsw_ef= */ if _big { 256 } else { 128 })
        }
        // except Exception as _e:
    }
    /// Initialize Qdrant collection if not exists.
    pub fn _init_collection(&mut self) -> Result<()> {
        // Initialize Qdrant collection if not exists.
        // try:
        {
            let mut collections = self.qdrant.get_collections().collections;
            let mut exists = collections::iter().map(|c| c.name == self.collection_name).collect::<Vec<_>>().iter().any(|v| *v);
            if exists {
                let mut info = self.qdrant.get_collection(self.collection_name);
                let mut current_dim = info.config::params.vectors.size;
                if current_dim != self.embedding_dim {
                    logger.warning(format!("[RAG] Dimension mismatch (Found {}, Expected {}). Recreating collection...", current_dim, self.embedding_dim));
                    self.qdrant.delete_collection(self.collection_name);
                    let mut exists = false;
                } else if !/* getattr */ true {
                    // try:
                    {
                        // TODO: from qdrant_client.models import PayloadSchemaType
                        for field in ("file_id".to_string(), "sheet_name".to_string(), "date".to_string(), "entity".to_string(), "category".to_string(), "url".to_string(), "scan_root".to_string(), "doc_type".to_string(), "domain".to_string(), "table".to_string(), "version".to_string(), "dataset".to_string(), "sheet".to_string(), "dept_name".to_string()).iter() {
                            // try:
                            {
                                self.qdrant.create_payload_index(/* collection_name= */ self.collection_name, /* field_name= */ field, /* field_schema= */ PayloadSchemaType.KEYWORD);
                            }
                            // except Exception as _e:
                        }
                    }
                    // except Exception as exc:
                }
            }
            if !exists {
                let mut vectors_config = VectorParams(/* size= */ self.embedding_dim, /* distance= */ Distance.COSINE);
                let mut create_kw = HashMap::from([("collection_name".to_string(), self.collection_name), ("vectors_config".to_string(), vectors_config)]);
                // try:
                {
                    // TODO: from qdrant_client.models import HnswConfigDiff
                    let mut _hnsw_big = ("1".to_string(), "true".to_string(), "yes".to_string()).contains(&std::env::var(&"RAG_RAT_QDRANT_HNSW_BIG".to_string()).unwrap_or_default().cloned().unwrap_or("".to_string()).trim().to_string().to_lowercase());
                    create_kw["hnsw_config".to_string()] = HnswConfigDiff(/* m= */ 16, /* ef_construct= */ if _hnsw_big { 256 } else { 128 });
                }
                // except ImportError as exc:
                // try:
                {
                    let mut _on_disk = ("1".to_string(), "true".to_string(), "yes".to_string()).contains(&std::env::var(&"RAG_RAT_QDRANT_ON_DISK_PAYLOAD".to_string()).unwrap_or_default().cloned().unwrap_or("".to_string()).trim().to_string().to_lowercase());
                    if _on_disk {
                        create_kw["on_disk_payload".to_string()] = true;
                    }
                }
                // except Exception as exc:
                self.qdrant.create_collection(/* ** */ create_kw);
                logger.info(format!("[RAG] Created Qdrant collection: {} (Cosine, HNSW m=16, ef_construct=128/256)", self.collection_name));
                if !/* getattr */ true {
                    // try:
                    {
                        // TODO: from qdrant_client.models import PayloadSchemaType
                        let mut payload_index_fields = ("file_id".to_string(), "sheet_name".to_string(), "date".to_string(), "entity".to_string(), "category".to_string(), "url".to_string(), "scan_root".to_string(), "doc_type".to_string(), "domain".to_string(), "table".to_string(), "version".to_string(), "dataset".to_string(), "sheet".to_string(), "dept_name".to_string());
                        for field in payload_index_fields.iter() {
                            // try:
                            {
                                self.qdrant.create_payload_index(/* collection_name= */ self.collection_name, /* field_name= */ field, /* field_schema= */ PayloadSchemaType.KEYWORD);
                            }
                            // except Exception as exc:
                        }
                        logger.info("[RAG] Payload indexes created (server Qdrant): file_id, sheet_name, date, entity, category, ...".to_string());
                    }
                    // except Exception as idx_err:
                } else {
                    logger.debug("[RAG] Payload indexes skipped (local Qdrant). Use server Qdrant if you need payload indexes.".to_string());
                }
            }
        }
        // except Exception as e:
    }
    /// Load all metadata from Qdrant (paginated) to populate hash and BM25 buffers.
    /// Ensures search can detect all documents from the loaded vector DB.
    pub fn _load_metadata(&mut self) -> Result<()> {
        // Load all metadata from Qdrant (paginated) to populate hash and BM25 buffers.
        // Ensures search can detect all documents from the loaded vector DB.
        if !self.qdrant {
            logger.warning("[RAG] Storage locked: Metadata secondary buffers will be empty.".to_string());
            return;
        }
        // try:
        {
            self.chunks = vec![];
            self.chunk_hashes = HashSet::new();
            let mut offset = None;
            let mut batch_size = 2000;
            while true {
                let (mut points, mut offset) = self.qdrant.scroll(/* collection_name= */ self.collection_name, /* limit= */ batch_size, /* offset= */ offset, /* with_payload= */ true, /* with_vectors= */ false);
                if !points {
                    break;
                }
                for p in points.iter() {
                    let mut payload = (p.payload || HashMap::new());
                    let mut text = payload.get(&"text".to_string()).cloned().unwrap_or("".to_string());
                    let mut text_hash = hashlib::sha256(text.as_bytes().to_vec()).hexdigest();
                    let mut chunk = HashMap::from([("text".to_string(), text), ("url".to_string(), payload.get(&"url".to_string()).cloned()), ("title".to_string(), payload.get(&"title".to_string()).cloned()), ("scan_root".to_string(), payload.get(&"scan_root".to_string()).cloned()), ("hash".to_string(), text_hash), ("qdrant_id".to_string(), p.id)]);
                    if payload.get(&"is_table".to_string()).cloned() {
                        chunk["is_table".to_string()] = true;
                        if payload.get(&"sheet_name".to_string()).cloned().is_some() {
                            chunk["sheet_name".to_string()] = payload.get(&"sheet_name".to_string()).cloned();
                        }
                        if payload.get(&"columns".to_string()).cloned().is_some() {
                            chunk["columns".to_string()] = payload.get(&"columns".to_string()).cloned();
                        }
                    }
                    for key in ("file_id".to_string(), "dataset".to_string(), "sheet".to_string(), "sheet_name".to_string(), "date".to_string(), "entity".to_string(), "category".to_string(), "dept_name".to_string(), "dept_id".to_string(), "beds_real".to_string(), "beds_struct".to_string(), "patients_present".to_string(), "free_beds".to_string(), "source_file".to_string(), "source_sheet".to_string(), "row_index".to_string(), "unit".to_string()).iter() {
                        if payload.contains(&key) {
                            chunk[key] = payload[&key];
                        }
                    }
                    self.chunks.push(chunk);
                    self.chunk_hashes.insert(text_hash);
                }
                if offset.is_none() {
                    break;
                }
            }
            if self.chunks {
                if !self._load_bm25_from_disk() {
                    self._rebuild_bm25();
                }
                logger.info(format!("[RAG] Loaded {} chunks into search buffers (all from vector DB)", self.chunks.len()));
            }
        }
        // except Exception as e:
    }
    /// Tokenizer for BM25: lowercase + normalize Romanian diacritics so semantic/key matching works across wording.
    pub fn _tokenize(&mut self, text: String) -> Vec<String> {
        // Tokenizer for BM25: lowercase + normalize Romanian diacritics so semantic/key matching works across wording.
        if !text {
            vec![]
        }
        let mut lower = text.to_lowercase();
        let mut normalized = lower.translate(self._ro_normalize_table);
        self._tokenizer_pattern.findall(normalized)
    }
    /// Rebuild BM25 index for keyword search.
    pub fn _rebuild_bm25(&mut self) -> Result<()> {
        // Rebuild BM25 index for keyword search.
        if (!BM25_AVAILABLE || !self.chunks) {
            return;
        }
        // try:
        {
            let mut tokenized_corpus = self.chunks.iter().map(|c| self._tokenize(c["text".to_string()])).collect::<Vec<_>>();
            self.bm25 = BM25Okapi(tokenized_corpus);
            logger.debug(format!("[RAG] BM25 Index rebuilt with {} items", self.chunks.len()));
            // try:
            {
                self._save_bm25();
            }
            // except Exception as save_err:
        }
        // except Exception as e:
    }
    /// Persist BM25 index + fingerprint to disk to avoid full rebuild on every restart.
    pub fn _save_bm25(&mut self) -> Result<()> {
        // Persist BM25 index + fingerprint to disk to avoid full rebuild on every restart.
        // TODO: import pickle
        let mut bm25_path = (self.cache_dir / "bm25_index::pkl".to_string());
        let mut fp_path = (self.cache_dir / "bm25_fingerprint.txt".to_string());
        let mut fingerprint = hashlib::sha256({ let mut v = self.chunks.iter().map(|c| c.get(&"hash".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().clone(); v.sort(); v }.join(&"".to_string()).as_bytes().to_vec()).hexdigest();
        let mut f = File::open(bm25_path)?;
        {
            pickle::dump(self.bm25, f, /* protocol= */ 4);
        }
        fp_pathstd::fs::write(&fingerprint));
        Ok(logger.debug(format!("[RAG] BM25 index persisted ({} docs, fp={})", self.chunks.len(), fingerprint[..8])))
    }
    /// Load BM25 from disk if fingerprint matches current chunk hashes. Returns true if loaded.
    pub fn _load_bm25_from_disk(&mut self) -> Result<bool> {
        // Load BM25 from disk if fingerprint matches current chunk hashes. Returns true if loaded.
        // TODO: import pickle
        let mut bm25_path = (self.cache_dir / "bm25_index::pkl".to_string());
        let mut fp_path = (self.cache_dir / "bm25_fingerprint.txt".to_string());
        if (!bm25_path.exists() || !fp_path.exists()) {
            false
        }
        // try:
        {
            let mut current_fp = hashlib::sha256({ let mut v = self.chunks.iter().map(|c| c.get(&"hash".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().clone(); v.sort(); v }.join(&"".to_string()).as_bytes().to_vec()).hexdigest();
            let mut saved_fp = fp_path.read_to_string()).trim().to_string();
            if current_fp != saved_fp {
                logger.debug("[RAG] BM25 fingerprint mismatch — rebuilding from scratch.".to_string());
                false
            }
            let mut f = File::open(bm25_path)?;
            {
                self.bm25 = pickle::load(f);
            }
            logger.info(format!("[RAG] BM25 loaded from disk ({} docs). Startup time saved!", self.chunks.len()));
            true
        }
        // except Exception as e:
    }
    /// Compatibility delegator for tests.
    pub fn _calculate_entropy(&self, text: String) -> f64 {
        // Compatibility delegator for tests.
        self.chunker::_calculate_entropy(text)
    }
    /// Detect junk chunks using unified chunker.
    pub fn _is_junk_chunk(&self, text: String) -> bool {
        // Detect junk chunks using unified chunker.
        self.chunker::is_junk(text)
    }
    /// Check Qdrant for semantic near-duplicates.
    pub fn _find_near_duplicate(&mut self, embedding: String, threshold: f64) -> Result<bool> {
        // Check Qdrant for semantic near-duplicates.
        // try:
        {
            let mut results = self.qdrant.query_points(/* collection_name= */ self.collection_name, /* query= */ embedding.tolist(), /* limit= */ 1, /* score_threshold= */ threshold).points;
            results.len() > 0
        }
        // except Exception as _e:
    }
    /// Split documents into chunks. Excel sheets (is_table) are kept as one chunk per sheet (vector table).
    pub fn chunk_documents(&mut self, documents: Vec<HashMap>, chunk_size: i64, overlap: i64, filter_junk: bool) -> Vec<HashMap> {
        // Split documents into chunks. Excel sheets (is_table) are kept as one chunk per sheet (vector table).
        let mut all_chunks = vec![];
        self.chunker::config::CHUNK_SIZE = chunk_size;
        self.chunker::config::CHUNK_OVERLAP = overlap;
        for doc in documents.iter() {
            let mut content = doc.get(&"content".to_string()).cloned().unwrap_or("".to_string());
            if (!content || !content.trim().to_string()) {
                continue;
            }
            let mut base_meta = HashMap::from([("url".to_string(), doc.get(&"url".to_string()).cloned()), ("title".to_string(), doc.get(&"title".to_string()).cloned()), ("scan_root".to_string(), doc.get(&"scan_root".to_string()).cloned()), ("is_table".to_string(), doc.get(&"is_table".to_string()).cloned()), ("sheet_name".to_string(), doc.get(&"sheet_name".to_string()).cloned()), ("columns".to_string(), doc.get(&"columns".to_string()).cloned())]);
            if (doc.get(&"excel_row".to_string()).cloned() || doc.get(&"is_table".to_string()).cloned()) {
                let mut text = content.trim().to_string();
                if !text {
                    continue;
                }
                let mut chunk_meta = HashMap::from([("url".to_string(), base_meta["url".to_string()]), ("title".to_string(), base_meta["title".to_string()]), ("scan_root".to_string(), base_meta["scan_root".to_string()]), ("is_table".to_string(), true), ("sheet_name".to_string(), base_meta.get(&"sheet_name".to_string()).cloned()), ("columns".to_string(), base_meta.get(&"columns".to_string()).cloned()), ("text".to_string(), text), ("chunk_index".to_string(), doc.get(&"row_index".to_string()).cloned().unwrap_or(0))]);
                if doc.get(&"excel_row".to_string()).cloned() {
                    chunk_meta["excel_row".to_string()] = true;
                    for key in EXCEL_ROW_PAYLOAD_KEYS.iter() {
                        if doc.contains(&key) {
                            chunk_meta[key] = doc[&key];
                        }
                    }
                } else {
                    let mut max_table_chars = /* getattr */ 80000;
                    if (max_table_chars && text.len() > max_table_chars) {
                        chunk_meta["text".to_string()] = (text[..max_table_chars] + "\n\n[... truncated ...]".to_string());
                    }
                }
                all_chunks.push(chunk_meta);
                continue;
            }
            let mut meta = base_meta.iter().iter().filter(|(k, v)| ("url".to_string(), "title".to_string(), "scan_root".to_string()).contains(&k)).map(|(k, v)| (k, v)).collect::<HashMap<_, _>>();
            let mut doc_chunks = self.chunker::chunk_document(content, /* metadata= */ meta, /* strategy= */ config::rag.chunk_strategy, /* filter_junk= */ filter_junk, /* model= */ self.model);
            for c in doc_chunks.iter() {
                let mut chunk_text = c.text.trim().to_string();
                if !self.chunker::is_junk(chunk_text) {
                    all_chunks.push(HashMap::from([("url".to_string(), c.metadata.get(&"url".to_string()).cloned()), ("title".to_string(), c.metadata.get(&"title".to_string()).cloned()), ("scan_root".to_string(), c.metadata.get(&"scan_root".to_string()).cloned()), ("text".to_string(), chunk_text), ("chunk_index".to_string(), c.chunk_index)]));
                }
            }
        }
        all_chunks
    }
    /// true if url is under scan_root (filesystem paths only); always true for URLs or missing root.
    pub fn _url_under_scan_root(url: String, scan_root: Option<String>) -> Result<bool> {
        // true if url is under scan_root (filesystem paths only); always true for URLs or missing root.
        if (!scan_root || !url || url.starts_with(&*"http".to_string()) || scan_root.starts_with(&*"http".to_string())) {
            true
        }
        // try:
        {
            let mut u = PathBuf::from(url).canonicalize().unwrap_or_default();
            let mut r = PathBuf::from(scan_root).canonicalize().unwrap_or_default();
            (u == r || u.parents.contains(&r))
        }
        // except (OSError, ValueError) as _e:
    }
    /// Build/update Qdrant index with new documents.
    /// 
    /// Uses SmartDeduplicator (4-tier) when available, otherwise falls back
    /// to the original hash + cosine dedup. Conflicts detected during
    /// ingestion are queued for Human-in-the-Loop review.
    /// Only indexes docs whose url is under scan_root.
    pub fn build_index(&mut self, documents: Vec<HashMap>, dedup_threshold: Option<f64>, filter_junk: bool) -> () {
        // Build/update Qdrant index with new documents.
        // 
        // Uses SmartDeduplicator (4-tier) when available, otherwise falls back
        // to the original hash + cosine dedup. Conflicts detected during
        // ingestion are queued for Human-in-the-Loop review.
        // Only indexes docs whose url is under scan_root.
        if !self.qdrant {
            logger.warning("[RAG] Skipping indexing: Storage is LOCKED or not initialized.".to_string());
            return;
        }
        self._init_collection();
        let _ctx = self._lock;
        {
            self.cache::clear();
            let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            let mut threshold = (dedup_threshold || DedupeConfig.SIMILARITY_THRESHOLD);
            let mut docs_processed = 0;
            let mut chunks_added = 0;
            let mut total_chunks_from_docs = 0;
            let mut skipped_hash = 0;
            let mut skipped_near_dup = 0;
            let mut skipped_boilerplate = 0;
            let mut conflicts_found = 0;
            // TODO: import uuid
            let mut use_smart = self.smart_dedup.is_some();
            if use_smart {
                self.smart_dedup.clear();
                for ch in self.chunks.iter() {
                    self.smart_dedup._hash_cache.insert(ch.get(&"hash".to_string()).cloned().unwrap_or("".to_string()));
                }
            }
            for doc in documents.iter() {
                if !self._url_under_scan_root(doc.get(&"url".to_string()).cloned().unwrap_or("".to_string()), doc.get(&"scan_root".to_string()).cloned()) {
                    logger.warning("[RAG] Skipping doc outside scan root: url=%s scan_root=%s".to_string(), doc.get(&"url".to_string()).cloned(), doc.get(&"scan_root".to_string()).cloned());
                    continue;
                }
                let mut doc_chunks = self.chunk_documents(vec![doc], /* filter_junk= */ filter_junk);
                if !doc_chunks {
                    continue;
                }
                total_chunks_from_docs += doc_chunks.len();
                docs_processed += 1;
                let mut BATCH_SIZE = 32;
                for i in (0..doc_chunks.len()).step_by(BATCH_SIZE as usize).iter() {
                    let mut batch = doc_chunks[i..(i + BATCH_SIZE)];
                    let mut texts = batch.iter().map(|c| c["text".to_string()]).collect::<Vec<_>>();
                    let mut embeddings = self.model.encode(texts, /* normalize_embeddings= */ true);
                    let mut points = vec![];
                    for (chunk, embedding) in batch.iter().zip(embeddings::iter()).iter() {
                        let mut text = chunk["text".to_string()];
                        let mut text_hash = hashlib::sha256(text.as_bytes().to_vec()).hexdigest();
                        let mut is_table_row = (chunk.get(&"excel_row".to_string()).cloned() || chunk.get(&"row_index".to_string()).cloned().is_some());
                        if is_table_row {
                            if self.chunk_hashes.contains(&text_hash) {
                                skipped_hash += 1;
                                continue;
                            }
                        } else if use_smart {
                            let mut result = self.smart_dedup.should_skip_chunk(/* text= */ text, /* embedding= */ embedding, /* source_url= */ chunk.get(&"url".to_string()).cloned(), /* title= */ chunk.get(&"title".to_string()).cloned());
                            if result.should_skip {
                                let mut reason = result.reason;
                                if reason == "exact_duplicate".to_string() {
                                    skipped_hash += 1;
                                } else if ("boilerplate".to_string(), "structural".to_string(), "repetitive".to_string()).contains(&reason) {
                                    skipped_boilerplate += 1;
                                } else {
                                    skipped_near_dup += 1;
                                }
                                continue;
                            }
                            if (result.conflict && self.conflict_queue) {
                                self.conflict_queue.insert(result.conflict);
                                conflicts_found += 1;
                            }
                        } else {
                            if self.chunk_hashes.contains(&text_hash) {
                                skipped_hash += 1;
                                continue;
                            }
                            if self._find_near_duplicate(embedding, threshold) {
                                skipped_near_dup += 1;
                                continue;
                            }
                        }
                        let mut unique_seed = (text_hash + /* uuid */ "00000000-0000-0000-0000-000000000000".to_string().to_string());
                        let mut point_id = int(hashlib::md5(unique_seed.as_bytes().to_vec()).hexdigest()[..16], 16);
                        let mut payload = HashMap::from([("text".to_string(), text), ("url".to_string(), chunk.get(&"url".to_string()).cloned()), ("title".to_string(), chunk.get(&"title".to_string()).cloned()), ("scan_root".to_string(), chunk.get(&"scan_root".to_string()).cloned())]);
                        if chunk.get(&"parent_text".to_string()).cloned() {
                            payload["parent_text".to_string()] = chunk["parent_text".to_string()];
                        }
                        if chunk.get(&"parent_id".to_string()).cloned() {
                            payload["parent_id".to_string()] = chunk["parent_id".to_string()];
                        }
                        if chunk.get(&"is_table".to_string()).cloned() {
                            payload["is_table".to_string()] = true;
                            if chunk.get(&"sheet_name".to_string()).cloned().is_some() {
                                payload["sheet_name".to_string()] = chunk.get(&"sheet_name".to_string()).cloned();
                            }
                            if chunk.get(&"columns".to_string()).cloned().is_some() {
                                payload["columns".to_string()] = chunk.get(&"columns".to_string()).cloned();
                            }
                        }
                        if chunk.get(&"excel_row".to_string()).cloned() {
                            for key in EXCEL_ROW_PAYLOAD_KEYS.iter() {
                                if chunk.contains(&key) {
                                    payload[key] = chunk[&key];
                                }
                            }
                        }
                        points.push(PointStruct(/* id= */ point_id, /* vector= */ embedding.tolist(), /* payload= */ payload));
                        self.chunk_hashes.insert(text_hash);
                        self.chunks.push(HashMap::from([("text".to_string(), text), ("url".to_string(), chunk.get(&"url".to_string()).cloned()), ("title".to_string(), chunk.get(&"title".to_string()).cloned()), ("scan_root".to_string(), chunk.get(&"scan_root".to_string()).cloned()), ("hash".to_string(), text_hash), ("qdrant_id".to_string(), point_id)]));
                    }
                    if points {
                        self.qdrant.upsert(/* collection_name= */ self.collection_name, /* points= */ points);
                        chunks_added += points.len();
                    }
                }
            }
            self._rebuild_bm25();
            let mut total_time = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
            if (chunks_added > 0 && /* hasattr(self.cache, "bump_version".to_string()) */ true) {
                self.cache::bump_version();
            }
            logger.info(format!("[RAG] Ingested {} chunks to Qdrant in {:.2}s", chunks_added, total_time));
            if use_smart {
                let mut stats = self.smart_dedup.get_stats();
                logger.info(format!("[RAG] Dedup stats: {} kept, {} exact-dup, {} boilerplate, {} structural, {} semantic-dup, {} conflicts queued", stats.get(&"kept".to_string()).cloned().unwrap_or(0), stats.get(&"exact_duplicates".to_string()).cloned().unwrap_or(0), stats.get(&"boilerplate".to_string()).cloned().unwrap_or(0), stats.get(&"structural".to_string()).cloned().unwrap_or(0), stats.get(&"semantic_duplicates".to_string()).cloned().unwrap_or(0), stats.get(&"conflicts_detected".to_string()).cloned().unwrap_or(0)));
            }
            if (conflicts_found > 0 && self.conflict_queue) {
                logger.info(format!("[RAG] ⚠ {} potential conflicts detected. Review in Settings → Conflict Resolution.", conflicts_found));
            }
            if (chunks_added == 0 && documents) {
                logger.warning("[RAG] Ingested 0 chunks: %d doc(s) → %d chunk(s) from chunker; skipped %d exact-dup, %d boilerplate/structural, %d near-dup. If re-indexing same content, this is normal.".to_string(), documents.len(), total_chunks_from_docs, skipped_hash, skipped_boilerplate, skipped_near_dup);
            }
        }
    }
    /// Add pre-chunked content with deduplication.
    pub fn add_chunks(&mut self, chunks: Vec<HashMap>, dedup_threshold: Option<f64>) -> () {
        // Add pre-chunked content with deduplication.
        if !self.qdrant {
            logger.warning("[RAG] Skipping chunk addition: Storage is LOCKED or not initialized.".to_string());
            return;
        }
        let _ctx = self._lock;
        {
            let mut threshold = (dedup_threshold || DedupeConfig.SIMILARITY_THRESHOLD);
            let mut points = vec![];
            // TODO: import uuid
            for chunk in chunks.iter() {
                let mut text = chunk.get(&"text".to_string()).cloned().unwrap_or("".to_string());
                if !text {
                    continue;
                }
                if self._is_junk_chunk(text) {
                    continue;
                }
                let mut text_hash = hashlib::sha256(text.as_bytes().to_vec()).hexdigest();
                if self.chunk_hashes.contains(&text_hash) {
                    continue;
                }
                let mut embedding = self.model.encode(vec![text], /* normalize_embeddings= */ true)[0];
                if self._find_near_duplicate(embedding, threshold) {
                    continue;
                }
                let mut unique_seed = (text_hash + /* uuid */ "00000000-0000-0000-0000-000000000000".to_string().to_string());
                let mut point_id = int(hashlib::md5(unique_seed.as_bytes().to_vec()).hexdigest()[..16], 16);
                points.push(PointStruct(/* id= */ point_id, /* vector= */ embedding.tolist(), /* payload= */ HashMap::from([("text".to_string(), text), ("url".to_string(), chunk.get(&"url".to_string()).cloned()), ("title".to_string(), chunk.get(&"title".to_string()).cloned()), ("scan_root".to_string(), chunk.get(&"scan_root".to_string()).cloned())])));
                self.chunk_hashes.insert(text_hash);
                self.chunks.push(HashMap::from([("text".to_string(), text), ("url".to_string(), chunk.get(&"url".to_string()).cloned()), ("title".to_string(), chunk.get(&"title".to_string()).cloned()), ("scan_root".to_string(), chunk.get(&"scan_root".to_string()).cloned()), ("hash".to_string(), text_hash), ("qdrant_id".to_string(), point_id)]));
            }
        }
    }
    /// Create a validate_fn callback for the Zero-Waste cache.
    /// 
    /// The callback accepts a CacheFingerprint and re-fetches the source
    /// chunks from Qdrant (using stored URLs) to compare SHA-256 hashes.
    /// If even one hash has changed, the entry is stale → return false.
    /// 
    /// This is the *surgical* validation from Article Scenarios 4-6:
    /// instead of invalidating the whole cache on any write, we only
    /// invalidate the specific entries whose source data has changed.
    pub fn _make_chunk_validator(&mut self) -> Result<()> {
        // Create a validate_fn callback for the Zero-Waste cache.
        // 
        // The callback accepts a CacheFingerprint and re-fetches the source
        // chunks from Qdrant (using stored URLs) to compare SHA-256 hashes.
        // If even one hash has changed, the entry is stale → return false.
        // 
        // This is the *surgical* validation from Article Scenarios 4-6:
        // instead of invalidating the whole cache on any write, we only
        // invalidate the specific entries whose source data has changed.
        if (!self.qdrant || !ZERO_WASTE_AVAILABLE) {
            None
        }
        let _validate = |fingerprint| {
            // try:
            {
                if !fingerprint.source_urls {
                    fingerprint.collection_version >= /* getattr */ 0
                }
                // TODO: from qdrant_client import models
                for url in fingerprint.source_urls.iter() {
                    let (mut current_points, _) = self.qdrant.scroll(/* collection_name= */ self.collection_name, /* scroll_filter= */ models::Filter(/* must= */ vec![models::FieldCondition(/* key= */ "url".to_string(), /* match= */ models::MatchValue(/* value= */ url))]), /* limit= */ 200, /* with_payload= */ true, /* with_vectors= */ false);
                    if !current_points {
                        false
                    }
                    let mut current_hashes = current_points.iter().map(|p| hashlib::sha256(p.payload.get(&"text".to_string()).cloned().unwrap_or("".to_string()).as_bytes().to_vec()).hexdigest()[..16]).collect::<Vec<_>>().into_iter().collect::<HashSet<_>>();
                    let mut cached_hashes = fingerprint.chunk_hashes.into_iter().collect::<HashSet<_>>();
                    if !cached_hashes.issubset(current_hashes) {
                        false
                    }
                }
                true
            }
            // except Exception as _e:
        };
        Ok(_validate)
    }
    /// Direct Semantic search with Zero-Waste two-tier caching.
    /// 
    /// Flow:
    /// 1. Temporal bypass check ("latest"/"current" → skip all cache)
    /// 2. Tier 1: Answer Cache (≥95% → return cached results, zero cost)
    /// 3. Tier 2: Context Cache (≥70% → reuse chunks, skip Qdrant, re-rank)
    /// 4. Full retrieval: Qdrant → rerank → store in both tiers
    /// 
    /// When scan_root is set, bypasses cache and filters results to that root.
    pub fn search(&mut self, query: String, k: i64, rerank: bool, scan_root: Option<String>) -> Vec<HashMap> {
        // Direct Semantic search with Zero-Waste two-tier caching.
        // 
        // Flow:
        // 1. Temporal bypass check ("latest"/"current" → skip all cache)
        // 2. Tier 1: Answer Cache (≥95% → return cached results, zero cost)
        // 3. Tier 2: Context Cache (≥70% → reuse chunks, skip Qdrant, re-rank)
        // 4. Full retrieval: Qdrant → rerank → store in both tiers
        // 
        // When scan_root is set, bypasses cache and filters results to that root.
        if !self.qdrant {
            if self.bm25 {
                logger.debug("[RAG] Qdrant offline, falling back to BM25 for search.".to_string());
                self.hybrid_search(query, k, /* alpha= */ 0.0_f64, /* rerank= */ rerank)
            }
            vec![]
        }
        let mut use_scan_filter = (scan_root && /* /* isinstance(scan_root, str) */ */ true && scan_root.trim().to_string());
        let mut _validator = if !use_scan_filter { self._make_chunk_validator() } else { None };
        if !use_scan_filter {
            let mut cached = self.cache::get(&query).cloned().unwrap_or(/* validate_fn= */ _validator);
            if cached {
                for res in cached.iter() {
                    res["_is_cached".to_string()] = true;
                }
                cached
            }
            let mut context_from_cache = None;
            if /* hasattr(self.cache, "get_context".to_string()) */ true {
                let mut context_from_cache = self.cache::get_context(query, /* validate_fn= */ _validator);
            }
            if context_from_cache {
                logger.debug(format!("[Cache] T2 hit: reusing {} cached chunks", context_from_cache.len()));
                let mut results = context_from_cache;
                if rerank {
                    let mut results = self.rerank(query, results, /* top_k= */ k);
                } else {
                    let mut results = results[..k];
                }
                self.cache::set(query, results, /* source_chunks= */ context_from_cache);
                results
            }
        }
        let mut limit = if rerank { 200.min((k * 10).max(50)) } else { 100.min((k * 5).max(20)) };
        let mut query_vec = self.model.encode(vec![query], /* normalize_embeddings= */ true)[0].tolist();
        let mut query_kw = HashMap::from([("collection_name".to_string(), self.collection_name), ("query".to_string(), query_vec), ("limit".to_string(), limit)]);
        if use_scan_filter {
            query_kw["query_filter".to_string()] = Filter(/* must= */ vec![FieldCondition(/* key= */ "scan_root".to_string(), /* match= */ MatchValue(/* value= */ scan_root.trim().to_string()))]);
        }
        let mut _hnsw_ef = self._get_hnsw_ef_search();
        if _hnsw_ef.is_some() {
            query_kw["search_params".to_string()] = _hnsw_ef;
        }
        let mut hits = self.qdrant.query_points(/* ** */ query_kw).points;
        let mut results = vec![];
        for hit in hits.iter() {
            let mut p = (hit.payload || HashMap::new());
            let mut r = HashMap::from([("text".to_string(), p.get(&"text".to_string()).cloned()), ("url".to_string(), p.get(&"url".to_string()).cloned()), ("title".to_string(), p.get(&"title".to_string()).cloned()), ("score".to_string(), hit.score)]);
            if p.get(&"parent_text".to_string()).cloned() {
                r["parent_text".to_string()] = p["parent_text".to_string()];
            }
            if p.get(&"parent_id".to_string()).cloned() {
                r["parent_id".to_string()] = p["parent_id".to_string()];
            }
            if p.get(&"is_table".to_string()).cloned() {
                r["is_table".to_string()] = true;
                if p.get(&"sheet_name".to_string()).cloned().is_some() {
                    r["sheet_name".to_string()] = p.get(&"sheet_name".to_string()).cloned();
                }
                if p.get(&"columns".to_string()).cloned().is_some() {
                    r["columns".to_string()] = p.get(&"columns".to_string()).cloned();
                }
            }
            for key in ("file_id".to_string(), "dataset".to_string(), "sheet".to_string(), "sheet_name".to_string(), "date".to_string(), "entity".to_string(), "category".to_string(), "dept_name".to_string(), "dept_id".to_string(), "beds_real".to_string(), "beds_struct".to_string(), "patients_present".to_string(), "free_beds".to_string(), "source_file".to_string(), "source_sheet".to_string(), "row_index".to_string(), "unit".to_string()).iter() {
                if p.contains(&key) {
                    r[key] = p[&key];
                }
            }
            results.push(r);
        }
        let mut raw_results = results.into_iter().collect::<Vec<_>>();
        if (/* hasattr(self.cache, "set_context".to_string()) */ true && results) {
            self.cache::set_context(query, raw_results);
        }
        if rerank {
            let mut results = self.rerank(query, results, /* top_k= */ k);
        }
        if !use_scan_filter {
            self.cache::set(query, results, /* source_chunks= */ raw_results);
        }
        results
    }
    /// Delete all chunks associated with a specific URL/path.
    /// 
    /// Uses surgical cache invalidation when Zero-Waste is available:
    /// only the cache entries whose source_urls include this URL are evicted,
    /// instead of nuking the entire cache.
    pub fn delete_document_by_url(&mut self, url: String) -> Result<bool> {
        // Delete all chunks associated with a specific URL/path.
        // 
        // Uses surgical cache invalidation when Zero-Waste is available:
        // only the cache entries whose source_urls include this URL are evicted,
        // instead of nuking the entire cache.
        if !self.qdrant {
            false
        }
        // try:
        {
            // TODO: from qdrant_client import models
            self.qdrant.delete(/* collection_name= */ self.collection_name, /* points_selector= */ models::FilterSelector(/* filter= */ models::Filter(/* must= */ vec![models::FieldCondition(/* key= */ "url".to_string(), /* match= */ models::MatchValue(/* value= */ url))])));
            let _ctx = self._lock;
            {
                if /* hasattr(self.cache, "invalidate_urls".to_string()) */ true {
                    let mut evicted = self.cache::invalidate_urls(HashSet::from([url]));
                    logger.debug(format!("[RAG] Surgical invalidation: {} cache entries evicted for '{}'", evicted, url));
                } else {
                    self.cache::clear();
                }
                if /* hasattr(self.cache, "bump_version".to_string()) */ true {
                    self.cache::bump_version();
                }
                let mut prev_len = self.chunks.len();
                self.chunks = self.chunks.iter().filter(|c| c.get(&"url".to_string()).cloned() != url).map(|c| c).collect::<Vec<_>>();
                let mut new_len = self.chunks.len();
                self._rebuild_bm25();
            }
            logger.info(format!("[RAG] Deleted document: {} (removed {} chunks)", url, (prev_len - new_len)));
            true
        }
        // except Exception as e:
    }
    /// Delete the entire Qdrant collection and clear in-memory state. Next index will recreate.
    pub fn clear_vector_index(&mut self) -> Result<bool> {
        // Delete the entire Qdrant collection and clear in-memory state. Next index will recreate.
        if !self.qdrant {
            false
        }
        // try:
        {
            self.qdrant.delete_collection(self.collection_name);
            let _ctx = self._lock;
            {
                self.chunks = vec![];
                self.chunk_hashes = HashSet::new();
                self.cache::clear();
            }
            logger.info(format!("[RAG] Cleared vector index (collection {})", self.collection_name));
            true
        }
        // except Exception as e:
    }
    pub fn hybrid_search(&mut self, query: String, k: i64, alpha: f64, rerank: bool) -> Vec<HashMap> {
        if !self.chunks {
            vec![]
        }
        let mut _t0 = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut _validator = self._make_chunk_validator();
        let mut cached = if /* hasattr(self.cache, "get".to_string()) */ true { self.cache::get(&query).cloned().unwrap_or(/* validate_fn= */ _validator) } else { None };
        if cached {
            for res in cached.iter() {
                res["_is_cached".to_string()] = true;
            }
            if (METRICS_AVAILABLE && _metrics) {
                _metrics.record_query(query, (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - _t0), /* cache_tier= */ 1, /* n_results= */ cached.len());
            }
            cached
        }
        if /* hasattr(self.cache, "get_context".to_string()) */ true {
            let mut context_from_cache = self.cache::get_context(query, /* validate_fn= */ _validator);
            if context_from_cache {
                logger.debug(format!("[Cache] T2 hit in hybrid_search: reusing {} chunks", context_from_cache.len()));
                let mut results = context_from_cache;
                if rerank {
                    let mut results = self.rerank(query, results, /* top_k= */ k);
                } else {
                    let mut results = results[..k];
                }
                self.cache::set(query, results, /* source_chunks= */ context_from_cache);
                if (METRICS_AVAILABLE && _metrics) {
                    _metrics.record_query(query, (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - _t0), /* cache_tier= */ 2, /* n_results= */ results.len());
                }
                results
            }
        }
        let mut k_search = (k * 5).max(50);
        let mut hits = vec![];
        if self.qdrant {
            let mut query_vec = self.model.encode(vec![query], /* normalize_embeddings= */ true)[0].tolist();
            let mut query_kw = HashMap::from([("collection_name".to_string(), self.collection_name), ("query".to_string(), query_vec), ("limit".to_string(), k_search)]);
            let mut _hnsw_ef = self._get_hnsw_ef_search();
            if _hnsw_ef.is_some() {
                query_kw["search_params".to_string()] = _hnsw_ef;
            }
            let mut hits = self.qdrant.query_points(/* ** */ query_kw).points;
        } else {
            logger.debug("[RAG] Qdrant offline, search using BM25 only.".to_string());
            let mut alpha = 0.0_f64;
        }
        let mut id_to_idx = self.chunks.iter().enumerate().iter().map(|(i, c)| (c["qdrant_id".to_string()], i)).collect::<HashMap<_, _>>();
        let mut f_ranks = HashMap::new();
        for (rank, hit) in hits.iter().enumerate().iter() {
            if id_to_idx.contains(&hit.id) {
                f_ranks[id_to_idx[&hit.id]] = (rank + 1);
            }
        }
        let mut b_ranks = HashMap::new();
        if self.bm25 {
            let mut tokens = self._tokenize(query);
            let mut scores = self.bm25.get_scores(tokens);
            let mut pos_indices = { let mut v = scores.iter().enumerate().iter().filter(|(i, s)| s > 0).map(|(i, s)| (i, s)).collect::<Vec<_>>().clone(); v.sort(); v }[..k_search];
            let mut b_ranks = pos_indices.iter().enumerate().iter().map(|(rank, (i, s))| (i, (rank + 1))).collect::<HashMap<_, _>>();
        }
        let mut K_RRF = 60;
        let mut fusion_scores = HashMap::new();
        let mut all_indices = (f_ranks.keys().into_iter().collect::<HashSet<_>>() | b_ranks.keys().into_iter().collect::<HashSet<_>>());
        for idx in all_indices.iter() {
            let mut f_score = if f_ranks.contains(&idx) { (1.0_f64 / (K_RRF + f_ranks[&idx])) } else { 0.0_f64 };
            let mut b_score = if b_ranks.contains(&idx) { (1.0_f64 / (K_RRF + b_ranks[&idx])) } else { 0.0_f64 };
            fusion_scores[idx] = ((alpha * f_score) + ((1.0_f64 - alpha) * b_score));
        }
        let mut k_candidates = if rerank { (k * 3) } else { k };
        let mut sorted_indices = { let mut v = fusion_scores.keys().clone(); v.sort(); v }[..k_candidates];
        let mut results = sorted_indices.iter().map(|idx| self.chunks[&idx].clone()).collect::<Vec<_>>();
        for (i, res) in results.iter().enumerate().iter() {
            res["fusion_score".to_string()] = fusion_scores[sorted_indices[&i]];
        }
        let mut raw_results = results.into_iter().collect::<Vec<_>>();
        if (/* hasattr(self.cache, "set_context".to_string()) */ true && results) {
            self.cache::set_context(query, raw_results);
        }
        if rerank {
            let mut results = self.rerank(query, results, /* top_k= */ k);
        }
        self.cache::set(query, results, /* source_chunks= */ raw_results);
        if (METRICS_AVAILABLE && _metrics) {
            _metrics.record_query(query, (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - _t0), /* cache_tier= */ None, /* n_results= */ results.len());
        }
        results
    }
    /// Re-rank retrieved chunks using the AdvancedReranker (5-factor scoring)
    /// or falling back to the CrossEncoder-only approach.
    pub fn rerank(&mut self, query: String, chunks: Vec<HashMap>, top_k: i64) -> Result<Vec<HashMap>> {
        // Re-rank retrieved chunks using the AdvancedReranker (5-factor scoring)
        // or falling back to the CrossEncoder-only approach.
        if !chunks {
            vec![]
        }
        if self.advanced_reranker.is_some() {
            // try:
            {
                let (mut ranked, mut scores) = self.advanced_reranker.rerank(query, chunks, /* top_k= */ top_k);
                if ranked {
                    for (chunk, score) in ranked.iter().zip(scores.iter()).iter() {
                        chunk["rerank_score".to_string()] = score;
                    }
                    ranked
                }
            }
            // except Exception as e:
        }
        // try:
        {
            if self.cross_encoder.is_none() {
                // TODO: from sentence_transformers import CrossEncoder
                let mut reranker_path = /* getattr */ None;
                if (reranker_path && PathBuf::from(reranker_path).expanduser().exists()) {
                    let mut load_name = PathBuf::from(reranker_path).expanduser().canonicalize().unwrap_or_default().to_string();
                    logger.info(format!("[RAG] Loading reranker from local path (no hub): {}", load_name));
                } else {
                    let mut load_name = /* getattr */ "BAAI/bge-reranker-base".to_string();
                }
                let mut device = if (config::rag.use_gpu && /* hasattr(config::rag, "use_gpu".to_string()) */ true) { "cuda".to_string() } else { "cpu".to_string() };
                // try:
                {
                    // TODO: import torch
                    if (device == "cuda".to_string() && !torch.cuda.is_available()) {
                        let mut device = "cpu".to_string();
                    }
                }
                // except Exception as _e:
                self.cross_encoder = CrossEncoder(load_name, /* device= */ device);
            }
            let mut pairs = chunks.iter().map(|c| vec![query, c["text".to_string()]]).collect::<Vec<_>>();
            let mut scores = self.cross_encoder.predict(pairs);
            for (i, chunk) in chunks.iter().enumerate().iter() {
                chunk["rerank_score".to_string()] = scores[&i].to_string().parse::<f64>().unwrap_or(0.0);
            }
            let mut sorted_chunks = { let mut v = chunks.clone(); v.sort(); v };
            sorted_chunks[..top_k]
        }
        // except Exception as e:
    }
    pub fn save(&self, path: Option<PathBuf>) -> () {
        // pass
    }
    /// Reload state from database.
    pub fn load(&self, path: Option<PathBuf>) -> bool {
        // Reload state from database.
        self._load_metadata();
        true
    }
    pub fn get_stats(&mut self) -> Result<HashMap> {
        if !self.qdrant {
            HashMap::from([("points_count".to_string(), self.chunks.len()), ("status".to_string(), "degraded".to_string())])
        }
        // try:
        {
            let mut info = self.qdrant.get_collection(self.collection_name);
            HashMap::from([("total_chunks".to_string(), info.points_count), ("collection".to_string(), self.collection_name)])
        }
        // except Exception as _e:
    }
}

/// Async wrapper for LocalRAG to prevent blocking the event loop.
#[derive(Debug, Clone)]
pub struct AsyncLocalRAG {
}

impl AsyncLocalRAG {
    pub async fn search_async(&self, query: String, k: i64) -> Vec<HashMap> {
        asyncio.to_thread(self.search, query, k).await
    }
    pub async fn hybrid_search_async(&self, query: String, k: i64, alpha: f64) -> Vec<HashMap> {
        asyncio.to_thread(self.hybrid_search, query, k, alpha).await
    }
    pub async fn rerank_async(&self, query: String, chunks: Vec<HashMap>, top_k: i64) -> Vec<HashMap> {
        asyncio.to_thread(self.rerank, query, chunks, top_k).await
    }
    pub async fn build_index_async(&self, documents: Vec<HashMap>, dedup_threshold: Option<f64>) -> () {
        asyncio.to_thread(self.build_index, documents, dedup_threshold).await
    }
    pub async fn add_chunks_async(&self, chunks: Vec<HashMap>, dedup_threshold: Option<f64>) -> () {
        asyncio.to_thread(self.add_chunks, chunks, dedup_threshold).await
    }
}

/// Async generator for RAG response.
pub async fn generate_rag_response_async(query: String, rag: LocalRAG, llm_backend: String, use_hybrid: bool, k: i64, alpha: f64) -> () {
    // Async generator for RAG response.
    if use_hybrid {
        if /* hasattr(rag, "hybrid_search_async".to_string()) */ true {
            let mut candidates = rag.hybrid_search_async(query, /* k= */ (k * 3), /* alpha= */ alpha).await;
        } else {
            let mut candidates = asyncio.to_thread(rag.hybrid_search, query, /* k= */ (k * 3), /* alpha= */ alpha).await;
        }
    } else if /* hasattr(rag, "search_async".to_string()) */ true {
        let mut candidates = rag.search_async(query, /* k= */ (k * 3)).await;
    } else {
        let mut candidates = asyncio.to_thread(rag.search, query, /* k= */ (k * 3)).await;
    }
    if /* hasattr(rag, "rerank_async".to_string()) */ true {
        let mut context_chunks = rag.rerank_async(query, candidates, /* top_k= */ k).await;
    } else {
        let mut context_chunks = asyncio.to_thread(rag.rerank, query, candidates, /* top_k= */ k).await;
    }
    if !context_chunks {
        /* yield "I don't have enough information in my knowledge base.".to_string() */;
        return;
    }
    let mut MAX_CTX_CHARS = 80000;
    let mut context_text = "".to_string();
    for (i, c) in context_chunks.iter().enumerate().iter() {
        let mut chunk_text = format!("Source [{}]: {}\n\n", (i + 1), c["text".to_string()]);
        if (context_text.len() + chunk_text.len()) > MAX_CTX_CHARS {
            break;
        }
        context_text += chunk_text;
    }
    let mut prompt = format!("Context:\n{}\n\nQuestion: {}\n\nAnswer mentioning sources:", context_text, query);
    if /* hasattr(llm_backend, "send_message_async".to_string()) */ true {
        // async for
        while let Some(chunk) = llm_backend::send_message_async(prompt).next().await {
            /* yield chunk */;
        }
    } else {
        for chunk in llm_backend::send_message(prompt).iter() {
            /* yield chunk */;
        }
    }
}
