/// Centralized Configuration for ZEN_RAG
/// ======================================
/// This module delegates to config_enhanced::py which is the SINGLE SOURCE OF TRUTH.
/// 
/// All constants, paths, helper functions, and the Config class are re-exported from
/// config_enhanced so that ``from Core.config import ...`` continues to work everywhere.
/// 
/// Priority Order (highest to lowest):
/// 1. Environment variables (overrides applied in config_enhanced::py)
/// 2. config_enhanced::py values
/// 3. Hardcoded defaults in config_enhanced::py

use anyhow::{Result, Context};
use crate::config_enhanced::{Config, PROVIDERS, LLMProvider, LLMConfig, ProviderConfig, get_provider, get_all_providers, get_local_providers, get_external_providers, save_config, load_config, validate_config};

pub const PROJECT_ROOT: &str = "Config.PROJECT_ROOT";

pub const DEFAULT_MODELS_DIR: &str = "Config.MODELS_DIR";

pub const MODELS_DIR: &str = "Config.MODELS_DIR";

pub const CACHE_DIR: &str = "Config.CACHE_DIR";

pub const LOGS_DIR: &str = "Config.LOGS_DIR";

pub const UPLOADS_DIR: &str = "Config.UPLOADS_DIR";

pub const RAG_STORAGE_DIR: &str = "PROJECT_ROOT / 'rag_storage";

pub const DEFAULT_PROVIDER: &str = "Config.DEFAULT_PROVIDER";

pub const DEFAULT_MODEL: &str = "Config.DEFAULT_MODEL";

pub const INFERENCE_PARAMS: &str = "Config.INFERENCE_PARAMS";

pub const MODEL_OVERRIDES: &str = "Config.MODEL_OVERRIDES";

pub const DEFAULT_LLAMA_PORT: i64 = 0;

pub const MANAGEMENT_PORT: i64 = 0;

pub const LLAMA_STARTUP_TIMEOUT: i64 = 0;

pub const LLAMA_SHUTDOWN_TIMEOUT: i64 = 0;

pub const GPU_LAYERS: i64 = 0;

pub const CONTEXT_SIZE: i64 = 0;

pub const BATCH_SIZE: i64 = 0;

pub const STATUS_CACHE_TTL: f64 = 0.0;

pub const RESPONSE_CACHE_TTL: &str = "Config.CACHE_TTL";

pub const MAX_CACHE_SIZE: &str = "Config.MAX_CACHE_SIZE";

pub const CACHE_TYPE: &str = "Config.CACHE_TYPE";

pub const QDRANT_URL: &str = "Config.QDRANT_URL";

pub const QDRANT_COLLECTION: &str = "Config.QDRANT_COLLECTION";

pub const EMBEDDING_MODEL: &str = "Config.EMBEDDING_MODEL";

pub const EMBEDDING_DIM: &str = "Config.EMBEDDING_DIM";

pub const TOP_K_RESULTS: &str = "Config.TOP_K_RESULTS";

pub const SEMANTIC_WEIGHT: &str = "Config.SEMANTIC_WEIGHT";

pub const KEYWORD_WEIGHT: &str = "Config.KEYWORD_WEIGHT";

pub const RATE_LIMIT_ENABLED: &str = "Config.RATE_LIMIT_ENABLED";

pub const RATE_LIMIT_REQUESTS: &str = "Config.RATE_LIMIT_REQUESTS";

pub const RATE_LIMIT_WINDOW: &str = "Config.RATE_LIMIT_WINDOW";

pub const MAX_INPUT_LENGTH: &str = "Config.MAX_INPUT_LENGTH";

pub const MAX_FILE_SIZE: &str = "Config.MAX_FILE_SIZE";

pub const ALLOWED_EXTENSIONS: &str = "Config.ALLOWED_EXTENSIONS";

pub const LOG_LEVEL: &str = "Config.LOG_LEVEL";

pub const LOG_FORMAT: &str = "Config.LOG_FORMAT";

pub const LOG_FILE: &str = "Config.LOG_FILE";

pub const API_TIMEOUT: &str = "Config.API_TIMEOUT";

pub const MAX_RETRIES: &str = "Config.MAX_RETRIES";

pub const RETRY_DELAY: &str = "Config.RETRY_DELAY";

pub const STREAMLIT_HOST: &str = "Config.STREAMLIT_HOST";

pub const STREAMLIT_PORT: &str = "Config.STREAMLIT_PORT";

pub const STREAMLIT_THEME: &str = "Config.STREAMLIT_THEME";

pub const FEATURES: &str = "Config.FEATURES";

/// Get the models directory, creating if needed.
pub fn get_models_dir() -> () {
    // Get the models directory, creating if needed.
    Config.MODELS_DIR.create_dir_all();
    Config.MODELS_DIR
}

/// Get only cloud/external providers (require API keys).
pub fn get_cloud_providers() -> () {
    // Get only cloud/external providers (require API keys).
    get_external_providers()
}
