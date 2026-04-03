/// RAG Integration – Thin adapter around zena_mode.rag_pipeline::LocalRAG
/// 
/// Responsibilities:
/// • Initialise LocalRAG (Qdrant + embeddings + hybrid search)
/// • Provide upload_document / search_context / index_content
/// • Fall back to a minimal in-memory store when LocalRAG is absent
/// 
/// All LLM-generation logic lives in Core/services/rag_service::py.

use anyhow::{Result, Context};
use regex::Regex;
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub const _SUGGESTED_CACHE_TTL: i64 = 300;

pub static _SINONIME_RO_CAUTARE: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub const COMPLEX_QUERY_WORD_THRESHOLD: i64 = 6;

pub const MAX_SYNONYMS_SIMPLE: i64 = 2;

pub const MAX_SYNONYMS_COMPLEX: i64 = 5;

pub const MAX_EXPANDED_QUERY_CHARS: i64 = 300;

pub static _RO_STOPWORDS: std::sync::LazyLock<frozenset> = std::sync::LazyLock::new(|| Default::default());

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const DEFAULT_CONTEXT_MAX_CHARS: i64 = 80000;

pub static _RAG_INTEGRATION: std::sync::LazyLock<Option<RAGIntegration>> = std::sync::LazyLock::new(|| None);

/// Minimal in-memory RAG for tests. Shares ``format_context`` with main class.
#[derive(Debug, Clone)]
pub struct _MockRAG {
    pub docs: Vec<HashMap>,
}

impl _MockRAG {
    pub fn new() -> Self {
        Self {
            docs: Vec::new(),
        }
    }
    pub async fn upload_document(&mut self, path: String, collection: String) -> Result<()> {
        // try:
        {
            let mut text = if PathBuf::from(path).exists() { PathBuf::from(path).read_to_string()) } else { path.to_string() };
        }
        // except Exception as _e:
        self.docs.push(HashMap::from([("text".to_string(), text), ("source".to_string(), path.to_string()), ("collection".to_string(), collection)]));
        Ok((true, format!("Indexed: {}", path)))
    }
    pub async fn search_context(&mut self, query: String, collection: String, top_k: i64, kw: HashMap<String, Box<dyn std::any::Any>>) -> () {
        let mut q = query.to_lowercase();
        let mut scored = vec![];
        for d in self.docs.iter() {
            if (collection && d.get(&"collection".to_string()).cloned() != collection) {
                continue;
            }
            let mut txt = d.get(&"text".to_string()).cloned().unwrap_or("".to_string()).to_lowercase();
            if txt.contains(&q) {
                let mut score = 0.9_f64;
            } else {
                let mut hits = q.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().iter().filter(|w| txt.contains(&w)).map(|w| 1).collect::<Vec<_>>().iter().sum::<i64>();
                let mut score = if hits { (0.5_f64 + (0.1_f64 * hits)).min(0.8_f64) } else { 0.0_f64 };
            }
            if score > 0 {
                scored.push(HashMap::from([("text".to_string(), d.get(&"text".to_string()).cloned().unwrap_or("".to_string())), ("score".to_string(), score), ("source".to_string(), d.get(&"source".to_string()).cloned()), ("collection".to_string(), d.get(&"collection".to_string()).cloned())]));
            }
        }
        scored.sort(/* key= */ |r| r["score".to_string()], /* reverse= */ true);
        scored[..top_k]
    }
    pub fn format_context_for_llm(&self, results: String, max_tokens: String) -> () {
        format_context(results, /* max_chars= */ max_tokens)
    }
    pub fn get_stats(&self) -> () {
        HashMap::from([("documents_uploaded".to_string(), self.docs.len()), ("collections".to_string(), HashMap::new()), ("total_collection_size".to_string(), self.docs.iter().map(|d| d.get(&"text".to_string()).cloned().unwrap_or("".to_string()).len()).collect::<Vec<_>>().iter().sum::<i64>())])
    }
}

/// Thin wrapper around LocalRAG (Qdrant) with in-memory fallback.
#[derive(Debug, Clone)]
pub struct RAGIntegration {
    pub rag_manager: Option<serde_json::Value>,
    pub documents: Vec<HashMap>,
    pub collections: HashMap<String, Vec<HashMap>>,
    pub initialized: bool,
    pub _mem_docs: Vec<HashMap>,
    pub _suggested_cache: Option<(f64, i64, Vec<String>)>,
    pub _summary_cache: Option<(f64, i64, HashMap)>,
    pub _stats_cache: Option<(f64, HashMap)>,
}

impl RAGIntegration {
    pub fn new() -> Self {
        Self {
            rag_manager: None,
            documents: Vec::new(),
            collections: HashMap::new(),
            initialized: false,
            _mem_docs: Vec::new(),
            _suggested_cache: None,
            _summary_cache: None,
            _stats_cache: None,
        }
    }
    /// true when backed by LocalRAG (not in-memory fallback).
    pub fn _is_pro(&self) -> bool {
        // true when backed by LocalRAG (not in-memory fallback).
        (self.rag_manager::is_some() && /* hasattr(self.rag_manager, "build_index".to_string()) */ true)
    }
    /// true when backed by a _MockRAG (or any non-pro manager).
    pub fn _has_mock(&self) -> bool {
        // true when backed by a _MockRAG (or any non-pro manager).
        (self.rag_manager::is_some() && !self._is_pro)
    }
    /// Try LocalRAG; fall back to in-memory store.
    pub async fn initialize(&mut self) -> Result<bool> {
        // Try LocalRAG; fall back to in-memory store.
        // try:
        {
            logger.info("Initializing RAG engine (Qdrant)…".to_string());
            // TODO: from zena_mode.rag_pipeline import LocalRAG
            let mut storage = (PathBuf::from(std::env::current_dir().unwrap().to_str().unwrap().to_string()) / "rag_storage".to_string());
            self.rag_manager = LocalRAG(/* cache_dir= */ storage);
            self.rag_manager::warmup();
            self.initialized = true;
            logger.info("RAG engine initialised at %s".to_string(), storage);
            true
        }
        // except ImportError as exc:
        // except Exception as exc:
    }
    pub async fn upload_document(&mut self, file_path: String, collection_name: String, metadata: Option<HashMap>) -> Result<(bool, String)> {
        if !self.initialized {
            (false, "RAG not initialised".to_string())
        }
        let mut fp = PathBuf::from(file_path);
        if !fp.exists() {
            (false, format!("File not found: {}", fp))
        }
        // try:
        {
            let mut text = fp.read_to_string(), /* errors= */ "ignore".to_string());
        }
        // except Exception as _e:
        if self._is_pro {
            // TODO: import streamlit as st
            let mut threshold = st.session_state.get(&"setting_dedup_sensitivity".to_string()).cloned().unwrap_or(0.9_f64);
            let mut filter_junk = st.session_state.get(&"setting_enable_boilerplate_removal".to_string()).cloned().unwrap_or(true);
            let mut doc = HashMap::from([("content".to_string(), text), ("url".to_string(), fp.to_string()), ("title".to_string(), fp.name), ("metadata".to_string(), (metadata || HashMap::new()))]);
            asyncio.to_thread(self.rag_manager::build_index, vec![doc], /* dedup_threshold= */ threshold, /* filter_junk= */ filter_junk).await;
        } else if self._has_mock {
            self.rag_manager::upload_document(fp.to_string(), /* collection= */ collection_name).await
        } else {
            self._mem_docs.push(HashMap::from([("text".to_string(), text), ("source".to_string(), fp.to_string()), ("collection".to_string(), collection_name)]));
        }
        let mut info = HashMap::from([("name".to_string(), fp.name), ("path".to_string(), fp.to_string()), ("collection".to_string(), collection_name), ("size".to_string(), fp.stat().st_size), ("uploaded_at".to_string(), datetime::now().isoformat()), ("metadata".to_string(), (metadata || HashMap::new()))]);
        self.documents.push(info);
        self.collections::entry(collection_name).or_insert(vec![]).push(info);
        Ok((true, format!("Indexed: {}", fp.name)))
    }
    /// Index raw extracted text (from content_extractor).
    /// 
    /// source_name is the dataset/folder path from the UI (resolved). It is used as
    /// fallback for doc url/title when a source has no "path". The vector index does
    /// NOT store source_name; only per-document "url" (file path) and "title" are in
    /// the payload. Search and list_indexed_sources do not filter by dataset path.
    /// See docs/VECTOR_INDEX_AND_DATASET_PATH.md.
    pub async fn index_content(&mut self, content: String, sources: Vec<HashMap>, source_name: String) -> (bool, String) {
        // Index raw extracted text (from content_extractor).
        // 
        // source_name is the dataset/folder path from the UI (resolved). It is used as
        // fallback for doc url/title when a source has no "path". The vector index does
        // NOT store source_name; only per-document "url" (file path) and "title" are in
        // the payload. Search and list_indexed_sources do not filter by dataset path.
        // See docs/VECTOR_INDEX_AND_DATASET_PATH.md.
        if (!self.initialized && !self.initialize().await) {
            (false, "RAG engine not available".to_string())
        }
        let mut documents = vec![];
        if sources {
            let mut blocks = _split_aggregated_text(content, sources);
            for (src, block) in sources.iter().zip(blocks.iter()).iter() {
                let mut src_path = src.get(&"path".to_string()).cloned().unwrap_or(source_name);
                if !_path_under_root(src_path, source_name) {
                    logger.warning("Skipping source outside scan root: %s (root: %s)".to_string(), src_path, source_name);
                    continue;
                }
                let mut doc = HashMap::from([("content".to_string(), block), ("url".to_string(), src_path), ("title".to_string(), src.get(&"title".to_string()).cloned().unwrap_or(source_name)), ("scan_root".to_string(), source_name)]);
                if src.get(&"is_table".to_string()).cloned() {
                    doc["is_table".to_string()] = true;
                    if src.get(&"sheet_name".to_string()).cloned().is_some() {
                        doc["sheet_name".to_string()] = src["sheet_name".to_string()];
                    }
                    if src.get(&"columns".to_string()).cloned().is_some() {
                        doc["columns".to_string()] = src["columns".to_string()];
                    }
                }
                if src.get(&"excel_row".to_string()).cloned() {
                    doc["excel_row".to_string()] = true;
                    for key in ("file_id".to_string(), "dataset".to_string(), "sheet".to_string(), "sheet_name".to_string(), "date".to_string(), "entity".to_string(), "category".to_string(), "dept_name".to_string(), "dept_id".to_string(), "beds_real".to_string(), "beds_struct".to_string(), "patients_present".to_string(), "free_beds".to_string(), "source_file".to_string(), "source_sheet".to_string(), "row_index".to_string(), "unit".to_string()).iter() {
                        if src.contains(&key) {
                            doc[key] = src[&key];
                        }
                    }
                }
                documents.push(doc);
            }
        } else {
            documents.push(HashMap::from([("content".to_string(), content), ("url".to_string(), source_name), ("title".to_string(), source_name), ("scan_root".to_string(), source_name)]));
        }
        if !documents {
            (false, "No content to index".to_string())
        }
        if self._is_pro {
            // TODO: import streamlit as st
            let mut threshold = st.session_state.get(&"setting_dedup_sensitivity".to_string()).cloned().unwrap_or(0.9_f64);
            let mut filter_junk = st.session_state.get(&"setting_enable_boilerplate_removal".to_string()).cloned().unwrap_or(true);
            asyncio.to_thread(self.rag_manager::build_index, documents, /* dedup_threshold= */ threshold, /* filter_junk= */ filter_junk).await;
        } else if self._has_mock {
            for doc in documents.iter() {
                self.rag_manager::docs.push(HashMap::from([("text".to_string(), doc["content".to_string()]), ("source".to_string(), doc["url".to_string()]), ("collection".to_string(), "default".to_string())]));
            }
        } else {
            for doc in documents.iter() {
                self._mem_docs.push(HashMap::from([("text".to_string(), doc["content".to_string()]), ("source".to_string(), doc["url".to_string()]), ("collection".to_string(), "default".to_string())]));
            }
        }
        for doc in documents.iter() {
            self.documents.push(HashMap::from([("path".to_string(), doc["url".to_string()]), ("title".to_string(), doc["title".to_string()]), ("size".to_string(), doc["content".to_string()].len())]));
        }
        let mut total = documents.iter().map(|d| d["content".to_string()].len()).collect::<Vec<_>>().iter().sum::<i64>();
        (true, format!("Indexed {} sources ({} chars)", documents.len(), total))
    }
    /// Delete a document by its source path/URL.
    pub async fn delete_document(&mut self, path: String) -> bool {
        // Delete a document by its source path/URL.
        if !self.initialized {
            false
        }
        if self._is_pro {
            asyncio.to_thread(self.rag_manager::delete_document_by_url, path).await;
        } else if self._has_mock {
            // pass
        } else {
            self._mem_docs = self._mem_docs.iter().filter(|d| d.get(&"source".to_string()).cloned() != path).map(|d| d).collect::<Vec<_>>();
        }
        self.documents = self.documents.iter().filter(|d| d.get(&"path".to_string()).cloned() != path).map(|d| d).collect::<Vec<_>>();
        for (name, docs) in self.collections::iter().iter() {
            self.collections[name] = docs.iter().filter(|d| d.get(&"path".to_string()).cloned() != path).map(|d| d).collect::<Vec<_>>();
        }
        logger.info(format!("Deleted document: {}", path));
        true
    }
    pub async fn search_context(&mut self, query: String, collection_name: String, top_k: i64, score_threshold: f64, use_hybrid: bool, alpha: f64) -> Vec<HashMap> {
        if (!self.initialized || (self.rag_manager::is_none() && !self._mem_docs)) {
            vec![]
        }
        if self._is_pro {
            if use_hybrid {
                if /* hasattr(self.rag_manager, "hybrid_search".to_string()) */ true {
                    let mut raw = asyncio.to_thread(self.rag_manager::hybrid_search, query, /* k= */ top_k, /* alpha= */ alpha, /* rerank= */ true).await;
                } else {
                    let mut raw = asyncio.to_thread(self.rag_manager::search, query, /* k= */ top_k, /* rerank= */ true).await;
                }
            } else {
                let mut raw = asyncio.to_thread(self.rag_manager::search, query, /* k= */ top_k, /* rerank= */ true).await;
            }
            // TODO: import math
            let _normalise_score = |r| {
                if r.contains(&"rerank_score".to_string()) {
                    (1.0_f64 / (1.0_f64 + math::exp(-r["rerank_score".to_string()])))
                }
                if r.contains(&"score".to_string()) {
                    r["score".to_string()]
                }
                if r.contains(&"fusion_score".to_string()) {
                    (r["fusion_score".to_string()] * 60).min(1.0_f64)
                }
                0.0_f64
            };
            let mut results = vec![];
            for r in raw.iter() {
                if _normalise_score(r) < score_threshold {
                    continue;
                }
                let mut item = HashMap::from([("text".to_string(), r.get(&"text".to_string()).cloned().unwrap_or("".to_string())), ("score".to_string(), _normalise_score(r)), ("source".to_string(), (r.get(&"url".to_string()).cloned() || r.get(&"title".to_string()).cloned().unwrap_or("unknown".to_string()))), ("collection".to_string(), collection_name)]);
                for key in ("sheet_name".to_string(), "date".to_string(), "row_index".to_string(), "source_file".to_string(), "dataset".to_string(), "sheet".to_string(), "dept_name".to_string()).iter() {
                    if r.get(&key).cloned().is_some() {
                        item[key] = r[&key];
                    }
                }
                results.push(item);
            }
            _enrich_results_with_tables(results)
        }
        if self._has_mock {
            let mut results = self.rag_manager::search_context(query, /* collection= */ collection_name, /* top_k= */ top_k).await;
            let mut filtered = results.iter().filter(|r| r.get(&"score".to_string()).cloned().unwrap_or(0) >= score_threshold).map(|r| r).collect::<Vec<_>>();
            _enrich_results_with_tables(filtered)
        }
        let mut q = query.to_lowercase();
        let mut scored = vec![];
        for d in self._mem_docs.iter() {
            if (collection_name && d.get(&"collection".to_string()).cloned() != collection_name) {
                continue;
            }
            let mut txt = d.get(&"text".to_string()).cloned().unwrap_or("".to_string()).to_lowercase();
            if txt.contains(&q) {
                let mut score = 0.9_f64;
            } else {
                let mut hits = q.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().iter().filter(|w| txt.contains(&w)).map(|w| 1).collect::<Vec<_>>().iter().sum::<i64>();
                let mut score = if hits { (0.5_f64 + (0.1_f64 * hits)).min(0.8_f64) } else { 0.0_f64 };
            }
            if score >= score_threshold {
                scored.push(HashMap::from([("text".to_string(), d.get(&"text".to_string()).cloned().unwrap_or("".to_string())), ("score".to_string(), score), ("source".to_string(), d.get(&"source".to_string()).cloned()), ("collection".to_string(), d.get(&"collection".to_string()).cloned())]));
            }
        }
        scored.sort(/* key= */ |r| r["score".to_string()], /* reverse= */ true);
        _enrich_results_with_tables(scored[..top_k])
    }
    /// Retrieve + format context for an LLM prompt. Uses high default max_context_chars so all results are included for accurate numbers.
    pub async fn query_context(&mut self, query: String, top_k: i64, max_context_chars: i64, score_threshold: f64, use_hybrid: bool, alpha: f64) -> (String, Vec<HashMap>) {
        // Retrieve + format context for an LLM prompt. Uses high default max_context_chars so all results are included for accurate numbers.
        if max_context_chars.is_none() {
            let mut max_context_chars = DEFAULT_CONTEXT_MAX_CHARS;
        }
        let mut results = self.search_context(query, /* top_k= */ top_k, /* score_threshold= */ score_threshold, /* use_hybrid= */ use_hybrid, /* alpha= */ alpha).await;
        if !results {
            ("".to_string(), vec![])
        }
        let mut parts = vec![];
        let mut total = 0;
        for (i, r) in results.iter().enumerate().iter() {
            let mut block = format!("[Source {}: {} | Score: {:.2}]\n{}", (i + 1), r.get(&"source".to_string()).cloned().unwrap_or("?".to_string()), r.get(&"score".to_string()).cloned().unwrap_or(0), r.get(&"text".to_string()).cloned().unwrap_or("".to_string()));
            if ((total + block.len()) > max_context_chars && total > 0) {
                break;
            }
            parts.push(block);
            total += block.len();
        }
        (parts.join(&"\n\n".to_string()), results)
    }
    /// Format search results for LLM context injection. Uses high default so all results are included for accurate numbers.
    pub fn format_context_for_llm(&self, results: Vec<HashMap>, max_tokens: i64) -> String {
        // Format search results for LLM context injection. Uses high default so all results are included for accurate numbers.
        format_context(results, /* max_chars= */ (max_tokens || DEFAULT_CONTEXT_MAX_CHARS))
    }
    /// Hybrid (semantic + lexical) search over all documents; results are enriched with tables.
    /// Uses hybrid (semantic + BM25) when available. For complex (long) queries, runs multi-query + RRF.
    pub fn search(&mut self, query: String, k: i64, rerank: bool) -> Result<Vec<HashMap>> {
        // Hybrid (semantic + lexical) search over all documents; results are enriched with tables.
        // Uses hybrid (semantic + BM25) when available. For complex (long) queries, runs multi-query + RRF.
        // TODO: import math
        let _norm_score = |r| {
            if r.get(&"rerank_score".to_string()).cloned().is_some() {
                (1.0_f64 / (1.0_f64 + math::exp(-r["rerank_score".to_string()])))
            }
            if r.get(&"score".to_string()).cloned().is_some() {
                r["score".to_string()]
            }
            ((r.get(&"fusion_score".to_string()).cloned() || 0) * 60).min(1.0_f64)
        };
        let _raw_to_result = |r| {
            let mut res = HashMap::from([("text".to_string(), r.get(&"text".to_string()).cloned().unwrap_or("".to_string())), ("url".to_string(), r.get(&"url".to_string()).cloned()), ("title".to_string(), r.get(&"title".to_string()).cloned()), ("score".to_string(), _norm_score(r)), ("source".to_string(), (r.get(&"url".to_string()).cloned() || r.get(&"title".to_string()).cloned() || r.get(&"source_file".to_string()).cloned() || "unknown".to_string()))]);
            if r.get(&"is_table".to_string()).cloned() {
                res["is_table".to_string()] = true;
                if r.get(&"sheet_name".to_string()).cloned().is_some() {
                    res["sheet_name".to_string()] = r["sheet_name".to_string()];
                }
                if r.get(&"columns".to_string()).cloned().is_some() {
                    res["columns".to_string()] = r["columns".to_string()];
                }
            }
            for key in ("date".to_string(), "row_index".to_string(), "source_file".to_string(), "dataset".to_string(), "sheet".to_string(), "dept_name".to_string(), "entity".to_string(), "category".to_string()).iter() {
                if r.get(&key).cloned().is_some() {
                    res[key] = r[&key];
                }
            }
            res
        };
        if (self._is_pro && self.rag_manager) {
            let mut expanded = _expand_romanian_query(query);
            let mut words = re::findall("[a-zăâîșț]+".to_string(), (query || "".to_string()).trim().to_string().to_lowercase());
            let mut word_count = words.len();
            let (mut complex_threshold, mut multi_query_enabled) = _get_complex_query_config();
            let mut is_complex = (word_count > complex_threshold || (query || "".to_string()).trim().to_string().len() > 80);
            let mut use_hybrid = (/* hasattr(self.rag_manager, "hybrid_search".to_string()) */ true && /* getattr */ None && self.rag_manager::chunks.len() > 0);
            let mut alpha = 0.5_f64;
            // try:
            {
                // TODO: from ui.state import get_settings
                let mut s = get_settings();
                let mut alpha = (s.get(&"setting_hybrid_alpha".to_string()).cloned().unwrap_or(0.5_f64) || 0.5_f64).to_string().parse::<f64>().unwrap_or(0.0);
            }
            // except Exception as exc:
            if (is_complex && multi_query_enabled) {
                let mut key_terms_str = _key_terms_query(query);
                if (!key_terms_str || key_terms_str.trim().to_string() == expanded.trim().to_string()) {
                    let mut key_terms_str = None;
                }
                if (key_terms_str && key_terms_str.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().len() >= 2) {
                    let mut k_fetch = (k * 2).max(10);
                    if use_hybrid {
                        let mut r1 = self.rag_manager::hybrid_search(expanded, /* k= */ k_fetch, /* alpha= */ alpha, /* rerank= */ false);
                        let mut r2 = self.rag_manager::hybrid_search(key_terms_str, /* k= */ k_fetch, /* alpha= */ alpha, /* rerank= */ false);
                    } else {
                        let mut r1 = self.rag_manager::search(expanded, /* k= */ k_fetch, /* rerank= */ false, /* scan_root= */ None);
                        let mut r2 = self.rag_manager::search(key_terms_str, /* k= */ k_fetch, /* rerank= */ false, /* scan_root= */ None);
                    }
                    let mut merged = _merge_results_rrf(vec![r1, r2], /* top_k= */ if rerank { (k * 3) } else { k }, /* k_rrf= */ 60);
                    if (rerank && merged && /* hasattr(self.rag_manager, "rerank".to_string()) */ true) {
                        let mut merged = self.rag_manager::rerank(query, merged, /* top_k= */ k);
                    } else {
                        let mut merged = merged[..k];
                    }
                    let mut results = merged.iter().map(|r| _raw_to_result(r)).collect::<Vec<_>>();
                    _enrich_results_with_tables(results)
                }
            }
            if use_hybrid {
                let mut raw = self.rag_manager::hybrid_search(expanded, /* k= */ k, /* alpha= */ alpha, /* rerank= */ rerank);
                let mut results = raw.iter().map(|r| _raw_to_result(r)).collect::<Vec<_>>();
            } else {
                let mut q_orig = query.trim().to_string();
                if (q_orig && expanded.trim().to_string() != q_orig) {
                    let mut r1 = self.rag_manager::search(q_orig, /* k= */ (k * 2), /* rerank= */ rerank, /* scan_root= */ None);
                    let mut r2 = self.rag_manager::search(expanded, /* k= */ (k * 2), /* rerank= */ rerank, /* scan_root= */ None);
                    let mut results = _merge_results_rrf(vec![r1, r2], /* top_k= */ k);
                } else {
                    let mut results = self.rag_manager::search(expanded, /* k= */ k, /* rerank= */ rerank, /* scan_root= */ None);
                }
                for r in results.iter() {
                    if !r.contains(&"source".to_string()) {
                        r["source".to_string()] = (r.get(&"url".to_string()).cloned() || r.get(&"title".to_string()).cloned() || "unknown".to_string());
                    }
                }
            }
        } else {
            let mut q = query.to_lowercase();
            let mut scored = vec![];
            for d in self._mem_docs.iter() {
                let mut txt = d.get(&"text".to_string()).cloned().unwrap_or("".to_string()).to_lowercase();
                if txt.contains(&q) {
                    let mut score = 0.9_f64;
                } else {
                    let mut hits = q.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().iter().filter(|w| txt.contains(&w)).map(|w| 1).collect::<Vec<_>>().iter().sum::<i64>();
                    let mut score = if hits { (0.5_f64 + (0.1_f64 * hits)).min(0.8_f64) } else { 0.0_f64 };
                }
                if score >= 0.3_f64 {
                    scored.push(HashMap::from([("text".to_string(), d.get(&"text".to_string()).cloned().unwrap_or("".to_string())[..1000]), ("score".to_string(), score), ("source".to_string(), d.get(&"source".to_string()).cloned()), ("collection".to_string(), d.get(&"collection".to_string()).cloned())]));
                }
            }
            scored.sort(/* key= */ |r| r["score".to_string()], /* reverse= */ true);
            let mut results = scored[..k];
        }
        Ok(_enrich_results_with_tables(results))
    }
    /// Semantic search (with synonym expansion); on no results: message + suggested questions from indexed data only.
    /// Responses contain only content from the vector DB, no generic text.
    pub fn search_with_fallback(&mut self, query: String, k: i64, min_score: f64, rerank: bool) -> HashMap {
        // Semantic search (with synonym expansion); on no results: message + suggested questions from indexed data only.
        // Responses contain only content from the vector DB, no generic text.
        let mut results = self.search(query, /* k= */ k, /* rerank= */ rerank);
        let mut stats = self.get_stats();
        let mut total_chunks = stats.get(&"chunks".to_string()).cloned().unwrap_or(0);
        let mut relevant_results = results.iter().filter(|r| r.get(&"score".to_string()).cloned().unwrap_or(0) >= min_score).map(|r| r).collect::<Vec<_>>();
        if relevant_results {
            HashMap::from([("success".to_string(), true), ("results".to_string(), relevant_results), ("message".to_string(), None), ("suggested_questions".to_string(), None)])
        }
        if total_chunks == 0 {
            HashMap::from([("success".to_string(), false), ("results".to_string(), vec![]), ("message".to_string(), "No indexed data. Load documents to search.".to_string()), ("suggested_questions".to_string(), None)])
        }
        let mut suggested = self.get_suggested_questions();
        if suggested {
            let mut msg = "No results found. You can search by one of the terms from the indexed data:".to_string();
        } else {
            let mut msg = "No results found. Could not extract suggestions from indexed data.".to_string();
        }
        HashMap::from([("success".to_string(), false), ("results".to_string(), vec![]), ("message".to_string(), msg), ("suggested_questions".to_string(), if suggested { suggested } else { None })])
    }
    /// Search terms extracted only from indexed content. No global phrasing.
    pub fn get_suggested_questions(&mut self) -> Result<Vec<String>> {
        // Search terms extracted only from indexed content. No global phrasing.
        if (!self._is_pro || !self.rag_manager) {
            vec![]
        }
        let mut stats = self.get_stats();
        let mut chunk_count = stats.get(&"chunks".to_string()).cloned().unwrap_or(0);
        let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        if self._suggested_cache.is_some() {
            let (mut ts, mut cached_count, mut questions) = self._suggested_cache;
            if ((now - ts) <= _SUGGESTED_CACHE_TTL && cached_count == chunk_count) {
                questions
            }
            self._suggested_cache = None;
        }
        // try:
        {
            if !self.rag_manager::qdrant {
                vec![]
            }
            let (mut points, _) = self.rag_manager::qdrant.scroll(self.rag_manager::collection_name, /* limit= */ 30, /* with_payload= */ true);
            let mut all_text = points.iter().map(|p| (p.payload || HashMap::new()).get(&"text".to_string()).cloned().unwrap_or("".to_string())).collect::<Vec<_>>().join(&"\n".to_string());
            let mut terms = _extract_terms_from_indexed_text(all_text, /* max_terms= */ 6);
            let mut result = terms;
            self._suggested_cache = (now, chunk_count, result);
            result
        }
        // except Exception as e:
    }
    /// Summary of indexed data for the user. From index only. Cache 5 min.
    pub fn get_data_summary(&mut self) -> HashMap {
        // Summary of indexed data for the user. From index only. Cache 5 min.
        let mut stats = self.get_stats();
        let mut total_chunks = stats.get(&"chunks".to_string()).cloned().unwrap_or(0);
        let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        if total_chunks == 0 {
            HashMap::from([("has_data".to_string(), false), ("message".to_string(), "No indexed data.".to_string()), ("topics".to_string(), vec![]), ("suggested_questions".to_string(), vec![])])
        }
        if self._summary_cache.is_some() {
            let (mut ts, mut cached_count, mut summary) = self._summary_cache;
            if ((now - ts) <= _SUGGESTED_CACHE_TTL && cached_count == total_chunks) {
                summary
            }
            self._summary_cache = None;
        }
        let mut suggested = self.get_suggested_questions();
        let mut summary = HashMap::from([("has_data".to_string(), true), ("message".to_string(), format!("{} indexed chunks.", total_chunks)), ("topics".to_string(), suggested[..5]), ("suggested_questions".to_string(), suggested)]);
        self._summary_cache = (now, total_chunks, summary);
        summary
    }
    /// Get RAG statistics. Cache 1s to avoid repeated Qdrant calls in same request.
    pub fn get_stats(&mut self) -> Result<HashMap> {
        // Get RAG statistics. Cache 1s to avoid repeated Qdrant calls in same request.
        let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        if self._stats_cache.is_some() {
            let (mut ts, mut cached) = self._stats_cache;
            if (now - ts) < 1.0_f64 {
                cached
            }
            self._stats_cache = None;
        }
        let mut stats = HashMap::from([("documents_uploaded".to_string(), self.documents.len()), ("collections".to_string(), self.collections::iter().iter().map(|(n, d)| (n, d.len())).collect::<HashMap<_, _>>()), ("total_collection_size".to_string(), self.documents.iter().map(|d| d.get(&"size".to_string()).cloned().unwrap_or(0)).collect::<Vec<_>>().iter().sum::<i64>()), ("initialized".to_string(), self.initialized), ("backend".to_string(), if self._is_pro { "LocalRAG".to_string() } else { "in-memory".to_string() })]);
        if (self._is_pro && self.rag_manager) {
            // try:
            {
                let mut rag_stats = self.rag_manager::get_stats();
                stats["chunks".to_string()] = rag_stats.get(&"total_chunks".to_string()).cloned().unwrap_or(0);
                stats["collection".to_string()] = rag_stats.get(&"collection".to_string()).cloned().unwrap_or("".to_string());
                stats["documents".to_string()] = stats["chunks".to_string()];
            }
            // except Exception as exc:
        }
        self._stats_cache = (now, stats);
        Ok(stats)
    }
    pub fn clear_collection(&mut self, collection_name: String) -> bool {
        self.collections[collection_name] = vec![];
        self._mem_docs = self._mem_docs.iter().filter(|d| d.get(&"collection".to_string()).cloned() != collection_name).map(|d| d).collect::<Vec<_>>();
        true
    }
    /// Clear the entire Qdrant vector index. Use to remove wrongly indexed data, then re-scan only the desired path.
    pub fn clear_vector_index(&mut self) -> bool {
        // Clear the entire Qdrant vector index. Use to remove wrongly indexed data, then re-scan only the desired path.
        if (!self._is_pro || !self.rag_manager) {
            false
        }
        if !/* hasattr(self.rag_manager, "clear_vector_index".to_string()) */ true {
            false
        }
        let mut ok = self.rag_manager::clear_vector_index();
        if ok {
            self._stats_cache = None;
            self._suggested_cache = None;
            self._summary_cache = None;
        }
        ok
    }
    pub fn list_documents(&self, collection_name: Option<String>) -> Vec<HashMap> {
        if collection_name {
            self.collections::get(&collection_name).cloned().unwrap_or(vec![])
        }
        self.documents
    }
    /// List real sources from the vector DB (Qdrant). For UI display.
    /// Returns ALL sources in the collection; no filter by current dataset path.
    pub fn list_indexed_sources(&mut self) -> Result<Vec<HashMap>> {
        // List real sources from the vector DB (Qdrant). For UI display.
        // Returns ALL sources in the collection; no filter by current dataset path.
        if (!self._is_pro || !self.rag_manager || !/* getattr */ None) {
            vec![]
        }
        // try:
        {
            let mut client = self.rag_manager::qdrant;
            let mut col = self.rag_manager::collection_name;
            let mut seen = HashSet::new();
            let mut out = vec![];
            let mut offset = None;
            while true {
                let (mut points, mut offset) = client.scroll(/* collection_name= */ col, /* limit= */ 200, /* offset= */ offset, /* with_payload= */ true);
                if !points {
                    break;
                }
                for p in points.iter() {
                    let mut payload = (p.payload || HashMap::new());
                    let mut url = (payload.get(&"url".to_string()).cloned() || payload.get(&"source".to_string()).cloned() || "".to_string());
                    let mut title = (payload.get(&"title".to_string()).cloned() || "".to_string());
                    let mut key = (url, title);
                    if (seen.contains(&key) || !(url || title)) {
                        continue;
                    }
                    seen.insert(key);
                    out.push(HashMap::from([("name".to_string(), if url { (title || url.split("/".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[-1]) } else { "?".to_string() }), ("path".to_string(), url), ("title".to_string(), title), ("source".to_string(), url)]));
                }
                if offset.is_none() {
                    break;
                }
            }
            out
        }
        // except Exception as e:
    }
    /// Get full load report from the vector DB: all chunks, chars, breakdown by source and scan_root.
    /// Returns None if not using Qdrant; otherwise a dict with total_chunks, total_characters,
    /// unique_sources, by_source (list of {url, title, chunks, character}), by_scan_root (if present),
    /// and collection_name. Use for clear reports on existing load.
    pub fn get_vector_load_report(&mut self) -> Result<Option<HashMap<String, Box<dyn std::any::Any>>>> {
        // Get full load report from the vector DB: all chunks, chars, breakdown by source and scan_root.
        // Returns None if not using Qdrant; otherwise a dict with total_chunks, total_characters,
        // unique_sources, by_source (list of {url, title, chunks, character}), by_scan_root (if present),
        // and collection_name. Use for clear reports on existing load.
        if (!self._is_pro || !self.rag_manager || !/* getattr */ None) {
            None
        }
        // try:
        {
            let mut client = self.rag_manager::qdrant;
            let mut col = self.rag_manager::collection_name;
            let mut total_chunks = 0;
            let mut total_characters = 0;
            let mut by_url = HashMap::new();
            let mut by_scan_root = HashMap::new();
            let mut offset = None;
            while true {
                let (mut points, mut offset) = client.scroll(/* collection_name= */ col, /* limit= */ 500, /* offset= */ offset, /* with_payload= */ true);
                if !points {
                    break;
                }
                for p in points.iter() {
                    let mut payload = (p.payload || HashMap::new());
                    let mut text = (payload.get(&"text".to_string()).cloned() || "".to_string()).trim().to_string();
                    let mut url = (payload.get(&"url".to_string()).cloned() || payload.get(&"source".to_string()).cloned() || "".to_string());
                    let mut title = ((payload.get(&"title".to_string()).cloned() || "".to_string()).trim().to_string() || if url { url.split("/".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[-1] } else { "?".to_string() });
                    let mut scan_root = ((payload.get(&"scan_root".to_string()).cloned() || "".to_string()).trim().to_string() || None);
                    total_chunks += 1;
                    total_characters += text.len();
                    let mut key = (url, title);
                    if !by_url.contains(&key) {
                        by_url[key] = HashMap::from([("url".to_string(), url), ("title".to_string(), title), ("chunks".to_string(), 0), ("characters".to_string(), 0)]);
                    }
                    by_url[&key]["chunks".to_string()] += 1;
                    by_url[&key]["characters".to_string()] += text.len();
                    if scan_root {
                        if !by_scan_root.contains(&scan_root) {
                            by_scan_root[scan_root] = HashMap::from([("chunks".to_string(), 0), ("urls".to_string(), HashSet::new())]);
                        }
                        by_scan_root[&scan_root]["chunks".to_string()] += 1;
                        by_scan_root[&scan_root]["urls".to_string()].insert((url || title));
                    }
                }
                if offset.is_none() {
                    break;
                }
            }
            let mut by_source = { let mut v = by_url.values().clone(); v.sort(); v };
            for s in by_source.iter() {
                s["characters".to_string()] = s["characters".to_string()].to_string().parse::<i64>().unwrap_or(0);
            }
            let mut report_by_scan_root = { let mut v = by_scan_root.iter().clone(); v.sort(); v }.iter().map(|(root, data)| HashMap::from([("scan_root".to_string(), root), ("chunks".to_string(), data["chunks".to_string()]), ("sources_count".to_string(), data["urls".to_string()].len())])).collect::<Vec<_>>();
            HashMap::from([("collection_name".to_string(), col), ("total_chunks".to_string(), total_chunks), ("total_characters".to_string(), total_characters), ("unique_sources".to_string(), by_url.len()), ("by_source".to_string(), by_source), ("by_scan_root".to_string(), report_by_scan_root)])
        }
        // except Exception as e:
    }
}

/// Return (word_threshold, multi_query_enabled). Uses config if available.
pub fn _get_complex_query_config() -> Result<(i64, bool)> {
    // Return (word_threshold, multi_query_enabled). Uses config if available.
    // try:
    {
        // TODO: from config_enhanced import Config
        let mut thresh = /* getattr */ COMPLEX_QUERY_WORD_THRESHOLD.to_string().parse::<i64>().unwrap_or(0);
        let mut enabled = (/* getattr */ true != 0);
        (thresh, enabled)
    }
    // except Exception as _e:
}

/// Extract a short string of important terms for retrieval (domain terms + synonym dict keys/values).
pub fn _key_terms_query(query: String, max_terms: i64) -> String {
    // Extract a short string of important terms for retrieval (domain terms + synonym dict keys/values).
    if (!query || !query.trim().to_string()) {
        query
    }
    let mut q = query.trim().to_string().to_lowercase();
    let mut words = re::findall("[a-zăâîșț]+".to_string(), q);
    let mut seen = HashSet::new();
    let mut terms = vec![];
    let mut dict_terms = _SINONIME_RO_CAUTARE.keys().into_iter().collect::<HashSet<_>>();
    for vals in _SINONIME_RO_CAUTARE.values().iter() {
        dict_terms.extend(vals.iter().filter(|v| (/* /* isinstance(v, str) */ */ true && v.len() > 1)).map(|v| v).collect::<Vec<_>>());
    }
    for w in words.iter() {
        if (_RO_STOPWORDS.contains(&w) || w.len() < 2) {
            continue;
        }
        if seen.contains(&w.to_lowercase()) {
            continue;
        }
        if (dict_terms.contains(&w) || w.len() > 3) {
            seen.insert(w.to_lowercase());
            terms.push(w);
            if terms.len() >= max_terms {
                break;
            }
        }
    }
    if !terms {
        for w in words.iter() {
            if (!_RO_STOPWORDS.contains(&w) && w.len() > 2 && !seen.contains(&w.to_lowercase())) {
                seen.insert(w.to_lowercase());
                terms.push(w);
                if terms.len() >= max_terms {
                    break;
                }
            }
        }
    }
    if terms { terms.join(&" ".to_string()) } else { q[..200].trim().to_string() }
}

/// Extract only terms/labels that actually appear in the indexed text. No global content.
pub fn _extract_terms_from_indexed_text(text: String, max_terms: i64) -> Vec<String> {
    // Extract only terms/labels that actually appear in the indexed text. No global content.
    if (!text || !text.trim().to_string()) {
        vec![]
    }
    let is_label = |s| {
        if (!s || s.len() < 2 || s.len() > 60) {
            false
        }
        let mut s_clean = s.trim().to_string();
        if regex::Regex::new(&"^[\\d\\s.,%]+$".to_string()).unwrap().is_match(&s_clean) {
            false
        }
        (regex::Regex::new(&"[a-zA-Zăâîșț]".to_string()).unwrap().is_match(&s_clean) != 0)
    };
    let mut seen_lower = HashSet::new();
    let mut terms = vec![];
    let mut lines = text.lines().map(|s| s.to_string()).collect::<Vec<String>>().iter().filter(|ln| ln.trim().to_string()).map(|ln| ln.trim().to_string()).collect::<Vec<_>>();
    for line in lines.iter() {
        if line.len() > 80 {
            continue;
        }
        if line.contains(&"|".to_string()) {
            let mut parts = line.split("|".to_string()).map(|s| s.to_string()).collect::<Vec<String>>().iter().filter(|p| (p.trim().to_string() && p.trim().to_string() != "---".to_string())).map(|p| p.trim().to_string()).collect::<Vec<_>>();
            for p in parts.iter() {
                if (is_label(p) && !seen_lower.contains(&p.to_lowercase())) {
                    seen_lower.insert(p.to_lowercase());
                    terms.push(p);
                    if terms.len() >= max_terms {
                        terms
                    }
                }
            }
            continue;
        }
        if (is_label(line) && !seen_lower.contains(&line.to_lowercase())) {
            seen_lower.insert(line.to_lowercase());
            terms.push(line);
            if terms.len() >= max_terms {
                terms
            }
        }
    }
    terms[..max_terms]
}

/// Extract markdown tables from text (| A | B |). Returns list of tables; each table = list of dicts (keys = header).
pub fn _parse_markdown_tables(text: String) -> Vec<Vec<HashMap<String, String>>> {
    // Extract markdown tables from text (| A | B |). Returns list of tables; each table = list of dicts (keys = header).
    if (!text || !text.contains(&"|".to_string())) {
        vec![]
    }
    let row_cells = |line| {
        let mut parts = line.split("|".to_string()).map(|s| s.to_string()).collect::<Vec<String>>();
        if parts.len() < 2 {
            vec![]
        }
        let mut out = parts[1..-1].iter().map(|p| p.trim().to_string()).collect::<Vec<_>>();
        if out { out } else { parts.iter().filter(|p| p.trim().to_string()).map(|p| p.trim().to_string()).collect::<Vec<_>>() }
    };
    let mut tables = vec![];
    let mut lines = text.lines().map(|s| s.to_string()).collect::<Vec<String>>();
    let mut i = 0;
    while i < lines.len() {
        let mut line = lines[&i];
        if !line.contains(&"|".to_string()) {
            i += 1;
            continue;
        }
        let mut cells = row_cells(line);
        if !cells {
            i += 1;
            continue;
        }
        if regex::Regex::new(&"^[\\s\\-:]+$".to_string()).unwrap().is_match(&cells.join(&"".to_string())) {
            i += 1;
            continue;
        }
        let mut headers = cells;
        i += 1;
        if (i < lines.len() && lines[&i].contains(&"|".to_string())) {
            let mut sep = row_cells(lines[&i]);
            if (sep && regex::Regex::new(&"^[\\-\\s:]+$".to_string()).unwrap().is_match(&sep.join(&" ".to_string()))) {
                i += 1;
            }
        }
        let mut rows = vec![];
        while i < lines.len() {
            let mut row_line = lines[&i];
            if !row_line.contains(&"|".to_string()) {
                break;
            }
            let mut row_cells_list = row_cells(row_line);
            if row_cells_list.len() != headers.len() {
                break;
            }
            rows.push(/* dict(headers.iter().zip(row_cells_list.iter())) */ HashMap::new());
            i += 1;
        }
        if rows {
            tables.push(rows);
        }
    }
    tables
}

/// Add 'tables' and 'has_table' fields to each result that contains markdown tables.
pub fn _enrich_results_with_tables(results: Vec<HashMap>) -> Vec<HashMap> {
    // Add 'tables' and 'has_table' fields to each result that contains markdown tables.
    for r in results.iter() {
        let mut text = (r.get(&"text".to_string()).cloned() || "".to_string());
        let mut tables = _parse_markdown_tables(text);
        r["has_table".to_string()] = tables.len() > 0;
        r["tables".to_string()] = tables;
    }
    results
}

/// Expand query with synonyms for better semantic search.
/// For long queries (word count > threshold), allows more synonyms and caps total length.
pub fn _expand_romanian_query(query: String) -> String {
    // Expand query with synonyms for better semantic search.
    // For long queries (word count > threshold), allows more synonyms and caps total length.
    if (!query || !query.trim().to_string()) {
        query
    }
    let mut q = query.trim().to_string().to_lowercase();
    let mut words = re::findall("[a-zăâîșț]+".to_string(), q);
    let mut word_count = words.len();
    let mut max_syn = if word_count > COMPLEX_QUERY_WORD_THRESHOLD { MAX_SYNONYMS_COMPLEX } else { MAX_SYNONYMS_SIMPLE };
    let mut extra = vec![];
    for w in words.iter() {
        if _SINONIME_RO_CAUTARE.contains(&w) {
            for syn in _SINONIME_RO_CAUTARE[&w].iter() {
                if (!q.contains(&syn) && !extra.contains(&syn)) {
                    extra.push(syn);
                }
            }
        }
    }
    if !extra {
        query
    }
    let mut expanded = ((query + " ".to_string()) + extra[..max_syn].join(&" ".to_string()));
    if (MAX_EXPANDED_QUERY_CHARS && expanded.len() > MAX_EXPANDED_QUERY_CHARS) {
        let mut truncated = expanded[..MAX_EXPANDED_QUERY_CHARS];
        let mut expanded = if truncated.contains(&" ".to_string()) { truncated.rsplit(/* maxsplit= */ 1).map(|s| s.to_string()).collect::<Vec<String>>()[0] } else { truncated };
    }
    expanded
}

/// Merge multiple search result lists with Reciprocal Rank Fusion. Keeps best of original + expanded query.
pub fn _merge_results_rrf(result_lists: Vec<Vec<HashMap>>, top_k: i64, k_rrf: i64) -> Vec<HashMap> {
    // Merge multiple search result lists with Reciprocal Rank Fusion. Keeps best of original + expanded query.
    if !result_lists {
        vec![]
    }
    let mut key_to_item = HashMap::new();
    let mut key_to_rrf = HashMap::new();
    for rank_list in result_lists.iter() {
        for (rank, r) in rank_list.iter().enumerate().iter() {
            let mut url = (r.get(&"url".to_string()).cloned() || r.get(&"title".to_string()).cloned() || "".to_string());
            let mut text = (r.get(&"text".to_string()).cloned() || "".to_string())[..300];
            let mut key = (url, text);
            if !key_to_item.contains(&key) {
                key_to_item[key] = r;
                key_to_rrf[key] = 0.0_f64;
            }
            key_to_rrf[key] += (1.0_f64 / (k_rrf + rank));
        }
    }
    let mut sorted_keys = { let mut v = key_to_rrf.keys().clone(); v.sort(); v }[..top_k];
    let mut out = vec![];
    for key in sorted_keys.iter() {
        let mut item = key_to_item[&key].clone();
        item["score".to_string()] = (key_to_rrf[&key] / result_lists.len());
        out.push(item);
    }
    out
}

/// Format retrieved chunks for LLM context. Excel row results get a clear Row/Sheet/Date prefix.
/// Uses a high default max_chars so all results are included for accurate numbers; no truncation.
pub fn format_context(results: Vec<HashMap>, max_chars: i64) -> String {
    // Format retrieved chunks for LLM context. Excel row results get a clear Row/Sheet/Date prefix.
    // Uses a high default max_chars so all results are included for accurate numbers; no truncation.
    if max_chars.is_none() {
        let mut max_chars = DEFAULT_CONTEXT_MAX_CHARS;
    }
    if !results {
        "".to_string()
    }
    let mut parts = vec![];
    for r in results.iter() {
        let mut text = (r.get(&"text".to_string()).cloned().unwrap_or("".to_string()) || "".to_string());
        let mut source = (r.get(&"source".to_string()).cloned() || r.get(&"title".to_string()).cloned() || r.get(&"url".to_string()).cloned() || r.get(&"source_file".to_string()).cloned() || "?".to_string());
        let mut score = r.get(&"score".to_string()).cloned().unwrap_or(0);
        if (r.get(&"sheet_name".to_string()).cloned().is_some() || r.get(&"date".to_string()).cloned().is_some() || r.get(&"row_index".to_string()).cloned().is_some()) {
            let mut prefix_parts = vec![];
            if r.get(&"sheet_name".to_string()).cloned().is_some() {
                prefix_parts.push(format!("Sheet: {}", r.get(&"sheet_name".to_string()).cloned()));
            }
            if r.get(&"date".to_string()).cloned().is_some() {
                prefix_parts.push(format!("Date: {}", r.get(&"date".to_string()).cloned()));
            }
            if r.get(&"row_index".to_string()).cloned().is_some() {
                prefix_parts.push(format!("Row: {}", r.get(&"row_index".to_string()).cloned()));
            }
            let mut prefix = prefix_parts.join(&" | ".to_string());
            let mut fmt = format!("[{}] {} (Source: {})", prefix, text, source);
        } else {
            let mut fmt = format!("[Score: {:.2}] {} (Source: {})", score, text, source);
        }
        parts.push(fmt);
    }
    let mut out = parts.join(&"\n\n".to_string());
    if out.len() > max_chars { out[..max_chars] } else { out }
}

/// true if file_path is the same as root_path or under it (for filesystem paths only).
pub fn _path_under_root(file_path: String, root_path: String) -> Result<bool> {
    // true if file_path is the same as root_path or under it (for filesystem paths only).
    if (!file_path || !root_path || file_path.starts_with(&*"http".to_string()) || root_path.starts_with(&*"http".to_string())) {
        true
    }
    // try:
    {
        let mut fp = PathBuf::from(file_path).canonicalize().unwrap_or_default();
        let mut root = PathBuf::from(root_path).canonicalize().unwrap_or_default();
        (fp == root || fp.parents.contains(&root))
    }
    // except (OSError, ValueError) as _e:
}

/// Split aggregated extraction output back into per-source blocks.
/// 
/// content_extractor emits blocks separated by ``=== PAGE/FILE: … ===``
/// headers.  If parsing fails we distribute proportionally by char count.
pub fn _split_aggregated_text(content: String, sources: Vec<HashMap>) -> Vec<String> {
    // Split aggregated extraction output back into per-source blocks.
    // 
    // content_extractor emits blocks separated by ``=== PAGE/FILE: … ===``
    // headers.  If parsing fails we distribute proportionally by char count.
    let mut header_re = regex::Regex::new(&"^=== (?:PAGE|FILE): .+? ===$".to_string()).unwrap();
    let mut splits = header_re.split(content).map(|s| s.to_string()).collect::<Vec<String>>();
    if (splits && !splits[0].trim().to_string()) {
        let mut splits = splits[1..];
    }
    if splits.len() >= sources.len() {
        splits[..sources.len()].iter().map(|s| s.trim().to_string()).collect::<Vec<_>>()
    }
    let mut total = sources.iter().map(|s| s.get(&"chars".to_string()).cloned().unwrap_or(1)).collect::<Vec<_>>().iter().sum::<i64>().max(1);
    let (mut blocks, mut pos) = (vec![], 0);
    for src in sources.iter() {
        let mut length = 100.max(((content.len() * src.get(&"chars".to_string()).cloned().unwrap_or(1)) / total).to_string().parse::<i64>().unwrap_or(0));
        blocks.push(content[pos..(pos + length)].trim().to_string());
        pos += length;
    }
    blocks
}

/// Get or create the global RAG integration singleton.
pub async fn get_rag() -> RAGIntegration {
    // Get or create the global RAG integration singleton.
    // global/nonlocal _rag_integration
    if _rag_integration.is_none() {
        let mut _rag_integration = RAGIntegration();
        _rag_integration.initialize().await;
    }
    _rag_integration
}
