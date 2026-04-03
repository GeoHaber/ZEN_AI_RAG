/// mock_backend::py - Mock backend for testing / offline mode.
/// 
/// Provides the same interface as AsyncZenAIBackend but returns canned
/// responses without needing a running LLM engine.

use anyhow::{Result, Context};
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// In-memory mock that mirrors AsyncZenAIBackend's interface.
#[derive(Debug, Clone)]
pub struct MockAsyncBackend {
    pub client: Option<serde_json::Value>,
    pub api_url: String,
}

impl MockAsyncBackend {
    pub fn new() -> Self {
        Self {
            client: None,
            api_url: "mock://localhost".to_string(),
        }
    }
    pub async fn __aenter__(&self) -> () {
        self
    }
    pub async fn __aexit__(&self, exc: Vec<Box<dyn std::any::Any>>) -> () {
        // pass
    }
    /// Return a canned streaming response.
    pub async fn send_message_async(&self, message: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> AsyncGenerator</* unknown */> {
        // Return a canned streaming response.
        let mut response = format!("[Mock] Received: {}... (LLM engine not running)", message[..80]);
        for word in response.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>().iter() {
            /* yield (word + " ".to_string()) */;
        }
    }
    pub async fn check_health(&self) -> HashMap {
        HashMap::from([("status".to_string(), "mock".to_string()), ("message".to_string(), "Mock backend — no LLM engine".to_string())])
    }
    pub async fn get_models(&self) -> Vec<String> {
        vec!["mock-model.gguf".to_string()]
    }
    pub async fn download_model(&self, repo_id: String, filename: String) -> bool {
        logger.info(format!("[MockBackend] download_model({}, {}) — no-op", repo_id, filename));
        true
    }
    pub async fn set_active_model(&self, model_name: String) -> bool {
        logger.info(format!("[MockBackend] set_active_model({}) — no-op", model_name));
        true
    }
}
