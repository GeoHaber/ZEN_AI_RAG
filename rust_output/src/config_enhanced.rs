/// Enhanced Configuration System for ZEN_RAG
/// ==========================================
/// Supports multiple LLM sources:
/// - Local (llama-cpp, Ollama)
/// - External (OpenAI, Anthropic, HuggingFace)
/// - Custom APIs

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static _DEFAULT_MODELS_DIR: std::sync::LazyLock<_default_models_dir> = std::sync::LazyLock::new(|| Default::default());

pub static PROVIDERS: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub const LLMPROVIDER: &str = "ProviderConfig";

pub static __ALL__: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub const LLMCONFIG: &str = "Config";

/// Configuration for an LLM provider (connection settings, not the enum).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderConfig {
    pub name: String,
    pub r#type: String,
    pub api_url: String,
    pub requires_api_key: bool,
    pub requires_model_download: bool,
    pub default_model: Option<String>,
    pub description: String,
}

impl ProviderConfig {
    /// Dict-style access for backward compatibility.
    pub fn get(&self, key: String, default: String) -> () {
        // Dict-style access for backward compatibility.
        /* getattr */ default
    }
}

/// Enhanced configuration for ZEN_RAG.
#[derive(Debug, Clone)]
pub struct Config {
}

/// Default to a 'models' directory inside the project root for portability.
pub fn _default_models_dir() -> String {
    // Default to a 'models' directory inside the project root for portability.
    (PathBuf::from(file!()).parent().unwrap_or(std::path::Path::new("")) / "models".to_string()).to_string()
}

/// Get provider configuration.
pub fn get_provider(provider_name: String) -> Option<LLMProvider> {
    // Get provider configuration.
    PROVIDERS.get(&provider_name).cloned()
}

/// Get all available providers.
pub fn get_all_providers() -> HashMap<String, LLMProvider> {
    // Get all available providers.
    PROVIDERS.clone()
}

/// Get only local providers.
pub fn get_local_providers() -> HashMap<String, LLMProvider> {
    // Get only local providers.
    PROVIDERS.iter().iter().filter(|(name, provider)| vec!["local".to_string(), "ollama".to_string()].contains(&provider.type)).map(|(name, provider)| (name, provider)).collect::<HashMap<_, _>>()
}

/// Get only external providers.
pub fn get_external_providers() -> HashMap<String, LLMProvider> {
    // Get only external providers.
    PROVIDERS.iter().iter().filter(|(name, provider)| !vec!["local".to_string(), "ollama".to_string()].contains(&provider.type)).map(|(name, provider)| (name, provider)).collect::<HashMap<_, _>>()
}

/// Save configuration to file.
pub fn save_config(config_dict: HashMap<String, serde_json::Value>) -> Result<bool> {
    // Save configuration to file.
    // try:
    {
        let mut config_file = (Config.PROJECT_ROOT / "config::json".to_string());
        let mut f = File::create(config_file)?;
        {
            json::dump(config_dict, f, /* indent= */ 2);
        }
        true
    }
    // except Exception as _e:
}

/// Load configuration from file.
pub fn load_config() -> Result<HashMap> {
    // Load configuration from file.
    // try:
    {
        let mut config_file = (Config.PROJECT_ROOT / "config::json".to_string());
        if config_file.exists() {
            let mut f = File::open(config_file)?;
            {
                json::load(f)
            }
        }
    }
    // except Exception as _e:
    Ok(HashMap::new())
}

/// Validate configuration.
pub fn validate_config() -> Result<bool> {
    // Validate configuration.
    // try:
    {
        for dir_path in vec![Config.MODELS_DIR, Config.CACHE_DIR, Config.LOGS_DIR].iter() {
            dir_path.create_dir_all();
        }
        if !PROVIDERS.contains(&Config.DEFAULT_PROVIDER) {
            println!("Warning: Default provider '{}' not found", Config.DEFAULT_PROVIDER);
            false
        }
        let mut provider = get_provider(Config.DEFAULT_PROVIDER);
        if (provider && vec!["local".to_string(), "ollama".to_string()].contains(&provider.type)) {
            if !Config.MODELS_DIR.exists() {
                println!("Warning: Models directory not found: {}", Config.MODELS_DIR);
            }
        }
        true
    }
    // except Exception as e:
}
