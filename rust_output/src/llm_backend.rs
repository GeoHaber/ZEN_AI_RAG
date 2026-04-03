/// LLM Backend - Pure async LLM calling without Streamlit dependencies
/// Provides async/streaming LLM interface for decoupled backend operations
/// 
/// Examples:
/// >>> backend = LLMBackend()
/// >>> response = asyncio.run(backend.call_llm("OpenAI", "gpt-4", "key", messages))
/// >>> # Or use streaming:
/// >>> async with backend.stream_llm("OpenAI", "gpt-4", "key", messages) as stream:
/// ...     async for chunk in stream:
/// ...         print(chunk, end='')

use anyhow::{Result, Context};
use crate::llm_adapters::{LLMResponse};
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _BACKEND_INSTANCE: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

/// Pure async LLM backend for calling various LLM providers.
/// No Streamlit dependencies - suitable for testing, servers, CLIs.
/// 
/// Supports:
/// - Async/await patterns
/// - Streaming responses
/// - Error recovery
/// - Provider abstraction (OpenAI, Claude, Ollama, Local llama-cpp, Gemini)
#[derive(Debug, Clone)]
pub struct LLMBackend {
    pub timeout: String,
    pub _providers: HashMap<String, serde_json::Value>,
}

impl LLMBackend {
    /// Args:
    /// timeout: Request timeout in seconds
    pub fn new(timeout: f64) -> Self {
        Self {
            timeout,
            _providers: HashMap::new(),
        }
    }
    /// Call LLM synchronously and return full response.
    /// 
    /// Args:
    /// provider: Provider name ("OpenAI", "Ollama", "Claude", "Local (llama-cpp)", "Gemini")
    /// model: Model name
    /// api_key: API key if required
    /// messages: List of message dicts with 'role' and 'content'
    /// prompt: Single prompt string (alt to messages)
    /// temperature: Sampling temperature
    /// max_tokens: Maximum tokens to generate
    /// system_prompt: System prompt override
    /// 
    /// Returns:
    /// LLMResponse with full text response
    pub async fn call_llm(&mut self, provider: String, model: String, api_key: Option<String>, messages: Option<Vec<HashMap>>, prompt: Option<String>, temperature: f64, max_tokens: i64, system_prompt: Option<String>) -> Result<LLMResponse> {
        // Call LLM synchronously and return full response.
        // 
        // Args:
        // provider: Provider name ("OpenAI", "Ollama", "Claude", "Local (llama-cpp)", "Gemini")
        // model: Model name
        // api_key: API key if required
        // messages: List of message dicts with 'role' and 'content'
        // prompt: Single prompt string (alt to messages)
        // temperature: Sampling temperature
        // max_tokens: Maximum tokens to generate
        // system_prompt: System prompt override
        // 
        // Returns:
        // LLMResponse with full text response
        // try:
        {
            let mut text = "".to_string();
            // async for
            while let Some(chunk) = self.stream_llm(/* provider= */ provider, /* model= */ model, /* api_key= */ api_key, /* messages= */ messages, /* prompt= */ prompt, /* temperature= */ temperature, /* max_tokens= */ max_tokens, /* system_prompt= */ system_prompt).next().await {
                text += chunk;
            }
            LLMResponse(/* text= */ (text || "".to_string()), /* model= */ model, /* provider= */ provider, /* success= */ true)
        }
        // except Exception as e:
    }
    /// Stream LLM response as async generator.
    /// 
    /// Args:
    /// provider: Provider name
    /// model: Model name
    /// api_key: API key if required
    /// messages: List of message dicts
    /// prompt: Single prompt string
    /// temperature: Sampling temperature
    /// max_tokens: Maximum tokens
    /// system_prompt: System prompt override
    /// 
    /// Yields:
    /// Text chunks as they arrive from the LLM
    pub async fn stream_llm(&mut self, provider: String, model: String, api_key: Option<String>, messages: Option<Vec<HashMap>>, prompt: Option<String>, temperature: f64, max_tokens: i64, system_prompt: Option<String>) -> Result<AsyncGenerator</* unknown */>> {
        // Stream LLM response as async generator.
        // 
        // Args:
        // provider: Provider name
        // model: Model name
        // api_key: API key if required
        // messages: List of message dicts
        // prompt: Single prompt string
        // temperature: Sampling temperature
        // max_tokens: Maximum tokens
        // system_prompt: System prompt override
        // 
        // Yields:
        // Text chunks as they arrive from the LLM
        if (messages.is_none() && prompt.is_none()) {
            return Err(anyhow::anyhow!("ValueError(\"Must provide either 'messages' or 'prompt'\")"));
        }
        if (prompt.is_none() && messages) {
            let mut prompt = messages.iter().map(|m| format!("{}: {}", m["role".to_string()], m["content".to_string()])).collect::<Vec<_>>().join(&"\n".to_string());
        }
        let mut provider_normalized = self._normalize_provider(provider);
        // try:
        {
            // TODO: from adapter_factory import create_adapter
            // TODO: from llm_adapters import LLMRequest as AdapterRequest
        }
        // except ImportError as _e:
        let mut provider_to_adapter = HashMap::from([("ollama".to_string(), "Ollama".to_string()), ("llama.cpp".to_string(), "Local (llama-cpp)".to_string()), ("local (llama-cpp)".to_string(), "Local (llama-cpp)".to_string()), ("local_llama".to_string(), "Local (llama-cpp)".to_string()), ("openai".to_string(), "OpenAI".to_string()), ("claude".to_string(), "Anthropic (Claude)".to_string()), ("anthropic".to_string(), "Anthropic (Claude)".to_string()), ("anthropic (claude)".to_string(), "Anthropic (Claude)".to_string()), ("gemini".to_string(), "Google (Gemini)".to_string()), ("google".to_string(), "Google (Gemini)".to_string()), ("google (gemini)".to_string(), "Google (Gemini)".to_string()), ("huggingface".to_string(), "HuggingFace".to_string())]);
        let mut adapter_name = provider_to_adapter.get(&provider_normalized).cloned().unwrap_or(provider);
        // try:
        {
            let mut adapter = create_adapter(adapter_name, /* api_key= */ api_key);
        }
        // except Exception as e:
        let mut req = AdapterRequest(/* provider= */ adapter_name, /* model= */ model, /* prompt= */ prompt, /* temperature= */ temperature, /* max_tokens= */ max_tokens, /* top_p= */ 0.9_f64, /* system_prompt= */ system_prompt, /* api_key= */ api_key, /* stream= */ true);
        // try:
        {
            let mut ok = adapter.validate().await;
            if !ok {
                /* yield format!("Error: provider {} not available or not configured", provider) */;
                return;
            }
            // async for
            while let Some(chunk) = adapter.query(req).next().await {
                if /* /* isinstance(chunk, str) */ */ true {
                    /* yield chunk */;
                }
            }
        }
        // except Exception as e:
        // finally:
            // try:
            {
                adapter.close().await;
            }
            // except Exception as exc:
    }
    /// Normalize provider name to lowercase
    pub fn _normalize_provider(&self, provider: String) -> String {
        // Normalize provider name to lowercase
        if provider { provider.to_lowercase() } else { "openai".to_string() }
    }
    /// Check if provider is available and ready.
    /// 
    /// Args:
    /// provider: Provider name
    /// api_key: API key if required
    /// 
    /// Returns:
    /// true if provider can be used, false otherwise
    pub async fn validate_provider(&mut self, provider: String, api_key: Option<String>) -> Result<bool> {
        // Check if provider is available and ready.
        // 
        // Args:
        // provider: Provider name
        // api_key: API key if required
        // 
        // Returns:
        // true if provider can be used, false otherwise
        // try:
        {
            // TODO: from adapter_factory import create_adapter as _create_adapter
            let mut provider_map = HashMap::from([("ollama".to_string(), "OLLAMA".to_string()), ("llama.cpp".to_string(), "LOCAL_LLAMA".to_string()), ("local (llama-cpp)".to_string(), "LOCAL_LLAMA".to_string()), ("openai".to_string(), "OPENAI".to_string()), ("claude".to_string(), "CLAUDE".to_string()), ("anthropic (claude)".to_string(), "CLAUDE".to_string()), ("gemini".to_string(), "GEMINI".to_string()), ("google (gemini)".to_string(), "GEMINI".to_string())]);
            let mut enum_str = provider_map.get(&self._normalize_provider(provider)).cloned().unwrap_or("CUSTOM".to_string());
            // try:
            {
                // TODO: from llm_adapters import LLMProvider as AdapterProvider
            }
            // except ImportError as _e:
            let mut enum_provider = /* getattr(AdapterProvider, enum_str) */ Default::default();
            let mut adapter = _create_adapter(enum_provider, /* api_key= */ api_key);
            let mut result = adapter.validate().await;
            adapter.close().await;
            result
        }
        // except Exception as e:
    }
}

/// Get or create singleton LLM backend
pub fn get_backend() -> LLMBackend {
    // Get or create singleton LLM backend
    // global/nonlocal _backend_instance
    if _backend_instance.is_none() {
        let mut _backend_instance = LLMBackend();
    }
    _backend_instance
}

/// Synchronous wrapper for backward compatibility with existing code.
/// 
/// This is called from Streamlit app::py. It runs the async backend
/// in a thread to avoid event loop conflicts.
/// 
/// Args:
/// provider: Provider name (like "llama.cpp", "Ollama", "OpenAI", "Claude", "Gemini")
/// model: Model name
/// api_key: API key
/// messages: List of message dicts
/// 
/// Returns:
/// Response text string
pub fn call_llm(provider: String, model: String, api_key: String, messages: Vec<HashMap>) -> Result<String> {
    // Synchronous wrapper for backward compatibility with existing code.
    // 
    // This is called from Streamlit app::py. It runs the async backend
    // in a thread to avoid event loop conflicts.
    // 
    // Args:
    // provider: Provider name (like "llama.cpp", "Ollama", "OpenAI", "Claude", "Gemini")
    // model: Model name
    // api_key: API key
    // messages: List of message dicts
    // 
    // Returns:
    // Response text string
    // TODO: from concurrent.futures import ThreadPoolExecutor
    let mut provider_map = HashMap::from([("llama.cpp".to_string(), "Local (llama-cpp)".to_string()), ("local (llama-cpp)".to_string(), "Local (llama-cpp)".to_string()), ("local llama-cpp".to_string(), "Local (llama-cpp)".to_string()), ("ollama".to_string(), "Ollama".to_string()), ("openai".to_string(), "OpenAI".to_string()), ("claude".to_string(), "Anthropic (Claude)".to_string()), ("anthropic".to_string(), "Anthropic (Claude)".to_string()), ("anthropic (claude)".to_string(), "Anthropic (Claude)".to_string()), ("gemini".to_string(), "Google (Gemini)".to_string()), ("google".to_string(), "Google (Gemini)".to_string()), ("google (gemini)".to_string(), "Google (Gemini)".to_string()), ("huggingface".to_string(), "HuggingFace".to_string())]);
    let mut provider_normalized = provider.to_lowercase().trim().to_string();
    let mut provider_full = provider_map.get(&provider_normalized).cloned().unwrap_or(provider);
    let mut backend = get_backend();
    let _run_in_thread = || {
        // Run async code in a new thread with its own event loop
        let _run = || {
            let mut response = backend.call_llm(/* provider= */ provider_full, /* model= */ model, /* api_key= */ api_key, /* messages= */ messages).await;
            if response.success { response.text } else { format!("Error: {}", response.error) }
        };
        // try:
        {
            let mut r#loop = asyncio.new_event_loop();
            asyncio.set_event_loop(r#loop);
            let mut result = r#loop.run_until_complete(_run());
            r#loop.close();
            result
        }
        // except Exception as e:
    };
    // try:
    {
        let mut executor = ThreadPoolExecutor(/* max_workers= */ 1);
        {
            let mut future = executor.submit(_run_in_thread);
            let mut result = future.result(/* timeout= */ 120);
        }
        result
    }
    // except Exception as e:
}
