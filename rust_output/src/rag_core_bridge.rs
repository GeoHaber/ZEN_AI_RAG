/// rag_core_bridge::py — Bridge between ZEN_AI_RAG and the shared rag_core library.
/// 
/// This adapter wraps rag_core components while preserving ZEN_AI_RAG's
/// Qdrant-based persistent storage, metadata propagation, and rag_db::py
/// SQLite layer.
/// 
/// It exposes the same interface as ``LocalRAG`` so existing code
/// can use it as a drop-in replacement.
/// 
/// Pipeline::
/// 
/// Documents → rag_core.TextChunker → Embed (rag_core) → Dedup (rag_core)
/// ↓                       ↓
/// rag_db::py (SQLite)    Qdrant vector store
/// ↓
/// Query → Dense + BM25 (rag_core) → RRF (rag_core) → Rerank (rag_core)

use anyhow::{Result, Context};
use crate::bm25_index::{BM25Index};
use crate::cache::{SemanticCache};
use crate::chunker::{ChunkerConfig, TextChunker};
use crate::config_system::{config};
use crate::dedup::{DeduplicationManager};
use crate::embeddings::{EmbeddingManager};
use crate::fusion::{reciprocal_rank_fusion};
use crate::reranker::{RerankerManager};
use std::collections::HashMap;
use std::collections::HashSet;
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static QDRANTCLIENT: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static DISTANCE: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static VECTORPARAMS: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static POINTSTRUCT: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

/// Production-grade RAG with **rag_core** algorithms, Qdrant storage,
/// metadata propagation, and optional SQLite (rag_db::py) persistence.
#[derive(Debug, Clone)]
pub struct LocalRAGv2 {
    pub cache_dir: String,
    pub _lock: std::sync::Mutex<()>,
    pub _embed_mgr: EmbeddingManager,
    pub embedding_dim: String,
    pub model: String,
    pub _bm25: BM25Index,
    pub _reranker: RerankerManager,
    pub _cache: SemanticCache,
    pub chunker: TextChunker,
    pub _dedup: DeduplicationManager,
    pub db: Option<RAGDatabase>,
    pub collection_name: String,
    pub chunks: Vec<HashMap>,
    pub chunk_hashes: HashSet<String>,
    pub index: String,
    pub cross_encoder: Option<serde_json::Value>,
    pub qdrant: QdrantClient,
    pub read_only: bool,
    pub extractor: UniversalExtractor,
}

impl LocalRAGv2 {
    pub fn new(cache_dir: Option<PathBuf>) -> Self {
        Self {
            cache_dir: (cache_dir || (config::BASE_DIR / "rag_storage".to_string())),
            _lock: std::sync::Mutex::new(()),
            _embed_mgr: EmbeddingManager(/* model_name= */ model_name, /* prefer_code= */ false, /* device= */ device),
            embedding_dim: self._embed_mgr.dimension,
            model: self._embed_mgr._model,
            _bm25: BM25Index(/* code_aware= */ false),
            _reranker: RerankerManager(/* model_name= */ reranker_model),
            _cache: SemanticCache(/* ttl= */ 3600.0_f64, /* encoder= */ self._embed_mgr),
            chunker: TextChunker(ChunkerConfig(/* CHUNK_SIZE= */ 800, /* CHUNK_OVERLAP= */ 100)),
            _dedup: DeduplicationManager(/* similarity_threshold= */ 0.95_f64),
            db: None,
            collection_name: format!("zenai_knowledge_{}", self.embedding_dim),
            chunks: Vec::new(),
            chunk_hashes: HashSet::new(),
            index: self,
            cross_encoder: None,
            qdrant: Default::default(),
            read_only: false,
            extractor: Default::default(),
        }
    }
    pub fn _init_collection(&mut self) -> Result<()> {
        // try:
        {
            let mut collections = self.qdrant.get_collections().collections;
            let mut exists = collections::iter().map(|c| c.name == self.collection_name).collect::<Vec<_>>().iter().any(|v| *v);
            if exists {
                let mut info = self.qdrant.get_collection(self.collection_name);
                if info.config::params.vectors.size != self.embedding_dim {
                    logger.warning("[RAG] Dimension mismatch — recreating collection".to_string());
                    self.qdrant.delete_collection(self.collection_name);
                    let mut exists = false;
                }
            }
            if !exists {
                self.qdrant.create_collection(/* collection_name= */ self.collection_name, /* vectors_config= */ VectorParams(/* size= */ self.embedding_dim, /* distance= */ Distance.COSINE));
                logger.info(format!("[RAG] Created Qdrant collection: {}", self.collection_name));
            }
        }
        // except Exception as e:
    }
    pub fn _load_metadata(&mut self) -> Result<()> {
        if !self.qdrant {
            return;
        }
        // try:
        {
            let (mut points, _) = self.qdrant.scroll(/* collection_name= */ self.collection_name, /* limit= */ 10000, /* with_payload= */ true, /* with_vectors= */ false);
            self.chunks = vec![];
            self.chunk_hashes = HashSet::new();
            for p in points.iter() {
                let mut text = p.payload.get(&"text".to_string()).cloned().unwrap_or("".to_string());
                let mut text_hash = hashlib::sha256(text.as_bytes().to_vec()).hexdigest();
                self.chunks.push(HashMap::from([("text".to_string(), text), ("url".to_string(), p.payload.get(&"url".to_string()).cloned()), ("title".to_string(), p.payload.get(&"title".to_string()).cloned()), ("metadata".to_string(), p.payload.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new())), ("hash".to_string(), text_hash), ("qdrant_id".to_string(), p.id)]));
                self.chunk_hashes.insert(text_hash);
            }
            if self.chunks {
                self._bm25.build(self.chunks.iter().map(|c| c["text".to_string()]).collect::<Vec<_>>());
                logger.info(format!("[RAG] Loaded {} chunks into search buffers", self.chunks.len()));
            }
        }
        // except Exception as e:
    }
    pub fn warmup(&mut self) -> () {
        logger.info("[RAG] Warming up models...".to_string());
        self._embed_mgr.encode_single("warmup".to_string(), /* normalize= */ true);
        self._reranker.load();
        if self._reranker.is_loaded {
            self._reranker.rerank("warmup".to_string(), vec!["warmup doc".to_string()], /* top_k= */ 1);
        }
        logger.info("[RAG] Models warmed up and ready.".to_string());
    }
    pub fn ntotal(&self) -> i64 {
        // try:
        {
            self.qdrant.get_collection(self.collection_name).points_count
        }
        // except Exception as _e:
    }
    pub fn chunk_documents(&mut self, documents: Vec<HashMap>, chunk_size: i64, overlap: i64, filter_junk: bool) -> Vec<HashMap> {
        self.chunker::config::CHUNK_SIZE = chunk_size;
        self.chunker::config::CHUNK_OVERLAP = overlap;
        let mut all_chunks = vec![];
        for doc in documents.iter() {
            let mut content = doc.get(&"content".to_string()).cloned().unwrap_or("".to_string());
            if (!content || !content.trim().to_string()) {
                continue;
            }
            let mut meta = HashMap::from([("url".to_string(), doc.get(&"url".to_string()).cloned()), ("title".to_string(), doc.get(&"title".to_string()).cloned())]);
            let mut strategy = /* getattr */ "sentence".to_string();
            let mut doc_chunks = self.chunker::chunk_document(content, /* metadata= */ meta, /* strategy= */ strategy, /* filter_junk= */ filter_junk);
            for c in doc_chunks.iter() {
                let mut chunk_text = c.text.trim().to_string();
                if chunk_text.len() > 20 {
                    all_chunks.push(HashMap::from([("url".to_string(), c.metadata.get(&"url".to_string()).cloned()), ("title".to_string(), c.metadata.get(&"title".to_string()).cloned()), ("text".to_string(), chunk_text), ("chunk_index".to_string(), c.chunk_index), ("metadata".to_string(), doc.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new()))]));
                }
            }
        }
        all_chunks
    }
    pub fn build_index(&mut self, documents: Vec<HashMap>, dedup_threshold: Option<f64>, filter_junk: bool) -> Result<()> {
        if !self.qdrant {
            logger.warning("[RAG] Skipping indexing: Storage not available".to_string());
            return;
        }
        let _ctx = self._lock;
        {
            self._cache.clear();
            let mut start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            let mut threshold = (dedup_threshold || 0.95_f64);
            let mut chunks_added = 0;
            for doc in documents.iter() {
                let mut doc_id = None;
                if self.db {
                    // try:
                    {
                        let mut doc_id = self.db.add_document(/* url= */ doc.get(&"url".to_string()).cloned().unwrap_or("".to_string()), /* title= */ doc.get(&"title".to_string()).cloned().unwrap_or("".to_string()), /* content= */ doc.get(&"content".to_string()).cloned().unwrap_or("".to_string()));
                    }
                    // except Exception as e:
                }
                let mut doc_chunks = self.chunk_documents(vec![doc], /* filter_junk= */ filter_junk);
                if !doc_chunks {
                    continue;
                }
                let mut doc_chunks = self._dedup.deduplicate_chunks(doc_chunks);
                let mut BATCH_SIZE = 32;
                for i in (0..doc_chunks.len()).step_by(BATCH_SIZE as usize).iter() {
                    let mut batch = doc_chunks[i..(i + BATCH_SIZE)];
                    let mut texts = batch.iter().map(|c| c["text".to_string()]).collect::<Vec<_>>();
                    let mut embeddings = self._embed_mgr.encode(texts, /* batch_size= */ BATCH_SIZE);
                    let mut points = vec![];
                    let mut db_chunks = vec![];
                    for (chunk, embedding) in batch.iter().zip(embeddings::iter()).iter() {
                        let mut text = chunk["text".to_string()];
                        let mut text_hash = hashlib::sha256(text.as_bytes().to_vec()).hexdigest();
                        if self.chunk_hashes.contains(&text_hash) {
                            continue;
                        }
                        // try:
                        {
                            let mut hits = self.qdrant.query_points(/* collection_name= */ self.collection_name, /* query= */ embedding.tolist(), /* limit= */ 1, /* score_threshold= */ threshold).points;
                            if hits {
                                continue;
                            }
                        }
                        // except Exception as _e:
                        let mut point_id = int(hashlib::sha256(text_hash.as_bytes().to_vec()).hexdigest()[..16], 16);
                        let mut payload = HashMap::from([("text".to_string(), text), ("url".to_string(), chunk.get(&"url".to_string()).cloned()), ("title".to_string(), chunk.get(&"title".to_string()).cloned()), ("metadata".to_string(), chunk.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new()))]);
                        points.push(PointStruct(/* id= */ point_id, /* vector= */ embedding.tolist(), /* payload= */ payload));
                        self.chunk_hashes.insert(text_hash);
                        self.chunks.push(HashMap::from([("text".to_string(), text), ("url".to_string(), chunk.get(&"url".to_string()).cloned()), ("title".to_string(), chunk.get(&"title".to_string()).cloned()), ("metadata".to_string(), chunk.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new())), ("hash".to_string(), text_hash), ("qdrant_id".to_string(), point_id)]));
                        if (self.db && doc_id.is_some()) {
                            db_chunks.push(HashMap::from([("doc_id".to_string(), doc_id), ("chunk_index".to_string(), chunk.get(&"chunk_index".to_string()).cloned().unwrap_or(0)), ("text".to_string(), text), ("vector".to_string(), embedding), ("metadata".to_string(), chunk.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new()))]));
                        }
                    }
                    if points {
                        self.qdrant.upsert(/* collection_name= */ self.collection_name, /* points= */ points);
                        chunks_added += points.len();
                    }
                    if (db_chunks && self.db) {
                        // try:
                        {
                            self.db.add_chunks(db_chunks);
                        }
                        // except Exception as e:
                    }
                }
            }
            if self.chunks {
                self._bm25.build(self.chunks.iter().map(|c| c["text".to_string()]).collect::<Vec<_>>());
            }
            let mut elapsed = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start_time);
            logger.info(format!("[RAG] Ingested {} chunks in {:.2}s", chunks_added, elapsed));
        }
    }
    pub fn add_chunks(&mut self, chunks: Vec<HashMap>, dedup_threshold: Option<f64>) -> Result<()> {
        if !self.qdrant {
            return;
        }
        let _ctx = self._lock;
        {
            let mut threshold = (dedup_threshold || 0.95_f64);
            let mut points = vec![];
            for chunk in chunks.iter() {
                let mut text = chunk.get(&"text".to_string()).cloned().unwrap_or("".to_string());
                if !text {
                    continue;
                }
                let mut text_hash = hashlib::sha256(text.as_bytes().to_vec()).hexdigest();
                if self.chunk_hashes.contains(&text_hash) {
                    continue;
                }
                let mut embedding = self._embed_mgr.encode_single(text, /* normalize= */ true);
                // try:
                {
                    let mut hits = self.qdrant.query_points(/* collection_name= */ self.collection_name, /* query= */ embedding.tolist(), /* limit= */ 1, /* score_threshold= */ threshold).points;
                    if hits {
                        continue;
                    }
                }
                // except Exception as _e:
                let mut point_id = int(hashlib::sha256(text_hash.as_bytes().to_vec()).hexdigest()[..16], 16);
                points.push(PointStruct(/* id= */ point_id, /* vector= */ embedding.tolist(), /* payload= */ HashMap::from([("text".to_string(), text), ("url".to_string(), chunk.get(&"url".to_string()).cloned()), ("title".to_string(), chunk.get(&"title".to_string()).cloned()), ("metadata".to_string(), chunk.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new()))])));
                self.chunk_hashes.insert(text_hash);
                self.chunks.push(HashMap::from([("text".to_string(), text), ("url".to_string(), chunk.get(&"url".to_string()).cloned()), ("title".to_string(), chunk.get(&"title".to_string()).cloned()), ("metadata".to_string(), chunk.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new())), ("hash".to_string(), text_hash), ("qdrant_id".to_string(), point_id)]));
            }
            if points {
                self.qdrant.upsert(/* collection_name= */ self.collection_name, /* points= */ points);
                self._bm25.build(self.chunks.iter().map(|c| c["text".to_string()]).collect::<Vec<_>>());
                logger.info(format!("[RAG] Added {} chunks", points.len()));
            }
        }
    }
    pub fn search(&mut self, query: String, k: i64, rerank: bool) -> Vec<HashMap> {
        if !self.qdrant {
            if (self._bm25 && self._bm25.indexed) {
                self.hybrid_search(query, k, /* alpha= */ 0.0_f64, /* rerank= */ rerank)
            }
            vec![]
        }
        let mut cached = self._cache.get(&query).cloned();
        if cached.is_some() {
            for r in cached.iter() {
                r["_is_cached".to_string()] = true;
            }
            cached
        }
        let mut limit = if rerank { (k * 3) } else { k };
        let mut q_vec = self._embed_mgr.encode_single(query, /* normalize= */ true);
        let mut hits = self.qdrant.query_points(/* collection_name= */ self.collection_name, /* query= */ q_vec.tolist(), /* limit= */ limit).points;
        let mut results = hits.iter().map(|h| HashMap::from([("text".to_string(), h.payload.get(&"text".to_string()).cloned()), ("url".to_string(), h.payload.get(&"url".to_string()).cloned()), ("title".to_string(), h.payload.get(&"title".to_string()).cloned()), ("metadata".to_string(), h.payload.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new())), ("score".to_string(), h.score)])).collect::<Vec<_>>();
        if rerank {
            let mut results = self.rerank(query, results, /* top_k= */ k);
        }
        self._cache.set(query, results.iter().map(|r| r).collect::<Vec<_>>());
        results
    }
    pub fn hybrid_search(&mut self, query: String, k: i64, alpha: f64, rerank: bool) -> Vec<HashMap> {
        if !self.chunks {
            vec![]
        }
        let mut k_search = (k * 5).max(50);
        let mut dense_scores = HashMap::new();
        if self.qdrant {
            let mut q_vec = self._embed_mgr.encode_single(query, /* normalize= */ true);
            let mut hits = self.qdrant.query_points(/* collection_name= */ self.collection_name, /* query= */ q_vec.tolist(), /* limit= */ k_search).points;
            let mut id_to_idx = self.chunks.iter().enumerate().iter().map(|(i, c)| (c["qdrant_id".to_string()], i)).collect::<HashMap<_, _>>();
            for (rank, hit) in hits.iter().enumerate().iter() {
                if id_to_idx.contains(&hit.id) {
                    dense_scores[id_to_idx[&hit.id]] = (1.0_f64 / ((60 + rank) + 1));
                }
            }
        } else {
            let mut alpha = 0.0_f64;
        }
        let mut bm25_scores = HashMap::new();
        if (self._bm25 && self._bm25.indexed) {
            let mut raw = self._bm25.search(query, /* k= */ k_search);
            for (rank, (idx, _)) in { let mut v = raw.iter().clone(); v.sort(); v }.iter().enumerate().iter() {
                bm25_scores[idx] = (1.0_f64 / ((60 + rank) + 1));
            }
        }
        if (dense_scores && bm25_scores) {
            let mut fused = reciprocal_rank_fusion(dense_scores, bm25_scores, /* k= */ 60, /* weights= */ vec![alpha, (1.0_f64 - alpha)]);
        } else if dense_scores {
            let mut fused = dense_scores;
        } else if bm25_scores {
            let mut fused = bm25_scores;
        } else {
            vec![]
        }
        let mut k_candidates = if rerank { (k * 3) } else { k };
        let mut sorted_indices = { let mut v = fused.clone(); v.sort(); v }[..k_candidates];
        let mut results = sorted_indices.iter().map(|idx| self.chunks[&idx].clone()).collect::<Vec<_>>();
        for (i, res) in results.iter().enumerate().iter() {
            res["fusion_score".to_string()] = fused[sorted_indices[&i]];
        }
        if rerank {
            let mut results = self.rerank(query, results, /* top_k= */ k);
        }
        results
    }
    pub fn rerank(&mut self, query: String, chunks: Vec<HashMap>, top_k: i64) -> Result<Vec<HashMap>> {
        if !chunks {
            vec![]
        }
        // try:
        {
            if !self._reranker.is_loaded {
                self._reranker.load();
            }
            if !self._reranker.is_loaded {
                chunks[..top_k]
            }
            let mut texts = chunks.iter().map(|c| c["text".to_string()]).collect::<Vec<_>>();
            let mut reranked = self._reranker.rerank(query, texts, /* top_k= */ top_k);
            let mut results = vec![];
            for (orig_idx, score) in reranked.iter() {
                let mut chunk = chunks[&orig_idx].clone();
                chunk["rerank_score".to_string()] = score;
                results.push(chunk);
            }
            results
        }
        // except Exception as e:
    }
    pub fn save(&self, path: String) -> () {
        // pass
    }
    pub fn load(&self, path: String) -> bool {
        self._load_metadata();
        true
    }
    pub fn get_stats(&mut self) -> Result<HashMap> {
        let mut stats = HashMap::from([("total_chunks".to_string(), self.chunks.len()), ("collection".to_string(), self.collection_name), ("bm25_indexed".to_string(), self._bm25.indexed), ("embedding_model".to_string(), if self._embed_mgr.is_loaded { self._embed_mgr.model_type } else { "none".to_string() }), ("embedding_dim".to_string(), self.embedding_dim), ("reranker".to_string(), if self._reranker.is_loaded { self._reranker.model_name } else { "not loaded".to_string() }), ("cache_size".to_string(), if self._cache { self._cache.size } else { 0 }), ("read_only".to_string(), /* getattr */ false)]);
        if self.qdrant {
            // try:
            {
                let mut info = self.qdrant.get_collection(self.collection_name);
                stats["qdrant_points".to_string()] = info.points_count;
            }
            // except Exception as _e:
        }
        if self.db {
            // try:
            {
                stats["sqlite_chunks".to_string()] = self.db.count_chunks();
            }
            // except Exception as _e:
        }
        Ok(stats)
    }
    pub fn close(&mut self) -> Result<()> {
        // try:
        {
            if (/* hasattr(self, "qdrant".to_string()) */ true && self.qdrant.is_some()) {
                if /* hasattr(self.qdrant, "close".to_string()) */ true {
                    self.qdrant.close();
                }
                drop(self.qdrant);
                self.qdrant = None;
            }
        }
        // except Exception as _e:
        // try:
        {
            if self.db {
                self.db.close();
            }
        }
        // except Exception as _e:
    }
    pub fn __del__(&self) -> () {
        self.close();
    }
}

#[derive(Debug, Clone)]
pub struct AsyncLocalRAGv2 {
}

impl AsyncLocalRAGv2 {
    pub async fn search_async(&self, query: String, k: String) -> () {
        asyncio.to_thread(self.search, query, k).await
    }
    pub async fn hybrid_search_async(&self, query: String, k: String, alpha: String) -> () {
        asyncio.to_thread(self.hybrid_search, query, k, alpha).await
    }
    pub async fn rerank_async(&self, query: String, chunks: String, top_k: String) -> () {
        asyncio.to_thread(self.rerank, query, chunks, top_k).await
    }
    pub async fn build_index_async(&self, documents: String, dedup_threshold: String) -> () {
        asyncio.to_thread(self.build_index, documents, dedup_threshold).await
    }
    pub async fn add_chunks_async(&self, chunks: String, dedup_threshold: String) -> () {
        asyncio.to_thread(self.add_chunks, chunks, dedup_threshold).await
    }
}

pub fn _lazy_load_qdrant() -> () {
    // global/nonlocal QdrantClient, Distance, VectorParams, PointStruct
    if QdrantClient.is_some() {
        return;
    }
    // TODO: from qdrant_client import QdrantClient as _QC
    // TODO: from qdrant_client.models import Distance as _D, VectorParams as _VP, PointStruct as _PS
    let (mut QdrantClient, mut Distance, mut VectorParams, mut PointStruct) = (_QC, _D, _VP, _PS);
}

pub fn generate_rag_response(query: String, rag: LocalRAGv2, llm_backend: String, use_hybrid: bool, k: i64, alpha: f64) -> Generator</* unknown */> {
    if use_hybrid {
        let mut candidates = rag.hybrid_search(query, /* k= */ (k * 3), /* alpha= */ alpha);
    } else {
        let mut candidates = rag.search(query, /* k= */ (k * 3));
    }
    let mut context_chunks = rag.rerank(query, candidates, /* top_k= */ k);
    if !context_chunks {
        /* yield "I don't have enough information in my knowledge base.".to_string() */;
        return;
    }
    let mut MAX_CTX_CHARS = 12000;
    let mut context_text = "".to_string();
    for (i, c) in context_chunks.iter().enumerate().iter() {
        let mut chunk_text = format!("Source [{}]: {}\n\n", (i + 1), c["text".to_string()]);
        if (context_text.len() + chunk_text.len()) > MAX_CTX_CHARS {
            break;
        }
        context_text += chunk_text;
    }
    let mut prompt = format!("Context:\n{}\n\nQuestion: {}\n\nAnswer mentioning sources:", context_text, query);
    for chunk in llm_backend::send_message(prompt).iter() {
        /* yield chunk */;
    }
}
