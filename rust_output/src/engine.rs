/// rag_core.engine — Unified RAG Engine
/// ======================================
/// 
/// Single entry point for all RAG operations: index, search, groups.
/// Combines chunker, embeddings, BM25, RRF fusion, reranker, cache, and dedup
/// into one coherent async-friendly API.
/// 
/// Usage::
/// 
/// from rag_core import RAGEngine
/// 
/// rag = RAGEngine(collection="my_project", prefer_code=true)
/// await rag.initialize()
/// n = await rag.build_index(documents)
/// results = await rag.search("parse config file", top_k=10)

use anyhow::{Result, Context};
use crate::bm25_index::{BM25Index};
use crate::cache::{SemanticCache};
use crate::chunker::{ChunkerConfig, TextChunker};
use crate::dedup::{DeduplicationManager};
use crate::embeddings::{EmbeddingManager};
use crate::reranker::{RerankerManager};
use crate::search::{HybridSearcher, SearchResult};
use std::collections::HashMap;
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Unified RAG engine — the standard pipeline for all projects.
/// 
/// Tier 1 — Full pipeline (recommended)::
/// 
/// Documents → Chunker → Embed → Dedup → BM25 Index
/// ↓
/// Query → Dense + BM25 → RRF → Rerank → Results
/// 
/// Tier 2 — Qdrant bridge (when available)::
/// 
/// Delegates to existing Qdrant-backed LocalRAG for persistent storage.
/// 
/// Tier 3 — BM25-only fallback::
/// 
/// No neural models — pure keyword search.
/// 
/// Args:
/// collection: Name for this RAG collection (e.g. "function_catalog").
/// storage_dir: Directory for persistent caches.
/// prefer_code: Prefer code embedding models (GraphCodeBERT).
/// embedding_model: Override specific embedding model name.
/// reranker_model: Override specific reranker model name.
/// chunk_strategy: "sentence" | "fixed" | "code".
/// chunk_size: Characters per chunk.
/// chunk_overlap: Overlap between chunks.
/// rrf_k: RRF fusion constant.
/// dense_weight: Weight for dense vs BM25 (0-1).
/// cache_ttl: Semantic cache TTL in seconds.
/// dedup_threshold: Near-duplicate similarity threshold.
#[derive(Debug, Clone)]
pub struct RAGEngine {
    pub collection: String,
    pub storage_dir: String,
    pub _embeddings: EmbeddingManager,
    pub _reranker: RerankerManager,
    pub _bm25: BM25Index,
    pub _chunker: TextChunker,
    pub _dedup: DeduplicationManager,
    pub _cache: Option<SemanticCache>,
    pub _searcher: Option<HybridSearcher>,
    pub _chunk_strategy: String,
    pub _rrf_k: String,
    pub _dense_weight: String,
    pub _cache_ttl: String,
    pub _initialised: bool,
    pub _backend: String,
}

impl RAGEngine {
    pub fn new(collection: String, storage_dir: Option<PathBuf>, prefer_code: bool, embedding_model: Option<String>, reranker_model: Option<String>, chunk_strategy: String, chunk_size: i64, chunk_overlap: i64, rrf_k: i64, dense_weight: f64, cache_ttl: f64, dedup_threshold: f64) -> Self {
        Self {
            collection,
            storage_dir: if storage_dir { PathBuf::from(storage_dir) } else { (Path.cwd() / "rag_storage".to_string()) },
            _embeddings: EmbeddingManager(/* model_name= */ embedding_model, /* prefer_code= */ prefer_code),
            _reranker: RerankerManager(/* model_name= */ reranker_model),
            _bm25: BM25Index(/* code_aware= */ prefer_code),
            _chunker: TextChunker(ChunkerConfig(/* CHUNK_SIZE= */ chunk_size, /* CHUNK_OVERLAP= */ chunk_overlap)),
            _dedup: DeduplicationManager(/* similarity_threshold= */ dedup_threshold),
            _cache: None,
            _searcher: None,
            _chunk_strategy: chunk_strategy,
            _rrf_k: rrf_k,
            _dense_weight: dense_weight,
            _cache_ttl: cache_ttl,
            _initialised: false,
            _backend: String::new(),
        }
    }
    pub fn initialised(&self) -> bool {
        self._initialised
    }
    pub fn backend(&self) -> &String {
        self._backend
    }
    pub fn embedding_model(&self) -> &String {
        if self._embeddings.is_loaded {
            self._embeddings.model_type
        }
        "none".to_string()
    }
    pub fn doc_count(&self) -> i64 {
        if self._searcher {
            self._searcher.doc_count
        }
        0
    }
    /// Initialise the RAG pipeline (load models).
    /// 
    /// Returns true if at least BM25 is available.
    pub async fn initialize(&mut self, progress: Option<Box<dyn Fn(serde_json::Value)>>) -> bool {
        // Initialise the RAG pipeline (load models).
        // 
        // Returns true if at least BM25 is available.
        let _p = |msg, pct| {
            if progress {
                progress(msg, pct);
            }
            logger.info("[RAGEngine] %s".to_string(), msg);
        };
        _p("Initialising RAG engine ...".to_string(), 0.0_f64);
        _p("Loading embedding model ...".to_string(), 0.1_f64);
        let mut has_embeddings = self._embeddings.load();
        if has_embeddings {
            _p(format!("Embeddings: {} (dim={})", self._embeddings.model_type, self._embeddings.dimension), 0.3_f64);
            self._backend = "full".to_string();
        } else {
            _p("No embedding model — BM25-only mode".to_string(), 0.3_f64);
            self._backend = "bm25_only".to_string();
        }
        _p("Loading reranker ...".to_string(), 0.4_f64);
        let mut has_reranker = self._reranker.load();
        if has_reranker {
            _p(format!("Reranker: {}", self._reranker.model_name), 0.5_f64);
        } else {
            _p("No reranker available — skipping reranking".to_string(), 0.5_f64);
        }
        self._searcher = HybridSearcher(/* embeddings= */ if has_embeddings { self._embeddings } else { None }, /* bm25= */ self._bm25, /* reranker= */ if has_reranker { self._reranker } else { None }, /* rrf_k= */ self._rrf_k, /* dense_weight= */ self._dense_weight);
        self._cache = SemanticCache(/* ttl= */ self._cache_ttl, /* encoder= */ if has_embeddings { self._embeddings } else { None });
        self._initialised = true;
        _p("RAG engine ready".to_string(), 0.6_f64);
        true
    }
    /// Index documents.
    /// 
    /// Args:
    /// documents: List of ``{"text": "...", "url": "...", "title": "...", "metadata": {}}``
    /// progress: ``(message, 0-1) -> None`` callback.
    /// chunk: Whether to chunk documents first.
    /// filter_junk: Remove low-quality chunks.
    /// 
    /// Returns:
    /// Number of documents/chunks indexed.
    pub async fn build_index(&mut self, documents: Vec<HashMap<String, Box<dyn std::any::Any>>>) -> i64 {
        // Index documents.
        // 
        // Args:
        // documents: List of ``{"text": "...", "url": "...", "title": "...", "metadata": {}}``
        // progress: ``(message, 0-1) -> None`` callback.
        // chunk: Whether to chunk documents first.
        // filter_junk: Remove low-quality chunks.
        // 
        // Returns:
        // Number of documents/chunks indexed.
        if !self._initialised {
            self.initialize(/* progress= */ progress).await;
        }
        let _p = |msg, pct| {
            if progress {
                progress(msg, pct);
            }
        };
        if chunk {
            _p(format!("Chunking {} documents ...", documents.len()), 0.1_f64);
            let mut chunks = self._chunker.chunk_documents(documents, /* strategy= */ self._chunk_strategy, /* filter_junk= */ filter_junk);
        } else {
            let mut chunks = documents;
        }
        let mut before = chunks.len();
        let mut chunks = self._dedup.deduplicate_chunks(chunks);
        let mut removed = (before - chunks.len());
        if removed {
            _p(format!("Removed {} duplicate chunks", removed), 0.2_f64);
        }
        if !chunks {
            _p("No chunks to index".to_string(), 0.0_f64);
            0
        }
        _p(format!("Indexing {} chunks ...", chunks.len()), 0.25_f64);
        let mut n = self._searcher.index_documents(chunks, /* progress= */ _p);
        if (self._embeddings.is_loaded && self._searcher._doc_embeddings.is_some()) {
            let mut cache_path = (self.storage_dir / format!("{}_embeddings.npy", self.collection));
            self._embeddings.save_embeddings(self._searcher._doc_embeddings, cache_path);
            let mut meta_path = (self.storage_dir / format!("{}_docs.json", self.collection));
            meta_path.parent().unwrap_or(std::path::Path::new("")).create_dir_all();
            meta_pathstd::fs::write(&serde_json::to_string(&chunks.iter().map(|d| HashMap::from([("text".to_string(), d["text".to_string()][..500])])).collect::<Vec<_>>()).unwrap(), /* encoding= */ "utf-8".to_string());
        }
        if self._cache {
            self._cache.clear();
        }
        _p(format!("Indexed {} chunks", n), 1.0_f64);
        n
    }
    /// Convenience: index a single block of text.
    pub async fn index_text(&mut self, text: String) -> i64 {
        // Convenience: index a single block of text.
        self.build_index(vec![HashMap::from([("text".to_string(), text), ("url".to_string(), url), ("title".to_string(), title), ("metadata".to_string(), (metadata || HashMap::new()))])], /* chunk= */ chunk).await
    }
    /// Hybrid search: Dense + BM25 → RRF → Rerank.
    /// 
    /// Args:
    /// query: Natural language or code query.
    /// top_k: Number of results.
    /// use_reranking: Enable cross-encoder reranking.
    /// min_score: Minimum score threshold.
    /// filters: Metadata filters.
    /// 
    /// Returns:
    /// List of :class:`SearchResult` sorted by relevance.
    pub async fn search(&mut self, query: String) -> Vec<SearchResult> {
        // Hybrid search: Dense + BM25 → RRF → Rerank.
        // 
        // Args:
        // query: Natural language or code query.
        // top_k: Number of results.
        // use_reranking: Enable cross-encoder reranking.
        // min_score: Minimum score threshold.
        // filters: Metadata filters.
        // 
        // Returns:
        // List of :class:`SearchResult` sorted by relevance.
        if !self._initialised {
            self.initialize().await;
        }
        if (!self._searcher || self._searcher.doc_count == 0) {
            vec![]
        }
        if self._cache {
            let mut cached = self._cache.get(&query).cloned();
            if cached.is_some() {
                let mut restored = vec![];
                for r in cached.iter() {
                    if /* /* isinstance(r, dict) */ */ true {
                        let mut meta = r.iter().iter().filter(|(k, v)| !("text".to_string(), "score".to_string(), "index".to_string()).contains(&k)).map(|(k, v)| (k, v)).collect::<HashMap<_, _>>();
                        restored.push(SearchResult(/* text= */ r["text".to_string()], /* score= */ r.get(&"score".to_string()).cloned().unwrap_or(0.0_f64), /* index= */ r.get(&"index".to_string()).cloned().unwrap_or(0), /* metadata= */ meta));
                    } else {
                        restored.push(r);
                    }
                }
                restored
            }
        }
        let mut results = self._searcher.search(query, /* top_k= */ top_k, /* use_reranking= */ use_reranking, /* min_score= */ min_score, /* filters= */ filters);
        if (self._cache && results) {
            self._cache.set(query, results.iter().map(|r| r.to_dict()).collect::<Vec<_>>());
        }
        results
    }
    /// Convenience: search and return plain dicts.
    pub async fn search_text(&mut self, query: String, top_k: i64) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Convenience: search and return plain dicts.
        let mut results = self.search(query, /* top_k= */ top_k).await;
        results.iter().map(|r| r.to_dict()).collect::<Vec<_>>()
    }
    /// Format search results as context for an LLM prompt.
    /// 
    /// Args:
    /// results: Search results from :meth:`search`.
    /// max_tokens: Approximate max tokens (chars / 4).
    /// include_scores: Include relevance scores.
    /// 
    /// Returns:
    /// Formatted context string.
    pub fn format_context(&self, results: Vec<SearchResult>) -> String {
        // Format search results as context for an LLM prompt.
        // 
        // Args:
        // results: Search results from :meth:`search`.
        // max_tokens: Approximate max tokens (chars / 4).
        // include_scores: Include relevance scores.
        // 
        // Returns:
        // Formatted context string.
        let mut parts = vec![];
        let mut budget = (max_tokens * 4);
        for (i, r) in results.iter().enumerate().iter() {
            let mut header = format!("[Source {}]", i);
            if r.url {
                header += format!(" ({})", r.url);
            }
            if include_scores {
                header += format!(" [score: {:.3}]", r.score);
            }
            let mut entry = format!("{}\n{}", header, r.text);
            if (parts.iter().map(|p| p.len()).collect::<Vec<_>>().iter().sum::<i64>() + entry.len()) > budget {
                break;
            }
            parts.push(entry);
        }
        parts.join(&"\n\n".to_string())
    }
    /// Return engine status info.
    pub fn stats(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Return engine status info.
        HashMap::from([("initialised".to_string(), self._initialised), ("backend".to_string(), self._backend), ("collection".to_string(), self.collection), ("embedding_model".to_string(), if self._embeddings.is_loaded { self._embeddings.model_type } else { "none".to_string() }), ("embedding_dim".to_string(), self._embeddings.dimension), ("reranker".to_string(), if self._reranker.is_loaded { self._reranker.model_name } else { "none".to_string() }), ("doc_count".to_string(), self.doc_count), ("bm25_indexed".to_string(), self._bm25.indexed), ("cache_size".to_string(), if self._cache { self._cache.size } else { 0 }), ("dedup_seen".to_string(), self._dedup.seen_count)])
    }
    /// Sync wrapper for initialize().
    pub fn sync_initialize(&mut self, progress: String) -> bool {
        // Sync wrapper for initialize().
        self._run_sync(self.initialize(/* progress= */ progress))
    }
    /// Sync wrapper for build_index().
    pub fn sync_build_index(&self, documents: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> i64 {
        // Sync wrapper for build_index().
        self._run_sync(self.build_index(documents, /* ** */ kwargs))
    }
    /// Sync wrapper for search().
    pub fn sync_search(&self, query: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Vec<SearchResult> {
        // Sync wrapper for search().
        self._run_sync(self.search(query, /* ** */ kwargs))
    }
    /// Run a coroutine synchronously, handling nested event loops.
    pub fn _run_sync(coro: String) -> Result<()> {
        // Run a coroutine synchronously, handling nested event loops.
        // try:
        {
            let mut r#loop = asyncio.get_running_loop();
        }
        // except RuntimeError as _e:
        if (r#loop && r#loop.is_running()) {
            // TODO: import concurrent.futures
            let mut pool = concurrent.futures.ThreadPoolExecutor(/* max_workers= */ 1);
            {
                pool.submit(asyncio.run, coro).result()
            }
        } else {
            asyncio.run(coro)
        }
    }
}
