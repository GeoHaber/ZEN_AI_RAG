/// zena_mode/contextual_compressor::py — Smart Context Compression
/// ===============================================================
/// 
/// Adapted from RAG_RAT Core/contextual_compressor::py for ZEN_AI_RAG.
/// 
/// Compresses retrieved chunks so only the most query-relevant sentences
/// are forwarded to the LLM, reducing token usage while preserving accuracy.
/// 
/// Strategy: keyword-overlap sentence scoring with order-preserving selection.

use anyhow::{Result, Context};
use crate::constants::{extract_key_words, split_sentences, estimate_token};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _INSTANCE: std::sync::LazyLock<Option<ContextualCompressor>> = std::sync::LazyLock::new(|| None);

/// Track compression performance metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompressionStats {
    pub total_chars_in: i64,
    pub total_chars_out: i64,
    pub total_chunks_in: i64,
    pub total_chunks_out: i64,
    pub calls: i64,
}

impl CompressionStats {
    /// Return the compression ratio (output / input characters).
    pub fn ratio(&self) -> f64 {
        // Return the compression ratio (output / input characters).
        if self.total_chars_in { (self.total_chars_out / self.total_chars_in) } else { 1.0_f64 }
    }
}

/// One compressed chunk with metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompressedChunk {
    pub text: String,
    pub score: f64,
    pub source: String,
    pub original_index: i64,
    pub metadata: HashMap<String, Box<dyn std::any::Any>>,
}

/// Compresses RAG context to only the most relevant sentences.
#[derive(Debug, Clone)]
pub struct ContextualCompressor {
    pub max_tokens: String,
    pub min_score: String,
    pub keep_top_k: String,
    pub stats: CompressionStats,
}

impl ContextualCompressor {
    /// Initialize the compressor with token budget and relevance thresholds.
    pub fn new() -> Self {
        Self {
            max_tokens: max_tokens,
            min_score: min_score,
            keep_top_k: keep_top_k,
            stats: CompressionStats(),
        }
    }
    /// Compress a list of chunks to the most query-relevant sentences.
    /// 
    /// Parameters
    /// ----------
    /// query : str
    /// The user query.
    /// chunks : list[dict]
    /// Each dict should have at least ``"text"`` (str).
    /// Optional keys: ``"source"`` (str), ``"metadata"`` (dict).
    /// 
    /// Returns
    /// -------
    /// list[CompressedChunk]
    /// Order-preserved, token-limited selection of relevant sentences.
    pub fn compress_chunks(&mut self, query: String, chunks: Vec<HashMap<String, Box<dyn std::any::Any>>>) -> Vec<CompressedChunk> {
        // Compress a list of chunks to the most query-relevant sentences.
        // 
        // Parameters
        // ----------
        // query : str
        // The user query.
        // chunks : list[dict]
        // Each dict should have at least ``"text"`` (str).
        // Optional keys: ``"source"`` (str), ``"metadata"`` (dict).
        // 
        // Returns
        // -------
        // list[CompressedChunk]
        // Order-preserved, token-limited selection of relevant sentences.
        if (!chunks || !query.trim().to_string()) {
            vec![]
        }
        self.stats.calls += 1;
        self.stats.total_chunks_in += chunks.len();
        let mut keywords = extract_key_words(query);
        if !keywords {
            self._truncate_fallback(chunks)
        }
        self._compress_chunks_part2(keywords)
    }
    /// Continue compress_chunks logic.
    pub fn _compress_chunks_part2(&mut self, keywords: String) -> () {
        // Continue compress_chunks logic.
        let mut scored = vec![];
        for (idx, chunk) in chunks.iter().enumerate().iter() {
            let mut text = chunk.get(&"text".to_string()).cloned().unwrap_or("".to_string());
            let mut source = chunk.get(&"source".to_string()).cloned().unwrap_or("".to_string());
            let mut meta = chunk.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new());
            self.stats.total_chars_in += text.len();
            for sentence in split_sentences(text).iter() {
                let mut s_lower = sentence.to_lowercase();
                let mut s_words = s_lower.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().into_iter().collect::<HashSet<_>>();
                let mut overlap = (keywords & s_words).len();
                if !overlap {
                    continue;
                }
                let mut score = (overlap / keywords.len().max(1));
                scored.push(HashMap::from([("sentence".to_string(), sentence), ("score".to_string(), score), ("source".to_string(), source), ("chunk_idx".to_string(), idx), ("metadata".to_string(), meta)]));
            }
        }
        if !scored {
            self._truncate_fallback(chunks)
        }
        scored.sort(/* key= */ |x| (-x["score".to_string()], x["chunk_idx".to_string()]));
        let mut scored = scored.iter().filter(|s| s["score".to_string()] >= self.min_score).map(|s| s).collect::<Vec<_>>();
        self._compress_chunks_part2(scored)
    }
    /// Continue compress_chunks logic.
    pub fn _compress_chunks_part2(&mut self, scored: String) -> () {
        // Continue compress_chunks logic.
        let mut selected = vec![];
        let mut token_budget = self.max_tokens;
        for item in scored[..self.keep_top_k].iter() {
            let mut est = estimate_tokens(item["sentence".to_string()]);
            if est > token_budget {
                break;
            }
            selected.push(item);
            token_budget -= est;
        }
        if !selected {
            self._truncate_fallback(chunks)
        }
        selected.sort(/* key= */ |x| x["chunk_idx".to_string()]);
        let mut results = vec![];
        for item in selected.iter() {
            let mut cc = CompressedChunk(/* text= */ item["sentence".to_string()], /* score= */ item["score".to_string()], /* source= */ item["source".to_string()], /* original_index= */ item["chunk_idx".to_string()], /* metadata= */ item["metadata".to_string()]);
            results.push(cc);
            self.stats.total_chars_out += cc.text.len();
        }
        self.stats.total_chunks_out += results.len();
        let mut ratio_pct = format!("{:.0%}", self.stats.ratio);
        logger.info("Compressed %d chunks → %d sentences (ratio %s, budget remaining %d tokens)".to_string(), chunks.len(), results.len(), ratio_pct, token_budget);
        results
    }
    /// Fallback: return chunks truncated to token budget.
    pub fn _truncate_fallback(&mut self, chunks: Vec<HashMap<String, Box<dyn std::any::Any>>>) -> Vec<CompressedChunk> {
        // Fallback: return chunks truncated to token budget.
        let mut results = vec![];
        let mut budget = self.max_tokens;
        for (idx, chunk) in chunks.iter().enumerate().iter() {
            let mut text = chunk.get(&"text".to_string()).cloned().unwrap_or("".to_string());
            let mut est = estimate_tokens(text);
            if est > budget {
                let mut char_limit = (budget * 4);
                let mut text = text[..char_limit];
                let mut est = estimate_tokens(text);
            }
            results.push(CompressedChunk(/* text= */ text, /* score= */ 0.0_f64, /* source= */ chunk.get(&"source".to_string()).cloned().unwrap_or("".to_string()), /* original_index= */ idx));
            budget -= est;
            if budget <= 0 {
                break;
            }
        }
        results
    }
}

/// Return the global :class:`ContextualCompressor` singleton.
pub fn get_compressor() -> ContextualCompressor {
    // Return the global :class:`ContextualCompressor` singleton.
    // global/nonlocal _instance
    if _instance.is_none() {
        let mut _instance = ContextualCompressor(/* max_tokens= */ max_tokens);
    }
    _instance
}
