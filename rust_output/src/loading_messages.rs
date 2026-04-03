/// ui/loading_messages::py - Fun loading messages for chat interface

use anyhow::{Result, Context};

pub static WAITING_FOR_USER: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static LLM_THINKING: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static RAG_THINKING: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static SWARM_THINKING: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

/// Get a random waiting-for-user message.
pub fn get_waiting_message() -> String {
    // Get a random waiting-for-user message.
    random.choice(WAITING_FOR_USER)
}

/// Get a random thinking message based on context.
/// 
/// Args:
/// use_rag: Whether RAG is being used
/// use_swarm: Whether swarm mode is active
/// 
/// Returns:
/// Random appropriate message
pub fn get_thinking_message(use_rag: bool, use_swarm: bool) -> String {
    // Get a random thinking message based on context.
    // 
    // Args:
    // use_rag: Whether RAG is being used
    // use_swarm: Whether swarm mode is active
    // 
    // Returns:
    // Random appropriate message
    if use_swarm {
        random.choice(SWARM_THINKING)
    } else if use_rag {
        random.choice(RAG_THINKING)
    } else {
        random.choice(LLM_THINKING)
    }
}

/// Get a random spinner icon.
pub fn get_spinner_icon() -> String {
    // Get a random spinner icon.
    let mut spinners = vec!["⏳".to_string(), "⌛".to_string(), "🔄".to_string(), "⚡".to_string(), "✨".to_string(), "🌟".to_string(), "💫".to_string(), "🎯".to_string()];
    random.choice(spinners)
}
