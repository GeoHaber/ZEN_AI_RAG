use anyhow::{Result, Context};
use regex::Regex;
use std::collections::HashMap;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// optimize local small model dispatcher.
/// Strategy:
/// - Level 0: Zero-latency Regex (Greetings, simple queries)
/// - Level 1: Intent Classification (needs RAG? needs Code?)
/// - Level 2: Routing to appropriate handler
#[derive(Debug, Clone)]
pub struct FastDispatcher {
    pub backend: String,
    pub rag_system: String,
}

impl FastDispatcher {
    pub fn new(backend: String, rag_system: String) -> Self {
        Self {
            backend,
            rag_system,
        }
    }
    /// Compile efficient regex patterns for Level 0.
    pub fn _compile_patterns(&mut self) -> () {
        // Compile efficient regex patterns for Level 0.
        self.fast_responses = HashMap::from([(regex::Regex::new(&"^(hi|hello|hey|greetings)$".to_string()).unwrap(), "Hello! How can I help you today? \n\nI'm ready for coding, analysis, or just a chat.".to_string()), (regex::Regex::new(&"^(thanks|thank you|thx)$".to_string()).unwrap(), "You're welcome! Let me know if you need anything else.".to_string()), (regex::Regex::new(&"^(who are you\\??)$".to_string()).unwrap(), "I am ZenAI, your local helpful assistant.".to_string()), (regex::Regex::new(&"^(date|time|what time is it\\??)$".to_string()).unwrap(), self._get_time_str)]);
    }
    pub fn _get_time_str(&self) -> () {
        // TODO: from datetime import datetime
        format!("It is currently {}.", datetime::now().strftime("%Y-%m-%d %H:%M:%S".to_string()))
    }
    /// Main entry point. Returns a dict explaining how to handle the prompt
    /// or providing a direct response.
    pub async fn dis/* mock::patch(&mut self, prompt: String, conversation_id: String) */ -> HashMap<String, Box<dyn std::any::Any>> {
        // Main entry point. Returns a dict explaining how to handle the prompt
        // or providing a direct response.
        for (pattern, response) in self.fast_responses.iter().iter() {
            if pattern.search(prompt.trim().to_string()) {
                if callable(response) {
                    HashMap::from([("type".to_string(), "direct".to_string()), ("content".to_string(), response())])
                }
                HashMap::from([("type".to_string(), "direct".to_string()), ("content".to_string(), response)])
            }
        }
        let mut lower_p = prompt.to_lowercase();
        if vec!["code".to_string(), "script".to_string(), "function".to_string(), "class".to_string(), "def ".to_string(), "import ".to_string(), "python".to_string(), "html".to_string()].iter().map(|w| lower_p.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            HashMap::from([("type".to_string(), "expert".to_string()), ("expert".to_string(), "code".to_string()), ("prompt".to_string(), prompt)])
        }
        if (self.rag_system && vec!["search".to_string(), "find".to_string(), "read".to_string(), "lookup".to_string(), "who".to_string(), "what".to_string()].iter().map(|w| lower_p.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v)) {
            HashMap::from([("type".to_string(), "rag".to_string()), ("prompt".to_string(), prompt)])
        }
        HashMap::from([("type".to_string(), "chat".to_string()), ("prompt".to_string(), prompt)])
    }
    /// Stream generator that internally routes based on dispatch logic.
    /// This replaces the direct backend call in the UI.
    pub async fn get_response_stream(&mut self, prompt: String, ui_state: String) -> () {
        // Stream generator that internally routes based on dispatch logic.
        // This replaces the direct backend call in the UI.
        let mut decision = self.dis/* mock::patch(prompt) */.await;
        logger.info(format!("⚡ Dispatch Decision: {}", decision["type".to_string()]));
        if decision["type".to_string()] == "direct".to_string() {
            /* yield decision["content".to_string()] */;
            return;
        } else if decision["type".to_string()] == "rag".to_string() {
            // pass
        }
        // async for
        while let Some(chunk) = self.backend.send_message_async(decision["prompt".to_string()]).next().await {
            /* yield chunk */;
        }
    }
}
