/// src/version_checker::py — Version checking utility for ZEN_RAG
/// 
/// Checks for updates to:
/// 1. llama-cpp-python library (via PyPI)
/// 2. GGUF models on HuggingFace

use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Fetch the latest version of a package from PyPI.
pub fn get_latest_pypi_version(package_name: String) -> Result<Option<String>> {
    // Fetch the latest version of a package from PyPI.
    let mut url = format!("https://pypi.org/pypi/{}/json", package_name);
    // try:
    {
        let mut response = urllib::request.urlopen(url, /* timeout= */ 5);
        {
            let mut data = serde_json::from_str(&String::from_utf8_lossy(&response.read()).to_string()).unwrap();
            data["info".to_string()]["version".to_string()]
        }
    }
    // except Exception as e:
}

/// Check if llama-cpp-python has an update.
pub fn check_library_update(current_version: String) -> HashMap<String, Box<dyn std::any::Any>> {
    // Check if llama-cpp-python has an update.
    let mut package = "llama-cpp-python".to_string();
    let mut latest = get_latest_pypi_version(package);
    if !latest {
        HashMap::from([("update_available".to_string(), false), ("error".to_string(), "Could not fetch latest version".to_string())])
    }
    let mut has_update = version.parse(latest) > version.parse(current_version);
    HashMap::from([("current".to_string(), current_version), ("latest".to_string(), latest), ("update_available".to_string(), has_update), ("message".to_string(), if has_update { format!("Update available: {}", latest) } else { "Up to date".to_string() })])
}

/// Fetch metadata for a HuggingFace repository.
pub fn get_hf_model_metadata(repo_id: String) -> Result<Option<HashMap<String, Box<dyn std::any::Any>>>> {
    // Fetch metadata for a HuggingFace repository.
    let mut url = format!("https://huggingface.co/api/models/{}", repo_id);
    // try:
    {
        let mut req = urllib::request.Request(url, /* headers= */ HashMap::from([("User-Agent".to_string(), "ZEN_RAG/4.0".to_string())]));
        let mut response = urllib::request.urlopen(req, /* timeout= */ 5);
        {
            serde_json::from_str(&String::from_utf8_lossy(&response.read()).to_string()).unwrap()
        }
    }
    // except Exception as e:
}

/// Check if a model in a HF repo has been updated since local download.
/// local_last_modified should be in ISO format or YYYY-MM-DD.
pub fn check_model_update(repo_id: String, local_last_modified: String) -> HashMap<String, Box<dyn std::any::Any>> {
    // Check if a model in a HF repo has been updated since local download.
    // local_last_modified should be in ISO format or YYYY-MM-DD.
    let mut meta = get_hf_model_metadata(repo_id);
    if !meta {
        HashMap::from([("update_available".to_string(), false), ("error".to_string(), "Could not fetch repo metadata".to_string())])
    }
    let mut remote_last_modified = meta.get(&"lastModified".to_string()).cloned().unwrap_or("".to_string());
    if !remote_last_modified {
        HashMap::from([("update_available".to_string(), false), ("error".to_string(), "No lastModified date in remote".to_string())])
    }
    let mut has_update = remote_last_modified > local_last_modified;
    HashMap::from([("repo".to_string(), repo_id), ("remote_date".to_string(), remote_last_modified), ("local_date".to_string(), local_last_modified), ("update_available".to_string(), has_update)])
}
