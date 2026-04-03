/// Core/contextual_retrieval::py — Anthropic-Style Contextual Retrieval.
/// 
/// Industry best practice: Before embedding, each chunk receives a short
/// contextual preamble that situates it within its parent document.
/// This dramatically improves retrieval recall (up to 49% reduction in
/// failed retrievals per Anthropic's research).
/// 
/// Pipeline:
/// 1. For each chunk, generate a 1-2 sentence context using the full document
/// 2. Prepend context to chunk text before embedding
/// 3. Store both raw chunk and contextualized version
/// 
/// References:
/// - Anthropic "Contextual Retrieval" (2024)
/// - Microsoft "Lost in the Middle" findings

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// A chunk enriched with document-level context.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextualizedChunk {
    pub original_text: String,
    pub context_prefix: String,
    pub contextualized_text: String,
    pub metadata: HashMap<String, Box<dyn std::any::Any>>,
    pub chunk_index: i64,
    pub document_title: String,
    pub context_hash: String,
}

impl ContextualizedChunk {
    pub fn __post_init__(&mut self) -> () {
        if !self.context_hash {
            self.context_hash = hashlib::sha256(self.contextualized_text.as_bytes().to_vec()).hexdigest()[..16];
        }
    }
}

/// Enrich chunks with document-level context before embedding.
/// 
/// This implements Anthropic's Contextual Retrieval pattern:
/// each chunk gets a short preamble explaining where it sits
/// within the overall document, dramatically improving retrieval
/// for ambiguous or context-dependent passages.
/// 
/// Usage:
/// cr = ContextualRetrieval(llm_fn=my_generate)
/// enriched = cr.contextualize_chunks(chunks, document_text)
#[derive(Debug, Clone)]
pub struct ContextualRetrieval {
    pub llm_fn: String,
    pub max_document_chars: String,
    pub _cache: HashMap<String, String>,
}

impl ContextualRetrieval {
    /// Args:
    /// llm_fn: function(prompt) -> str for context generation
    /// max_document_chars: max chars of document to include in prompt
    /// enable_caching: cache generated contexts by chunk hash
    pub fn new(llm_fn: Option<Box<dyn Fn>>, max_document_chars: i64, enable_caching: bool) -> Self {
        Self {
            llm_fn,
            max_document_chars,
            _cache: HashMap::new(),
        }
    }
    /// Add document-level context to each chunk.
    /// 
    /// If LLM is unavailable, falls back to a heuristic preamble
    /// using the document title and chunk position.
    pub fn contextualize_chunks(&mut self, chunks: Vec<HashMap<String, Box<dyn std::any::Any>>>, document_text: String, document_title: String) -> Vec<ContextualizedChunk> {
        // Add document-level context to each chunk.
        // 
        // If LLM is unavailable, falls back to a heuristic preamble
        // using the document title and chunk position.
        if !chunks {
            vec![]
        }
        let mut doc_truncated = document_text[..self.max_document_chars];
        let mut total = chunks.len();
        let mut results = vec![];
        for (i, chunk) in chunks.iter().enumerate().iter() {
            let mut text = chunk.get(&"text".to_string()).cloned().unwrap_or("".to_string());
            if !text.trim().to_string() {
                continue;
            }
            let mut cache_key = hashlib::sha256(format!("{}:{}", document_title, text[..200]).as_bytes().to_vec()).hexdigest()[..16];
            if (self._cache.is_some() && self._cache.contains(&cache_key)) {
                let mut context_prefix = self._cache[&cache_key];
            } else if self.llm_fn {
                let mut context_prefix = self._generate_context(doc_truncated, text, document_title, i, total);
                if self._cache.is_some() {
                    self._cache[cache_key] = context_prefix;
                }
            } else {
                let mut context_prefix = self._heuristic_context(document_title, text, i, total);
            }
            let mut contextualized = if context_prefix { format!("{}\n\n{}", context_prefix, text) } else { text };
            results.push(ContextualizedChunk(/* original_text= */ text, /* context_prefix= */ context_prefix, /* contextualized_text= */ contextualized, /* metadata= */ chunk.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new()), /* chunk_index= */ i, /* document_title= */ document_title));
        }
        logger.info(format!("[ContextualRetrieval] Enriched {}/{} chunks from '{}'", results.len(), chunks.len(), document_title[..50]));
        results
    }
    /// Generate context prefix for a single chunk. Returns enriched text.
    pub fn contextualize_single(&mut self, chunk_text: String, document_text: String, document_title: String, chunk_index: i64, total_chunks: i64) -> String {
        // Generate context prefix for a single chunk. Returns enriched text.
        if self.llm_fn {
            let mut prefix = self._generate_context(document_text[..self.max_document_chars], chunk_text, document_title, chunk_index, total_chunks);
        } else {
            let mut prefix = self._heuristic_context(document_title, chunk_text, chunk_index, total_chunks);
        }
        if prefix { format!("{}\n\n{}", prefix, chunk_text) } else { chunk_text }
    }
    /// Use LLM to generate a situating context for the chunk.
    pub fn _generate_context(&mut self, document_text: String, chunk_text: String, title: String, index: i64, total: i64) -> Result<String> {
        // Use LLM to generate a situating context for the chunk.
        // try:
        {
            if document_text.len() > 2000 {
                let mut prompt = format!(self._BATCH_PROMPT, /* title= */ (title || "Untitled".to_string()), /* summary= */ document_text[..2000], /* index= */ (index + 1), /* total= */ total, /* chunk= */ chunk_text[..1000]);
            } else {
                let mut prompt = format!(self._CONTEXT_PROMPT, /* document= */ document_text, /* chunk= */ chunk_text[..1000]);
            }
            let mut result = self.llm_fn(prompt);
            if (result && result.trim().to_string().len() > 10) {
                result.trim().to_string()[..300]
            }
        }
        // except Exception as e:
        Ok(self._heuristic_context(title, chunk_text, index, total))
    }
    /// Generate a simple positional context without LLM.
    pub fn _heuristic_context(title: String, chunk_text: String, index: i64, total: i64) -> String {
        // Generate a simple positional context without LLM.
        let mut parts = vec![];
        if title {
            parts.push(format!("From document: {}.", title));
        }
        if total > 1 {
            let mut position = if index < (total * 0.25_f64) { "beginning".to_string() } else { if index > (total * 0.75_f64) { "end".to_string() } else { "middle".to_string() } };
            parts.push(format!("This is from the {} of the document (section {}/{}).", position, (index + 1), total));
        }
        parts.join(&" ".to_string())
    }
}
