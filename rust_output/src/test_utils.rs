/// test_utils::py - Shared test utilities for ZenAI

use anyhow::{Result, Context};
use std::path::PathBuf;

/// Resolve models directory: env var > config > project-local > fallback.
pub fn _default_models_dir() -> Result<PathBuf> {
    // Resolve models directory: env var > config > project-local > fallback.
    let mut env = std::env::var(&"ZENAI_MODEL_DIR".to_string()).unwrap_or_default().cloned().unwrap_or("".to_string());
    if (env && PathBuf::from(env).is_dir()) {
        PathBuf::from(env)
    }
    // try:
    {
        // TODO: from config import MODEL_DIR
        if MODEL_DIR.is_dir() {
            MODEL_DIR
        }
    }
    // except Exception as _e:
    let mut local = (PathBuf::from(file!()).canonicalize().unwrap_or_default().parent().unwrap_or(std::path::Path::new("")).parent().unwrap_or(std::path::Path::new("")) / "models".to_string());
    if local.is_dir() {
        local
    }
    Ok(local)
}

/// Scan for available GGUF models in a directory and return Path objects.
pub fn scan_models(models_dir: String) -> () {
    // Scan for available GGUF models in a directory and return Path objects.
    if models_dir.is_none() {
        let mut models_path = _default_models_dir();
    } else {
        let mut models_path = PathBuf::from(models_dir);
    }
    if !models_path.exists() {
        vec![]
    }
    models_path.glob("*.gguf".to_string()).into_iter().collect::<Vec<_>>()
}
