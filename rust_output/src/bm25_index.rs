/// rag_core.bm25_index — BM25 Keyword Search Index
/// ==================================================
/// 
/// Wraps rank_bm25 with code-aware tokenisation and graceful fallback.

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _TOKEN_RE: std::sync::LazyLock<String /* re::compile */> = std::sync::LazyLock::new(|| Default::default());

/// BM25 keyword search with graceful fallback.
/// 
/// Uses ``rank_bm25.BM25Okapi`` when available, otherwise falls back
/// to simple token overlap scoring.
#[derive(Debug, Clone)]
pub struct BM25Index {
    pub code_aware: String,
    pub _bm25: Option<serde_json::Value>,
    pub _corpus_tokens: Vec<Vec<String>>,
    pub _has_rank_bm25: bool,
}

impl BM25Index {
    pub fn new(code_aware: bool) -> Self {
        Self {
            code_aware,
            _bm25: None,
            _corpus_tokens: Vec::new(),
            _has_rank_bm25: false,
        }
    }
    pub fn indexed(&self) -> bool {
        self._corpus_tokens.len() > 0
    }
    pub fn doc_count(&self) -> i64 {
        self._corpus_tokens.len()
    }
    /// Build the BM25 index from a list of document texts.
    /// 
    /// Returns the number of documents indexed.
    pub fn build(&mut self, documents: Vec<String>) -> Result<i64> {
        // Build the BM25 index from a list of document texts.
        // 
        // Returns the number of documents indexed.
        self._corpus_tokens = documents.iter().map(|doc| tokenize(doc, /* code_aware= */ self.code_aware)).collect::<Vec<_>>();
        let mut corpus_has_tokens = self._corpus_tokens.iter().map(|t| t.len() > 0).collect::<Vec<_>>().iter().any(|v| *v);
        if (!self._corpus_tokens || !corpus_has_tokens) {
            self._bm25 = None;
            self._has_rank_bm25 = false;
            self._corpus_tokens.len()
        }
        // try:
        {
            // TODO: from rank_bm25 import BM25Okapi
            self._bm25 = BM25Okapi(self._corpus_tokens);
            self._has_rank_bm25 = true;
        }
        // except ImportError as _e:
        Ok(self._corpus_tokens.len())
    }
    /// Search the index and return {doc_index: score} dict.
    /// 
    /// Scores are raw BM25 scores (not normalised to 0-1).
    pub fn search(&mut self, query: String, k: i64) -> HashMap<i64, f64> {
        // Search the index and return {doc_index: score} dict.
        // 
        // Scores are raw BM25 scores (not normalised to 0-1).
        if !self._corpus_tokens {
            HashMap::new()
        }
        let mut q_tokens = tokenize(query, /* code_aware= */ self.code_aware);
        if (self._has_rank_bm25 && self._bm25.is_some()) {
            let mut raw = self._bm25.get_scores(q_tokens);
            let mut scored = raw.iter().enumerate().iter().filter(|(i, s)| s > 0).map(|(i, s)| (i, s.to_string().parse::<f64>().unwrap_or(0.0))).collect::<Vec<_>>();
            scored.sort(/* key= */ |x| x[1], /* reverse= */ true);
            scored[..k].iter().map(|(i, s)| (i, s)).collect::<HashMap<_, _>>()
        }
        let mut q_set = q_tokens.into_iter().collect::<HashSet<_>>();
        let mut scores = HashMap::new();
        for (i, doc_tokens) in self._corpus_tokens.iter().enumerate().iter() {
            let mut overlap = (q_set & doc_tokens.into_iter().collect::<HashSet<_>>()).len();
            if overlap > 0 {
                scores[i] = (overlap / q_set.len().max(1));
            }
        }
        let mut sorted_scores = { let mut v = scores.iter().clone(); v.sort(); v };
        /* dict(sorted_scores[..k]) */ HashMap::new()
    }
}

/// Tokenise text for BM25.
/// 
/// When *code_aware* is true, splits camelCase and snake_case into sub-tokens
/// so ``parseJsonConfig`` produces ``[parse, json, config, parsejsonconfig]``.
pub fn tokenize(text: String) -> Vec<String> {
    // Tokenise text for BM25.
    // 
    // When *code_aware* is true, splits camelCase and snake_case into sub-tokens
    // so ``parseJsonConfig`` produces ``[parse, json, config, parsejsonconfig]``.
    let mut tokens = vec![];
    for word in _TOKEN_RE.findall(text).iter() {
        let mut lower_word = word.to_lowercase();
        if code_aware {
            let mut parts = re::findall("[a-z]+|[A-Z][a-z]*|[A-Z]+(?=[A-Z]|$)".to_string(), word).iter().map(|p| p.to_lowercase()).collect::<Vec<_>>();
            tokens.extend(parts);
        }
        tokens.push(lower_word);
    }
    tokens.iter().filter(|t| t.len() > 1).map(|t| t).collect::<Vec<_>>()
}
