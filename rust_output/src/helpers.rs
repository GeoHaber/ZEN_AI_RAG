/// Helper utilities shared across routers.
/// 
/// Extracted from api_server::py.

use anyhow::{Result, Context};
use crate::schemas::{ChatCompletionRequest, InferenceRequest};
use std::collections::HashMap;

/// Get the global ServerState — imported lazily to avoid circular deps.
pub fn get_state() -> () {
    // Get the global ServerState — imported lazily to avoid circular deps.
    // TODO: import api_server
    api_server::state
}

/// Get the global SwapTracker.
pub fn get_swap_tracker() -> () {
    // Get the global SwapTracker.
    // TODO: import api_server
    api_server::_swap_tracker
}

/// Get the raw Llama object (or None) — delegates to api_server::_get_llm for patchability.
pub fn get_llm() -> () {
    // Get the raw Llama object (or None) — delegates to api_server::_get_llm for patchability.
    // TODO: import api_server
    api_server::_get_llm()
}

/// Get the adapter that supports token streaming — delegates to api_server::_get_token_streamer.
pub fn get_token_streamer() -> () {
    // Get the adapter that supports token streaming — delegates to api_server::_get_token_streamer.
    // TODO: import api_server
    api_server::_get_token_streamer()
}

/// Estimate token count (~4 chars per token for English).
pub fn estimate_tokens(content: String) -> i64 {
    // Estimate token count (~4 chars per token for English).
    if /* /* isinstance(content, str) */ */ true {
        1.max((content.len() / 4))
    }
    if /* /* isinstance(content, list) */ */ true {
        let mut total = content.iter().map(|m| m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len()).collect::<Vec<_>>().iter().sum::<i64>();
        1.max((total / 4))
    }
    1
}

/// Build a standard chat::completion JSON response.
pub fn build_completion_json(request_id: String, text: String, completion_tokens: i64, prompt_tokens: i64, tool_calls: Option<Vec<HashMap>>) -> HashMap {
    // Build a standard chat::completion JSON response.
    let mut state = get_state();
    let mut message = HashMap::from([("role".to_string(), "assistant".to_string()), ("content".to_string(), text)]);
    let mut finish_reason = "stop".to_string();
    if tool_calls {
        message["tool_calls".to_string()] = tool_calls;
        let mut finish_reason = "tool_calls".to_string();
    }
    HashMap::from([("id".to_string(), request_id), ("object".to_string(), "chat::completion".to_string()), ("created".to_string(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64().to_string().parse::<i64>().unwrap_or(0)), ("model".to_string(), if state { state::model_id } else { "unknown".to_string() }), ("choices".to_string(), vec![HashMap::from([("index".to_string(), 0), ("message".to_string(), message), ("finish_reason".to_string(), finish_reason)])]), ("usage".to_string(), HashMap::from([("prompt_tokens".to_string(), prompt_tokens), ("completion_tokens".to_string(), completion_tokens), ("total_tokens".to_string(), (prompt_tokens + completion_tokens))]))])
}

/// Build a proper InferenceRequest from the HTTP request + messages.
pub fn build_inference_request(messages: Vec<HashMap>, req: ChatCompletionRequest) -> InferenceRequest {
    // Build a proper InferenceRequest from the HTTP request + messages.
    InferenceRequest(/* prompt= */ next(messages.iter().rev().iter().filter(|m| m["role".to_string()] == "user".to_string()).map(|m| m["content".to_string()]).collect::<Vec<_>>(), "".to_string()), /* system_prompt= */ next(messages.iter().filter(|m| m["role".to_string()] == "system".to_string()).map(|m| m["content".to_string()]).collect::<Vec<_>>(), None), /* temperature= */ req.temperature, /* top_p= */ req.top_p, /* max_tokens= */ (req.max_tokens || 2048), /* stream= */ req.stream, /* messages= */ messages, /* grammar= */ req.grammar, /* response_format= */ req.response_format, /* tools= */ /* getattr */ None, /* tool_choice= */ /* getattr */ None, /* seed= */ req.seed, /* logprobs= */ req.logprobs, /* top_logprobs= */ req.top_logprobs, /* logit_bias= */ req.logit_bias, /* top_k= */ /* getattr */ None, /* min_p= */ /* getattr */ None, /* repeat_penalty= */ /* getattr */ None, /* frequency_penalty= */ req.frequency_penalty, /* presence_penalty= */ req.presence_penalty)
}

/// Fallback: split text into token-like chunks for fake streaming.
pub fn tokenize_for_stream(text: String) -> Vec<String> {
    // Fallback: split text into token-like chunks for fake streaming.
    let mut tokens = vec![];
    let mut current = vec![];
    for ch in text.iter() {
        current.push(ch);
        if (" ".to_string(), "\n".to_string(), ".".to_string(), ",".to_string(), ";".to_string(), "!".to_string(), "?".to_string(), ":".to_string(), ")".to_string(), "]".to_string(), "}".to_string()).contains(&ch) {
            tokens.push(current.join(&"".to_string()));
            let mut current = vec![];
        } else if current.len() >= 5 {
            tokens.push(current.join(&"".to_string()));
            let mut current = vec![];
        }
    }
    if current {
        tokens.push(current.join(&"".to_string()));
    }
    tokens
}
