/// _backend_stub::py - Minimal backend fallback when async_backend / mock_backend
/// are unavailable.  Allows the UI to render and display helpful error messages
/// rather than crashing on import.

use anyhow::{Result, Context};
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// No-op backend that returns safe defaults for every UI call.
#[derive(Debug, Clone)]
pub struct StubBackend {
}

impl StubBackend {
    pub async fn check_health(&self) -> () {
        HashMap::from([("status".to_string(), "stub".to_string()), ("message".to_string(), "No backend connected".to_string())])
    }
    pub async fn send_message(&self, message: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> () {
        HashMap::from([("response".to_string(), "[Backend unavailable] Please start the LLM engine first.".to_string()), ("tokens".to_string(), 0)])
    }
    pub async fn get_models(&self) -> () {
        vec![]
    }
    pub async fn get_status(&self) -> () {
        HashMap::from([("engine".to_string(), "stub".to_string()), ("status".to_string(), "offline".to_string())])
    }
    pub fn __repr__(&self) -> () {
        "<StubBackend>".to_string()
    }
}
