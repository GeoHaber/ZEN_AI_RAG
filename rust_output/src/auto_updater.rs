use anyhow::{Result, Context};
use crate::config_system::{config};
use regex::Regex;
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Intelligence layer to discover high-performing GGUF models on Hugging Face.
/// When RAG_LOCAL_ONLY=1, no HuggingFace calls are made (returns empty).
#[derive(Debug, Clone)]
pub struct ModelScout {
    pub api: Option<serde_json::Value>,
    pub categories: HashMap<String, serde_json::Value>,
}

impl ModelScout {
    pub fn new() -> Self {
        Self {
            api: None,
            categories: HashMap::from([("coding".to_string(), vec!["qwen".to_string(), "codellama".to_string(), "deepseek-coder".to_string()]), ("reasoning".to_string(), vec!["meta-llama".to_string(), "mistral".to_string(), "phi-3".to_string()]), ("creative".to_string(), vec!["gemma".to_string(), "command-r".to_string()])]),
        }
    }
    /// Scour Hugging Face for trending/best models in a given category.
    /// When RAG_LOCAL_ONLY=1 or no API, returns [] (no HuggingFace calls).
    pub fn find_shiny_models(&mut self, category: String, limit: i64) -> Result<Vec<HashMap>> {
        // Scour Hugging Face for trending/best models in a given category.
        // When RAG_LOCAL_ONLY=1 or no API, returns [] (no HuggingFace calls).
        if (_local_only_skip_hf() || self.api.is_none()) {
            vec![]
        }
        // try:
        {
            let mut keywords = self.categories.get(&category.to_lowercase()).cloned().unwrap_or(vec!["llama".to_string()]);
            let mut models = self.api.list_models(/* task= */ "text-generation".to_string(), /* library= */ "gguf".to_string(), /* tags= */ keywords, /* sort= */ "downloads".to_string(), /* direction= */ -1, /* limit= */ (limit * 3));
            let mut shiny_list = vec![];
            for m in models::iter() {
                if m.downloads > 1000 {
                    shiny_list.push(HashMap::from([("id".to_string(), m.modelId), ("downloads".to_string(), m.downloads), ("likes".to_string(), m.likes), ("last_modified".to_string(), m.lastModified)]));
                }
            }
            { let mut v = shiny_list.clone(); v.sort(); v }[..limit]
        }
        // except Exception as e:
    }
}

/// true when RAG_LOCAL_ONLY=1: skip all HuggingFace API/hub calls.
pub fn _local_only_skip_hf() -> bool {
    // true when RAG_LOCAL_ONLY=1: skip all HuggingFace API/hub calls.
    (/* getattr */ false || ("1".to_string(), "true".to_string(), "yes".to_string()).contains(&std::env::var(&"RAG_LOCAL_ONLY".to_string()).unwrap_or_default().cloned().unwrap_or("".to_string()).trim().to_string().to_lowercase()))
}

/// Compare llama.cpp version tags (e.g., 'b4100' or 'v1.2.3').
/// Returns true if remote_tag is logically strictly greater than local_tag.
pub fn is_newer(remote_tag: String, local_tag: String) -> Result<bool> {
    // Compare llama.cpp version tags (e.g., 'b4100' or 'v1.2.3').
    // Returns true if remote_tag is logically strictly greater than local_tag.
    let parse_version = |tag| {
        let mut digits = re::findall("\\d+".to_string(), tag);
        /* tuple */ (digits.iter().map(int).collect::<Vec<_>>())
    };
    // try:
    {
        let mut remote_val = parse_version(remote_tag);
        let mut local_val = parse_version(local_tag);
        remote_val > local_val
    }
    // except Exception as _e:
}

/// Queries GitHub API for the latest llama.cpp release.
/// Returns update info dict if a newer version is found, else None.
pub fn check_for_updates(current_tag: String) -> Result<HashMap> {
    // Queries GitHub API for the latest llama.cpp release.
    // Returns update info dict if a newer version is found, else None.
    let mut url = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest".to_string();
    let mut headers = HashMap::from([("Accept".to_string(), "application/vnd.github.v3+json".to_string())]);
    // try:
    {
        let mut client = httpx.Client();
        {
            let mut resp = client.get(&url).cloned().unwrap_or(/* headers= */ headers);
            if resp.status_code == 200 {
                let mut data = resp.json();
                let mut latest_tag = data.get(&"tag_name".to_string()).cloned().unwrap_or("".to_string());
                if is_newer(latest_tag, current_tag) {
                    logger.info(format!("✨ Shiny new version found: {} (Current: {})", latest_tag, current_tag));
                    HashMap::from([("tag".to_string(), latest_tag), ("url".to_string(), data.get(&"html_url".to_string()).cloned()), ("assets".to_string(), data.get(&"assets".to_string()).cloned().unwrap_or(vec![]))])
                }
            }
        }
    }
    // except Exception as e:
    Ok(None)
}

/// Safely swaps binary files with backup.
pub fn perform_swap(target_path: String, new_path: String) -> Result<()> {
    // Safely swaps binary files with backup.
    let mut target = PathBuf::from(target_path);
    let mut new_bin = PathBuf::from(new_path);
    let mut backup = target.with_extension(".bak".to_string());
    if !new_bin.exists() {
        return Err(anyhow::anyhow!("FileNotFoundError(f'New binary not found at {new_path}')"));
    }
    if target.exists() {
        if backup.exists() {
            backup.remove_file().ok();
        }
        os::rename(target, backup);
        logger.info(format!("Backed up current binary to {}", backup.name));
    }
    os::rename(new_bin, target);
    Ok(logger.info(format!("Successfully swapped binary: {}", target.name)))
}

/// Attempt to get local llama-server version using --version.
pub async fn get_local_version() -> Result<String> {
    // Attempt to get local llama-server version using --version.
    // TODO: import asyncio
    let mut bin_path = (PathBuf::from(config::bin_dir) / "llama-server::exe".to_string());
    if !bin_path.exists() {
        "none".to_string()
    }
    // try:
    {
        let mut proc = asyncio.create_subprocess_exec(bin_path.to_string(), "--version".to_string(), /* stdout= */ asyncio.subprocess::PIPE, /* stderr= */ asyncio.subprocess::PIPE).await;
        let (mut stdout, mut stderr) = proc.communicate().await;
        let mut version_str = (String::from_utf8_lossy(&stdout).to_string().trim().to_string() || String::from_utf8_lossy(&stderr).to_string().trim().to_string());
        let mut r#match = regex::Regex::new(&"b\\d+".to_string()).unwrap().is_match(&version_str);
        if r#match { r#match.group(0) } else { version_str[..10] }
    }
    // except Exception as _e:
}
