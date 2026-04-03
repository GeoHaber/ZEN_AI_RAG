/// zena_mode/constants::py — Shared constants and utilities
/// ========================================================
/// 
/// Centralises stop words, sentence splitting, and token estimation
/// used across query_processor, contextual_compressor, and evaluation.

use anyhow::{Result, Context};
use std::collections::HashSet;

pub static STOP_WORDS: std::sync::LazyLock<frozenset<String>> = std::sync::LazyLock::new(|| Default::default());

pub static _SENTENCE_SPLIT_RE: std::sync::LazyLock<String /* re::compile */> = std::sync::LazyLock::new(|| Default::default());

pub static _WORD_RE: std::sync::LazyLock<String /* re::compile */> = std::sync::LazyLock::new(|| Default::default());

/// Split text into sentences, preserving ending punctuation.
pub fn split_sentences(text: String) -> Vec<String> {
    // Split text into sentences, preserving ending punctuation.
    let mut sentences = _SENTENCE_SPLIT_RE.split(text).map(|s| s.to_string()).collect::<Vec<String>>();
    sentences.iter().filter(|s| s.trim().to_string()).map(|s| s.trim().to_string()).collect::<Vec<_>>()
}

/// Extract key words from text, excluding stop words and short words.
/// 
/// Returns a *set* so callers can use set-intersection (``&``) directly.
pub fn extract_key_words(text: String, min_length: i64) -> HashSet<String> {
    // Extract key words from text, excluding stop words and short words.
    // 
    // Returns a *set* so callers can use set-intersection (``&``) directly.
    let mut words = _WORD_RE.findall(text.to_lowercase());
    words.iter().filter(|w| (!STOP_WORDS.contains(&w) && w.len() > min_length)).map(|w| w).collect::<HashSet<_>>()
}

/// Rough token count estimate (~4 chars per token).
pub fn estimate_tokens(text: String) -> i64 {
    // Rough token count estimate (~4 chars per token).
    1.max((text.len() / 4))
}
