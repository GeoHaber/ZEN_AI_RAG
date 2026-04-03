/// Configuration System - Backwards Compatibility Layer
/// =====================================================
/// Unifies access to config_enhanced::py for all modules.
/// 
/// IMPORTANT: config_enhanced::py is now the SINGLE SOURCE OF TRUTH.
/// This module provides compatibility for modules using config_system::py imports.
/// 
/// Usage:
/// from config_system import config, EMOJI
/// config::MODEL_DIR        # Maps to Config.MODELS_DIR
/// config::mgmt_port        # Backend port
/// EMOJI['success']        # For status messages

use anyhow::{Result, Context};
use crate::config_enhanced::{Config};

pub static EMOJI: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub static CONFIG: std::sync::LazyLock<ConfigAdapter> = std::sync::LazyLock::new(|| Default::default());

pub static __ALL__: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

/// Adapter to provide zena_mode-compatible interface while using config_enhanced::Config.
#[derive(Debug, Clone)]
pub struct ConfigAdapter {
}

impl ConfigAdapter {
    /// Dict-style access for compatibility (e.g. config::get('MAX_FILE_SIZE', 10*1024*1024)).
    pub fn get(&self, key: String, default: String) -> () {
        // Dict-style access for compatibility (e.g. config::get('MAX_FILE_SIZE', 10*1024*1024)).
        /* getattr */ /* getattr */ default
    }
    pub fn BASE_DIR(&self) -> &String {
        Config.PROJECT_ROOT
    }
    pub fn BIN_DIR(&self) -> &String {
        (Config.PROJECT_ROOT / "_bin".to_string())
    }
    /// Alias for Config.MODELS_DIR - use this consistently.
    pub fn MODEL_DIR(&self) -> &String {
        // Alias for Config.MODELS_DIR - use this consistently.
        Config.MODELS_DIR
    }
    /// Direct access to Config.MODELS_DIR.
    pub fn MODELS_DIR(&self) -> &String {
        // Direct access to Config.MODELS_DIR.
        Config.MODELS_DIR
    }
    pub fn default_model(&self) -> &String {
        Config.DEFAULT_MODEL
    }
    pub fn rag(&self) -> &String {
        // TODO: nested class RAGConfig
        RAGConfig()
    }
    pub fn embedding_config(&self) -> &String {
        // TODO: nested class EmbeddingConfig
        EmbeddingConfig()
    }
}
