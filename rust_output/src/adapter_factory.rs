/// Adapter Factory - Creates LLM adapter instances
/// 
/// This module provides factory functions to create the correct adapter
/// based on provider selection. It's the single point of creation for
/// all LLM adapters, enabling flexibility and testing.
/// 
/// The factory pattern ensures:
/// - Single place to create adapters (easy to mock in tests)
/// - Consistent initialization across codebase
/// - Type safety and validation
/// - Easy to add new providers

use anyhow::{Result, Context};
use crate::llm_adapters::{BaseLLMAdapter, LocalLlamaAdapter, OllamaAdapter, OpenAIAdapter, AnthropicAdapter, HuggingFaceAdapter, GeminiAdapter};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static ADAPTER_MAP: std::sync::LazyLock<HashMap<String, Type<BaseLLMAdapter>>> = std::sync::LazyLock::new(|| HashMap::new());

pub static PROVIDER_ALIAS: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub static __ALL__: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub fn _build_adapter_map() -> HashMap<String, Type<BaseLLMAdapter>> {
    let mut m = HashMap::from([("Local (llama-cpp)".to_string(), if LocalLLMWrapperAdapter.is_some() { LocalLLMWrapperAdapter } else { LocalLlamaAdapter }), ("Ollama".to_string(), OllamaAdapter), ("OpenAI".to_string(), OpenAIAdapter), ("Anthropic (Claude)".to_string(), AnthropicAdapter), ("HuggingFace".to_string(), HuggingFaceAdapter), ("Google (Gemini)".to_string(), GeminiAdapter)]);
    if MLXAdapter.is_some() {
        m["Local (MLX)".to_string()] = MLXAdapter;
    }
    m
}

/// Factory function to create the correct LLM adapter.
/// 
/// Validates provider name, handles optional API key, and returns
/// an initialized adapter instance ready to use.
/// 
/// Args:
/// provider: Provider name (must match one of ADAPTER_MAP keys)
/// api_key: API key if required (will use env var if not provided)
/// endpoint: Custom endpoint URL (for local or custom APIs)
/// model_name: Model name to use with this adapter
/// **kwargs: Additional arguments passed to adapter constructor
/// 
/// Returns:
/// Initialized adapter instance ready for LLM calls
/// 
/// Raises:
/// ValueError: If provider is unknown or required config missing
/// 
/// Examples:
/// # Local model
/// adapter = create_adapter("Local (llama-cpp)")
/// 
/// # Cloud API with key
/// adapter = create_adapter("OpenAI", api_key="sk-...")
/// 
/// # Custom endpoint
/// adapter = create_adapter("Ollama", endpoint="http://localhost:11434")
pub fn create_adapter(provider: String, api_key: Option<String>, endpoint: Option<String>, model_name: Option<String>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Result<BaseLLMAdapter> {
    // Factory function to create the correct LLM adapter.
    // 
    // Validates provider name, handles optional API key, and returns
    // an initialized adapter instance ready to use.
    // 
    // Args:
    // provider: Provider name (must match one of ADAPTER_MAP keys)
    // api_key: API key if required (will use env var if not provided)
    // endpoint: Custom endpoint URL (for local or custom APIs)
    // model_name: Model name to use with this adapter
    // **kwargs: Additional arguments passed to adapter constructor
    // 
    // Returns:
    // Initialized adapter instance ready for LLM calls
    // 
    // Raises:
    // ValueError: If provider is unknown or required config missing
    // 
    // Examples:
    // # Local model
    // adapter = create_adapter("Local (llama-cpp)")
    // 
    // # Cloud API with key
    // adapter = create_adapter("OpenAI", api_key="sk-...")
    // 
    // # Custom endpoint
    // adapter = create_adapter("Ollama", endpoint="http://localhost:11434")
    if !/* /* isinstance(provider, str) */ */ true {
        let mut provider = /* getattr */ provider.to_string();
    }
    let mut provider_normalized = provider.trim().to_string();
    let mut provider_mapped = PROVIDER_ALIAS.get(&provider_normalized).cloned().unwrap_or(provider_normalized);
    if !ADAPTER_MAP.contains(&provider_mapped) {
        let mut available = ADAPTER_MAP.keys().join(&", ".to_string());
        return Err(anyhow::anyhow!("ValueError(f\"Unknown LLM provider: '{provider_normalize}'\\nValid options: {available}\")"));
    }
    let mut adapter_class = ADAPTER_MAP[&provider_mapped];
    let mut init_args = HashMap::new();
    let mut ENV_KEY_MAP = HashMap::from([("OpenAI".to_string(), "OPENAI_API_KEY".to_string()), ("Anthropic (Claude)".to_string(), "ANTHROPIC_API_KEY".to_string()), ("HuggingFace".to_string(), "HUGGINGFACE_API_KEY".to_string()), ("Google (Gemini)".to_string(), "GOOGLE_API_KEY".to_string())]);
    if api_key {
        init_args["api_key".to_string()] = api_key;
    } else if ENV_KEY_MAP.contains(&provider_mapped) {
        let mut env_key = std::env::var(&ENV_KEY_MAP[&provider_mapped]).unwrap_or_default().cloned();
        if env_key {
            init_args["api_key".to_string()] = env_key;
        }
    }
    if endpoint {
        init_args["endpoint".to_string()] = endpoint;
    }
    if model_name {
        init_args["model_name".to_string()] = model_name;
    }
    init_args.extend(kwargs);
    // try:
    {
        let mut adapter = adapter_class(/* ** */ init_args);
        // try:
        {
            if adapter_class == LocalLLMWrapperAdapter {
                let mut fifo_adapter = /* getattr */ None;
                if (!fifo_adapter || !/* getattr */ false) {
                    // TODO: from local_adapters import FIFOLlamaCppAdapter
                    let mut adapter = FIFOLlamaCppAdapter(/* model_path= */ None);
                    logger.info("[Factory] Wrapper FIFO not ready; using FIFOLlamaCppAdapter directly".to_string());
                }
            }
        }
        // except Exception as e:
        adapter
    }
    // except TypeError as e:
}

/// Alias for create_adapter (backward compatibility).
/// 
/// This function exists to support code that expects 'get_adapter'
/// instead of 'create_adapter'. It simply calls create_adapter.
/// 
/// Args:
/// provider: Provider name
/// **kwargs: Passed to create_adapter
/// 
/// Returns:
/// Initialized adapter instance
pub fn get_adapter(provider: String, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> BaseLLMAdapter {
    // Alias for create_adapter (backward compatibility).
    // 
    // This function exists to support code that expects 'get_adapter'
    // instead of 'create_adapter'. It simply calls create_adapter.
    // 
    // Args:
    // provider: Provider name
    // **kwargs: Passed to create_adapter
    // 
    // Returns:
    // Initialized adapter instance
    create_adapter(provider, /* ** */ kwargs)
}

/// List all available adapters with descriptions.
/// 
/// Useful for UI dropdown lists and help text.
/// 
/// Returns:
/// Dict mapping provider names to descriptions
pub fn list_adapters() -> HashMap<String, String> {
    // List all available adapters with descriptions.
    // 
    // Useful for UI dropdown lists and help text.
    // 
    // Returns:
    // Dict mapping provider names to descriptions
    let mut out = HashMap::from([("Local (llama-cpp)".to_string(), "Run GGUF models locally using llama.cpp library".to_string()), ("Ollama".to_string(), "Run models via Ollama service (easiest local option)".to_string()), ("OpenAI".to_string(), "Use OpenAI's GPT-4/3.5 models (requires API key)".to_string()), ("Anthropic (Claude)".to_string(), "Use Claude models (requires API key)".to_string()), ("HuggingFace".to_string(), "Use HuggingFace Inference API (requires API key)".to_string()), ("Google (Gemini)".to_string(), "Use Google's Gemini models (requires API key)".to_string())]);
    if MLXAdapter.is_some() {
        out["Local (MLX)".to_string()] = "Run MLX models locally on Apple Silicon (mlx-lm)".to_string();
    }
    out
}

/// Check if a provider name is valid without creating an adapter.
/// 
/// Args:
/// provider: Provider name to validate
/// 
/// Returns:
/// true if provider is valid
/// 
/// Raises:
/// ValueError: If provider is invalid
pub fn validate_provider(provider: String) -> Result<bool> {
    // Check if a provider name is valid without creating an adapter.
    // 
    // Args:
    // provider: Provider name to validate
    // 
    // Returns:
    // true if provider is valid
    // 
    // Raises:
    // ValueError: If provider is invalid
    if !/* /* isinstance(provider, str) */ */ true {
        let mut provider = /* getattr */ provider.to_string();
    }
    if !ADAPTER_MAP.contains(&provider.trim().to_string()) {
        return Err(anyhow::anyhow!("ValueError(f'Unknown provider: {provider}')"));
    }
    Ok(true)
}
