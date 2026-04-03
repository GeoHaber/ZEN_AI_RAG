/// chunker::py - Unified text chunking for ZenAI RAG.
/// Consolidates logic from rag_pipeline::py and universal_extractor::py.

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Chunk {
    pub text: String,
    pub metadata: HashMap<String, serde_json::Value>,
    pub chunk_index: i64,
    pub hash: String,
}

impl Chunk {
    pub fn __post_init__(&mut self) -> () {
        if !self.hash {
            self.hash = hashlib::sha256(self.text.as_bytes().to_vec()).hexdigest();
        }
    }
}

/// Default configuration for chunking.
#[derive(Debug, Clone)]
pub struct ChunkerConfig {
    pub CHUNK_SIZE: i64,
    pub CHUNK_OVERLAP: i64,
    pub MIN_CHUNK_LENGTH: i64,
    pub MIN_ENTROPY: f64,
    pub MAX_ENTROPY: f64,
    pub BLACKLIST_KEYWORDS: HashSet<String>,
}

/// Unified text chunker with multiple strategies.
#[derive(Debug, Clone)]
pub struct TextChunker {
    pub config: String,
}

impl TextChunker {
    pub fn new(config: ChunkerConfig) -> Self {
        Self {
            config: (config || ChunkerConfig()),
        }
    }
    /// Calculate Shannon entropy of text.
    pub fn _calculate_entropy(&self, text: String) -> f64 {
        // Calculate Shannon entropy of text.
        if !text {
            0.0_f64
        }
        let mut counts = Counter(text);
        let mut probs = counts.values().iter().map(|c| (c / text.len())).collect::<Vec<_>>();
        -probs.iter().map(|p| (p * log2(p))).collect::<Vec<_>>().iter().sum::<i64>()
    }
    /// Detect junk chunks based on length, entropy, and keywords.
    pub fn is_junk(&mut self, text: String) -> bool {
        // Detect junk chunks based on length, entropy, and keywords.
        let mut text = text.trim().to_string();
        if text.len() < self.config::MIN_CHUNK_LENGTH {
            true
        }
        let mut words = text.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>();
        if words.len() < 5 {
            true
        }
        let mut entropy = self._calculate_entropy(text);
        if (entropy < self.config::MIN_ENTROPY || entropy > self.config::MAX_ENTROPY) {
            true
        }
        let mut text_lower = text.to_lowercase();
        if self.config::BLACKLIST_KEYWORDS.iter().map(|kw| text_lower.contains(&kw)).collect::<Vec<_>>().iter().any(|v| *v) {
            true
        }
        false
    }
    /// Split text into chunks using semantic recursion.
    pub fn recursive_split(&mut self, text: String, max_size: i64, overlap_size: i64) -> Vec<String> {
        // Split text into chunks using semantic recursion.
        if text.len() <= max_size {
            vec![text]
        }
        let mut separators = vec!["\n\n".to_string(), "\n".to_string(), ". ".to_string(), "! ".to_string(), "? ".to_string(), "; ".to_string(), ", ".to_string(), " ".to_string()];
        let mut split_at = -1;
        for sep in separators.iter() {
            let mut pos = text.rfind(sep, 0, max_size);
            if pos != -1 {
                let mut split_at = (pos + sep.len());
                break;
            }
        }
        if split_at == -1 {
            let mut split_at = max_size;
        }
        let mut chunk = text[..split_at];
        let mut remaining = if split_at > overlap_size { text[(split_at - overlap_size)..] } else { text[split_at..] };
        (vec![chunk] + self.recursive_split(remaining, max_size, overlap_size))
    }
    /// true semantic chunking using embedding similarity.
    /// 
    /// Args:
    /// text: Content to chunk
    /// model: SentenceTransformer model instance (must have .encode method)
    /// threshold: Cosine similarity threshold to break chunks
    pub fn semantic_split(&mut self, text: String, model: String, threshold: f64) -> Result<Vec<Chunk>> {
        // true semantic chunking using embedding similarity.
        // 
        // Args:
        // text: Content to chunk
        // model: SentenceTransformer model instance (must have .encode method)
        // threshold: Cosine similarity threshold to break chunks
        // TODO: import numpy as np
        let mut sentences = re::split(self.SENTENCE_ENDINGS, text);
        let mut sentences = sentences.iter().filter(|s| s.trim().to_string()).map(|s| s.trim().to_string()).collect::<Vec<_>>();
        if sentences.len() < 2 {
            vec![Chunk(/* text= */ text, /* chunk_index= */ 0)]
        }
        // try:
        {
            let mut embeddings = model.encode(sentences, /* normalize_embeddings= */ true);
        }
        // except Exception as _e:
        let mut chunks = vec![];
        let mut current_chunk = vec![sentences[0]];
        let mut current_len = sentences[0].len();
        let mut idx = 0;
        for i in 0..(embeddings::len() - 1).iter() {
            let mut sent = sentences[(i + 1)];
            let mut sent_len = sent.len();
            let mut score = np.dot(embeddings[&i], embeddings[(i + 1)]);
            let mut condition_topic_shift = score < threshold;
            let mut condition_max_size = (current_len + sent_len) > (self.config::CHUNK_SIZE * 2);
            if ((condition_topic_shift || condition_max_size) && current_len >= self.config::MIN_CHUNK_LENGTH) {
                let mut chunk_text = current_chunk.join(&" ".to_string());
                if !self.is_junk(chunk_text) {
                    chunks.push(Chunk(/* text= */ chunk_text, /* chunk_index= */ idx));
                    idx += 1;
                }
                let mut current_chunk = vec![sent];
                let mut current_len = sent_len;
            } else {
                current_chunk.push(sent);
                current_len += sent_len;
            }
        }
        if current_chunk {
            let mut chunk_text = current_chunk.join(&" ".to_string());
            if !self.is_junk(chunk_text) {
                chunks.push(Chunk(/* text= */ chunk_text, /* chunk_index= */ idx));
            }
        }
        Ok(chunks)
    }
    /// Divide a document into chunks.
    /// 
    /// Args:
    /// content: The text to chunk.
    /// metadata: Base metadata for all chunks.
    /// strategy: "recursive" or "semantic" (requires model).
    /// filter_junk: Whether to filter out junk chunks.
    /// model: Embedding model for semantic strategy.
    pub fn chunk_document(&mut self, content: String, metadata: HashMap<String, serde_json::Value>, strategy: String, filter_junk: bool, model: String) -> Vec<Chunk> {
        // Divide a document into chunks.
        // 
        // Args:
        // content: The text to chunk.
        // metadata: Base metadata for all chunks.
        // strategy: "recursive" or "semantic" (requires model).
        // filter_junk: Whether to filter out junk chunks.
        // model: Embedding model for semantic strategy.
        if !content {
            vec![]
        }
        let mut metadata = (metadata || HashMap::new());
        if (strategy == "semantic".to_string() && model) {
            let mut chunks = self.semantic_split(content, model);
            for c in chunks.iter() {
                c.metadata = metadata.clone();
            }
            chunks
        }
        self._recursive_chunk_wrapper(content, metadata, filter_junk)
    }
    /// Helper for standard recursive logic.
    pub fn _recursive_chunk_wrapper(&mut self, content: String, metadata: HashMap<String, serde_json::Value>, filter_junk: bool) -> Vec<Chunk> {
        // Helper for standard recursive logic.
        let mut chunks = vec![];
        let mut texts = self.recursive_split(content, self.config::CHUNK_SIZE, self.config::CHUNK_OVERLAP);
        for (i, text) in texts.iter().enumerate().iter() {
            let mut text = text.trim().to_string();
            if (!filter_junk || !self.is_junk(text)) {
                chunks.push(Chunk(/* text= */ text, /* metadata= */ metadata.clone(), /* chunk_index= */ i));
            }
        }
        chunks
    }
}

/// A chunk that knows its parent context.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HierarchicalChunk {
    pub text: String,
    pub parent_text: String,
    pub parent_id: String,
    pub chunk_id: String,
    pub chunk_index: i64,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl HierarchicalChunk {
    pub fn __post_init__(&mut self) -> () {
        if !self.parent_id {
            self.parent_id = hashlib::sha256(self.parent_text.as_bytes().to_vec()).hexdigest();
        }
        if !self.chunk_id {
            self.chunk_id = hashlib::sha256(self.text.as_bytes().to_vec()).hexdigest();
        }
    }
}

/// Parent-Child hierarchical chunking strategy.
/// 
/// Produces two levels:
/// - Parent chunks (~2000 chars): wide context window, stored as payload in Qdrant.
/// - Child chunks (~400 chars):  what gets embedded + retrieved for precision.
/// 
/// At search time, child embeddings are matched but the PARENT text is fed to the LLM,
/// providing much richer context while maintaining retrieval precision.
/// 
/// This mirrors WeKnora v0.3.3 and the RAPTOR / SiReRAG approach from ICLR '26.
/// 
/// Usage:
/// hc = HierarchicalChunker(parent_size=2000, child_size=400, overlap=50)
/// chunks = hc.chunk_document(text, metadata={"url": "...", "title": "..."})
/// # chunks[i].text → embed this
/// # chunks[i].parent_text → feed to LLM
#[derive(Debug, Clone)]
pub struct HierarchicalChunker {
    pub parent_size: String,
    pub child_size: String,
    pub child_overlap: String,
    pub min_child_length: String,
    pub _base_chunker: TextChunker,
}

impl HierarchicalChunker {
    pub fn new(parent_size: i64, child_size: i64, child_overlap: i64, min_child_length: i64) -> Self {
        Self {
            parent_size,
            child_size,
            child_overlap,
            min_child_length,
            _base_chunker: TextChunker(),
        }
    }
    /// Recursive split helper.
    pub fn _split(&self, text: String, max_size: i64, overlap: i64) -> Vec<String> {
        // Recursive split helper.
        self._base_chunker.recursive_split(text, max_size, overlap)
    }
    /// Split document into hierarchical parent-child chunks.
    /// 
    /// Args:
    /// content: Full document text.
    /// metadata: Shared metadata attached to all chunks.
    /// filter_junk: Skip low-quality child chunks.
    /// 
    /// Returns:
    /// List of HierarchicalChunk objects.
    pub fn chunk_document(&mut self, content: String, metadata: HashMap<String, serde_json::Value>, filter_junk: bool) -> Vec<HierarchicalChunk> {
        // Split document into hierarchical parent-child chunks.
        // 
        // Args:
        // content: Full document text.
        // metadata: Shared metadata attached to all chunks.
        // filter_junk: Skip low-quality child chunks.
        // 
        // Returns:
        // List of HierarchicalChunk objects.
        if (!content || !content.trim().to_string()) {
            vec![]
        }
        let mut metadata = (metadata || HashMap::new());
        let mut parent_texts = self._split(content, self.parent_size, /* overlap= */ 200);
        let mut chunks = vec![];
        let mut child_global_idx = 0;
        for parent_text in parent_texts.iter() {
            let mut parent_text = parent_text.trim().to_string();
            if !parent_text {
                continue;
            }
            let mut parent_id = hashlib::sha256(parent_text.as_bytes().to_vec()).hexdigest();
            let mut child_texts = self._split(parent_text, self.child_size, self.child_overlap);
            for child_text in child_texts.iter() {
                let mut child_text = child_text.trim().to_string();
                if child_text.len() < self.min_child_length {
                    continue;
                }
                if (filter_junk && self._base_chunker.is_junk(child_text)) {
                    continue;
                }
                let mut chunk = HierarchicalChunk(/* text= */ child_text, /* parent_text= */ parent_text, /* parent_id= */ parent_id, /* chunk_id= */ hashlib::sha256(child_text.as_bytes().to_vec()).hexdigest(), /* chunk_index= */ child_global_idx, /* metadata= */ metadata.clone());
                chunks.push(chunk);
                child_global_idx += 1;
            }
        }
        chunks
    }
    /// Convert HierarchicalChunks to flat dicts compatible with LocalRAG.build_index().
    /// 
    /// The 'text' field is the child (embedded, retrieved).
    /// The 'parent_text' field is stored in Qdrant payload for LLM context injection.
    pub fn to_flat_chunks(&self, hierarchical_chunks: Vec<HierarchicalChunk>) -> Vec<HashMap> {
        // Convert HierarchicalChunks to flat dicts compatible with LocalRAG.build_index().
        // 
        // The 'text' field is the child (embedded, retrieved).
        // The 'parent_text' field is stored in Qdrant payload for LLM context injection.
        let mut result = vec![];
        for hc in hierarchical_chunks.iter() {
            let mut flat = HashMap::from([("text".to_string(), hc.text), ("parent_text".to_string(), hc.parent_text), ("parent_id".to_string(), hc.parent_id), ("chunk_index".to_string(), hc.chunk_index)]);
            flat.extend(hc.metadata);
            result.push(flat);
        }
        result
    }
}
