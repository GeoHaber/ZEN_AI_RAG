use anyhow::{Result, Context};
use crate::base::{BaseZenHandler};
use crate::config_system::{config};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Namespace for chat-related request handling.
#[derive(Debug, Clone)]
pub struct ChatHandler {
}

impl ChatHandler {
    /// Routing for POST requests related to chat.
    pub fn handle_post(handler: BaseZenHandler) -> Result<()> {
        // Routing for POST requests related to chat.
        if handler.path == "/api/chat".to_string() {
            let mut params = handler.parse_json_body();
            let mut user_msg = params.get(&"message".to_string()).cloned().unwrap_or("".to_string());
            if !user_msg {
                handler.send_json_response(400, HashMap::from([("error".to_string(), "Missing message".to_string())]));
                true
            }
            // try:
            {
                // TODO: from zena_mode.server import MODEL_PATH
                let mut payload = HashMap::from([("model".to_string(), MODEL_PATH.name), ("messages".to_string(), vec![HashMap::from([("role".to_string(), "system".to_string()), ("content".to_string(), "You are ZenAI, a helpful assistant. Keep answers short.".to_string())]), HashMap::from([("role".to_string(), "user".to_string()), ("content".to_string(), user_msg)])]), ("stream".to_string(), false), ("max_tokens".to_string(), 150)]);
                let mut resp = /* reqwest::post( */config::get_api_url(), /* json= */ payload, /* timeout= */ 30);
                if resp.status_code == 200 {
                    let mut llm_data = resp.json();
                    let mut content = llm_data["choices".to_string()][0]["message".to_string()]["content".to_string()];
                    handler.send_json_response(200, HashMap::from([("response".to_string(), content), ("emotion".to_string(), "neutral".to_string())]));
                } else {
                    handler.send_json_response(500, HashMap::from([("error".to_string(), format!("LLM Error: {}", resp.text))]));
                }
            }
            // except Exception as e:
            true
        }
        Ok(false)
    }
}
