/// Unified Exception Hierarchy for ZEN_AI_RAG.
/// 
/// All exceptions are defined here.  No silent failures — always raise with
/// clear messages.  Callers (UI layer, API handlers) decide how to present
/// each exception type.
/// 
/// Hierarchy::
/// 
/// ZenAIError (base)
/// ├── ConfigurationError   (config / setup issues)
/// ├── ProviderError        (provider connection / availability)
/// ├── AuthenticationError  (API keys, credentials)
/// ├── LLMError             (LLM provider failures)
/// ├── RAGError             (RAG pipeline failures)
/// ├── DocumentError        (document processing)
/// └── ValidationError      (invalid user input)
/// 
/// Adapted from RAG_RAT/Core/exceptions::py.

use anyhow::{Result, Context};
use std::collections::HashMap;

/// Base exception for all ZEN_AI_RAG errors.
#[derive(Debug, Clone)]
pub struct ZenAIError {
    pub message: String,
    pub error_code: String,
    pub details: HashMap<String, Box<dyn std::any::Any>>,
}

impl ZenAIError {
    pub fn new(message: String, error_code: String, details: Option<HashMap<String, Box<dyn std::any::Any>>>) -> Self {
        Self {
            message,
            error_code,
            details,
        }
    }
    pub fn __str__(&self) -> String {
        if self.details {
            format!("{} ({}): {}", self.message, self.error_code, self.details)
        }
        format!("{} ({})", self.message, self.error_code)
    }
}

/// Configuration is invalid or incomplete.
#[derive(Debug, Clone)]
pub struct ConfigurationError {
}

impl ConfigurationError {
    pub fn new(message: String, missing_config: Option<String>) -> Self {
        Self {
        }
    }
}

/// LLM provider is unavailable or not configured.
#[derive(Debug, Clone)]
pub struct ProviderError {
}

impl ProviderError {
    pub fn new(message: String, provider: Option<String>) -> Self {
        Self {
        }
    }
}

/// Authentication failed (API key, credentials).
#[derive(Debug, Clone)]
pub struct AuthenticationError {
}

impl AuthenticationError {
    pub fn new(message: String, provider: Option<String>) -> Self {
        Self {
        }
    }
}

/// LLM call failed (API error, timeout, rate limit, etc.).
#[derive(Debug, Clone)]
pub struct LLMError {
}

impl LLMError {
    pub fn new(message: String, provider: Option<String>, status_code: Option<i64>) -> Self {
        Self {
        }
    }
}

/// RAG pipeline failed (retrieval, augmentation, generation).
#[derive(Debug, Clone)]
pub struct RAGError {
}

impl RAGError {
    pub fn new(message: String, stage: Option<String>) -> Self {
        Self {
        }
    }
}

/// Document processing failed.
#[derive(Debug, Clone)]
pub struct DocumentError {
}

impl DocumentError {
    pub fn new(message: String, file_path: Option<String>, format: Option<String>) -> Self {
        Self {
        }
    }
}

/// Input validation failed.
#[derive(Debug, Clone)]
pub struct ValidationError {
}

impl ValidationError {
    pub fn new(message: String, field: Option<String>) -> Self {
        Self {
        }
    }
}
