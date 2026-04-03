/// OpenAI-Compatible Request/Response Models + InferenceRequest dataclass.
/// 
/// Extracted from api_server::py to keep models in one place.

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

/// OpenAI /v1/chat/completions request format.
#[derive(Debug, Clone)]
pub struct ChatCompletionRequest {
    pub model: String,
    pub messages: Vec<ChatMessage>,
    pub temperature: f64,
    pub top_p: f64,
    pub max_tokens: Option<i64>,
    pub stream: bool,
    pub stop: Option<Union<serde_json::Value>>,
    pub n: i64,
    pub frequency_penalty: f64,
    pub presence_penalty: f64,
    pub user: Option<String>,
    pub grammar: Option<String>,
    pub response_format: Option<HashMap<String, Box<dyn std::any::Any>>>,
    pub tools: Option<Vec<HashMap<String, Box<dyn std::any::Any>>>>,
    pub tool_choice: Option<Union<serde_json::Value>>,
    pub seed: Option<i64>,
    pub logprobs: Option<bool>,
    pub top_logprobs: Option<i64>,
    pub logit_bias: Option<HashMap<String, f64>>,
    pub top_k: Option<i64>,
    pub min_p: Option<f64>,
    pub repeat_penalty: Option<f64>,
}

/// OpenAI /v1/completions (legacy).
#[derive(Debug, Clone)]
pub struct CompletionRequest {
    pub model: String,
    pub prompt: Union<serde_json::Value>,
    pub suffix: Option<String>,
    pub temperature: f64,
    pub top_p: f64,
    pub max_tokens: Option<i64>,
    pub stream: bool,
    pub stop: Option<Union<serde_json::Value>>,
    pub echo: bool,
    pub seed: Option<i64>,
    pub logprobs: Option<bool>,
    pub top_logprobs: Option<i64>,
    pub logit_bias: Option<HashMap<String, f64>>,
}

/// Request for /v1/compact endpoint.
#[derive(Debug, Clone)]
pub struct CompactRequest {
    pub messages: Vec<ChatMessage>,
    pub keep_last_n: i64,
    pub summarize_older: bool,
    pub compress_text: bool,
    pub target_tokens: i64,
}

/// OpenAI /v1/embeddings request format.
#[derive(Debug, Clone)]
pub struct EmbeddingRequest {
    pub input: Union<serde_json::Value>,
    pub model: String,
    pub encoding_format: String,
}

/// Tokenize request.
#[derive(Debug, Clone)]
pub struct TokenizeRequest {
    pub content: String,
    pub add_special: bool,
    pub with_pieces: bool,
}

/// Detokenize request.
#[derive(Debug, Clone)]
pub struct DetokenizeRequest {
    pub tokens: Vec<i64>,
}

/// Count tokens without full tokenization.
#[derive(Debug, Clone)]
pub struct TokenCountRequest {
    pub content: String,
}

/// Dedicated FIM/infill endpoint request.
#[derive(Debug, Clone)]
pub struct InfillRequest {
    pub prompt: String,
    pub suffix: String,
    pub model: String,
    pub max_tokens: Option<i64>,
    pub temperature: f64,
    pub top_p: f64,
    pub stop: Option<Union<serde_json::Value>>,
    pub stream: bool,
}

/// Request to load a LoRA adapter at runtime.
#[derive(Debug, Clone)]
pub struct LoRALoadRequest {
    pub lora_path: String,
    pub scale: f64,
}

/// Download a GGUF model from HuggingFace Hub.
#[derive(Debug, Clone)]
pub struct ModelPullRequest {
    pub repo_id: String,
    pub filename: String,
}

/// Save model KV-cache state to disk.
#[derive(Debug, Clone)]
pub struct StateSaveRequest {
    pub slot_name: String,
}

/// Load model KV-cache state from disk.
#[derive(Debug, Clone)]
pub struct StateLoadRequest {
    pub slot_name: String,
}

/// Structured request passed to the adapter.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceRequest {
    pub prompt: String,
    pub system_prompt: Option<String>,
    pub temperature: f64,
    pub top_p: f64,
    pub max_tokens: i64,
    pub stream: bool,
    pub messages: Vec<HashMap<String, String>>,
    pub grammar: Option<String>,
    pub response_format: Option<HashMap<String, Box<dyn std::any::Any>>>,
    pub tools: Option<Vec<HashMap<String, Box<dyn std::any::Any>>>>,
    pub tool_choice: Option<Box<dyn std::any::Any>>,
    pub suffix: Option<String>,
    pub echo: bool,
    pub seed: Option<i64>,
    pub logprobs: Option<bool>,
    pub top_logprobs: Option<i64>,
    pub logit_bias: Option<HashMap<String, f64>>,
    pub top_k: Option<i64>,
    pub min_p: Option<f64>,
    pub repeat_penalty: Option<f64>,
    pub frequency_penalty: f64,
    pub presence_penalty: f64,
}
