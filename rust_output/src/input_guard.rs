/// Core/input_guard::py — Input validation for RAG queries.
/// 
/// Ported from main-app (George branch) E-12 input length guard.
/// Validates query length, detects basic prompt-injection patterns,
/// and ensures Unicode safety for Romanian/multilingual text.

use anyhow::{Result, Context};
use regex::Regex;
use serde::{Serialize, Deserialize};

pub const MAX_QUERY_LENGTH: i64 = 8000;

pub static _INJECTION_PATTERNS: std::sync::LazyLock<Vec<re::compile>> = std::sync::LazyLock::new(|| Vec::new());

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResult {
    pub valid: bool,
    pub reason: Option<String>,
    pub sanitised_text: Option<String>,
}

/// Validate a user query before it enters the RAG pipeline.
/// 
/// Returns ValidationResult with .valid=true and .sanitised_text set on success,
/// or .valid=false with .reason explaining the rejection.
pub fn validate_query(text: String, max_length: i64, check_injection: bool) -> ValidationResult {
    // Validate a user query before it enters the RAG pipeline.
    // 
    // Returns ValidationResult with .valid=true and .sanitised_text set on success,
    // or .valid=false with .reason explaining the rejection.
    if !/* /* isinstance(text, str) */ */ true {
        ValidationResult(/* valid= */ false, /* reason= */ "Query must be a string".to_string())
    }
    if !text.trim().to_string() {
        ValidationResult(/* valid= */ false, /* reason= */ "Query is empty".to_string())
    }
    if text.len() > max_length {
        ValidationResult(/* valid= */ false, /* reason= */ format!("Query exceeds {} characters ({} given)", max_length, text.len()))
    }
    if check_injection {
        for pattern in _INJECTION_PATTERNS.iter() {
            if pattern.search(text) {
                ValidationResult(/* valid= */ false, /* reason= */ "Query matches a prompt-injection pattern".to_string())
            }
        }
    }
    let mut sanitised = regex::Regex::new(&"\\s+".to_string()).unwrap().replace_all(&" ".to_string(), text).to_string().trim().to_string();
    ValidationResult(/* valid= */ true, /* sanitised_text= */ sanitised)
}
