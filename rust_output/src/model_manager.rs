/// model_manager::py - Hugging Face model search, download, and management.
/// 
/// Provides helpers used by the management API for browsing, downloading,
/// and activating GGUF models from Hugging Face Hub.

use anyhow::{Result, Context};
use crate::config_system::{config};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _POPULAR_MODELS: std::sync::LazyLock<Vec<HashMap<String, serde_json::Value>>> = std::sync::LazyLock::new(|| Vec::new());

/// Return a curated list of popular GGUF models.
pub fn get_popular_models() -> () {
    // Return a curated list of popular GGUF models.
    _POPULAR_MODELS
}

/// Search Hugging Face Hub for GGUF models.
pub fn search_hf_models(query: String, limit: i64) -> Result<()> {
    // Search Hugging Face Hub for GGUF models.
    // try:
    {
        // TODO: from huggingface_hub import HfApi
        let mut api = HfApi();
        let mut results = api.list_models(/* search= */ query, /* filter= */ "gguf".to_string(), /* sort= */ "downloads".to_string(), /* direction= */ -1, /* limit= */ limit);
        results.iter().map(|m| HashMap::from([("repo_id".to_string(), m.id), ("downloads".to_string(), m.downloads), ("likes".to_string(), m.likes)])).collect::<Vec<_>>()
    }
    // except ImportError as _e:
    // except Exception as e:
}

/// Download a model file in a background thread.
pub fn download_model_async(repo_id: String, filename: String) -> Result<()> {
    // Download a model file in a background thread.
    let _download = || {
        // try:
        {
            // TODO: from huggingface_hub import hf_hub_download
            logger.info(format!("Downloading {} from {}...", filename, repo_id));
            let mut path = hf_hub_download(/* repo_id= */ repo_id, /* filename= */ filename, /* local_dir= */ config::MODEL_DIR.to_string());
            logger.info(format!("Download complete: {}", path));
        }
        // except ImportError as _e:
        // except Exception as e:
    };
    let mut t = std::thread::spawn(|| {});
    t.start();
    Ok(t)
}
