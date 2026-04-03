/// Local LLM Wrapper Adapter
/// 
/// Integrates Local_LLM's model discovery (LocalLLMManager) with
/// FIFOLlamaCppAdapter for in-memory inference.
/// 
/// Flow:
/// 1. LocalLLMManager discovers GGUF models in C:\AI\Models
/// 2. User selects model (or first balanced/chat model is auto-selected)
/// 3. FIFOLlamaCppAdapter loads model in-process via llama-cpp-python
/// 4. Queries go through FIFO buffers (no ports, no HTTP)

use anyhow::{Result, Context};
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Wrapper adapter combining Local_LLM discovery + FIFO in-memory inference.
/// 
/// - Uses LocalLLMManager to find available GGUF models
/// - Creates FIFOLlamaCppAdapter with selected model path
/// - All inference is in-memory (no ports, no HTTP)
/// - FIFO buffers provide backpressure and metrics
#[derive(Debug, Clone)]
pub struct LocalLLMWrapperAdapter {
    pub manager: Option<serde_json::Value>,
    pub adapter: Option<serde_json::Value>,
    pub model_name: String,
    pub _available_models: Vec<serde_json::Value>,
}

impl LocalLLMWrapperAdapter {
    pub fn new(model_name: Option<String>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Self {
        Self {
            manager: None,
            adapter: None,
            model_name,
            _available_models: vec![],
        }
    }
    /// Select a model from discovered models.
    pub fn _select_model(&mut self, model_name: Option<String>) -> Option<String> {
        // Select a model from discovered models.
        if !self._available_models {
            None
        }
        if model_name {
            for card in self._available_models.iter() {
                let mut name = card.get(&"name".to_string()).cloned().unwrap_or("".to_string());
                let mut filename = card.get(&"filename".to_string()).cloned().unwrap_or("".to_string());
                if (name.contains(&model_name) || filename.contains(&model_name)) {
                    let mut path = card.get(&"path".to_string()).cloned();
                    if path {
                        logger.info(format!("[LocalLLMWrapper] Selected requested model: {}", name));
                        path
                    }
                }
            }
        }
        for card in self._available_models.iter() {
            let mut cat = card.get(&"category".to_string()).cloned().unwrap_or("".to_string());
            if ("balanced".to_string(), "fast".to_string()).contains(&cat) {
                let mut path = card.get(&"path".to_string()).cloned();
                if path {
                    logger.info(format!("[LocalLLMWrapper] Auto-selected: {}", card.get(&"name".to_string()).cloned().unwrap_or(path)));
                    path
                }
            }
        }
        let mut path = self._available_models[0].get(&"path".to_string()).cloned();
        if path {
            logger.info(format!("[LocalLLMWrapper] Using first available model: {}", path));
        }
        path
    }
    /// Switch to a different model.
    pub fn switch_model(&self, new_model_path: String) -> bool {
        // Switch to a different model.
        if (self.adapter && /* hasattr(self.adapter, "switch_model".to_string()) */ true) {
            self.adapter.switch_model(new_model_path)
        }
        false
    }
    /// Check if adapter is ready for queries.
    pub async fn validate(&self) -> Result<bool> {
        // Check if adapter is ready for queries.
        if self.adapter {
            // try:
            {
                self.adapter.validate().await
            }
            // except Exception as _e:
        }
        Ok(false)
    }
    /// Query via FIFO in-memory inference (no ports).
    pub async fn query(&self, request: LLMRequest) -> Result<AsyncGenerator</* unknown */>> {
        // Query via FIFO in-memory inference (no ports).
        if !self.adapter {
            /* yield "❌ Local LLM wrapper: FIFO adapter not available".to_string() */;
            if !FIFOLlamaCppAdapter {
                /* yield "\n→ FIFOLlamaCppAdapter could not be imported".to_string() */;
            }
            /* yield "\n→ Install: pip install llama-cpp-python".to_string() */;
            return;
        }
        // try:
        {
            // async for
            while let Some(chunk) = self.adapter.query(request).next().await {
                /* yield chunk */;
            }
        }
        // except Exception as e:
    }
    /// TRUE token-level streaming — passthrough to FIFO adapter.
    /// 
    /// Each yield = one real token from the model, instantly.
    /// Used by api_server v2 for true SSE streaming.
    pub async fn query_stream_tokens(&mut self, request: String) -> Result<AsyncGenerator</* unknown */>> {
        // TRUE token-level streaming — passthrough to FIFO adapter.
        // 
        // Each yield = one real token from the model, instantly.
        // Used by api_server v2 for true SSE streaming.
        if !self.adapter {
            /* yield "❌ Local LLM wrapper: FIFO adapter not available".to_string() */;
            return;
        }
        if /* hasattr(self.adapter, "query_stream_tokens".to_string()) */ true {
            // try:
            {
                // async for
                while let Some(token) = self.adapter.query_stream_tokens(request).next().await {
                    /* yield token */;
                }
            }
            // except Exception as e:
        } else {
            // async for
            while let Some(chunk) = self.adapter.query(request).next().await {
                /* yield chunk */;
            }
        }
    }
    /// Cleanup.
    pub async fn close(&self) -> Result<()> {
        // Cleanup.
        if self.adapter {
            // try:
            {
                self.adapter.close().await;
            }
            // except Exception as exc:
        }
    }
    /// Return list of discovered model cards.
    pub fn get_available_models(&self) -> () {
        // Return list of discovered model cards.
        self._available_models
    }
    /// Get FIFO buffer statistics from adapter.
    pub fn get_stats(&self) -> () {
        // Get FIFO buffer statistics from adapter.
        if (self.adapter && /* hasattr(self.adapter, "get_stats".to_string()) */ true) {
            self.adapter.get_stats()
        }
        HashMap::new()
    }
}
