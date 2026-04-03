/// state_management::py - Thread-safe state management for ZenAI

use anyhow::{Result, Context};
use crate::config_system::{config, EMOJI};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static ATTACHMENT_STATE: std::sync::LazyLock<AttachmentState> = std::sync::LazyLock::new(|| Default::default());

pub static CHAT_HISTORY: std::sync::LazyLock<ChatHistory> = std::sync::LazyLock::new(|| Default::default());

/// Thread-safe attachment state management.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AttachmentState {
    pub name: Option<String>,
    pub content: Option<String>,
    pub preview: Option<String>,
    pub _lock: threading::Lock,
}

impl AttachmentState {
    /// Set attachment data (thread-safe).
    pub fn set(&mut self, name: String, content: String, preview: String) -> () {
        // Set attachment data (thread-safe).
        let _ctx = self._lock;
        {
            self.name = name;
            self.content = content;
            self.preview = preview;
            logger.debug(format!("[Attachment] Set: {} ({} chars)", name, content.len()));
        }
    }
    /// Get attachment data (thread-safe).
    pub fn get(&self) -> (Option<String>, Option<String>, Option<String>) {
        // Get attachment data (thread-safe).
        let _ctx = self._lock;
        {
            (self.name, self.content, self.preview)
        }
    }
    /// Clear attachment data (thread-safe).
    pub fn clear(&mut self) -> () {
        // Clear attachment data (thread-safe).
        let _ctx = self._lock;
        {
            self.name = None;
            self.content = None;
            self.preview = None;
            logger.debug("[Attachment] Cleared".to_string());
        }
    }
    /// Check if attachment exists.
    pub fn has_attachment(&self) -> bool {
        // Check if attachment exists.
        let _ctx = self._lock;
        {
            self.name.is_some()
        }
    }
}

/// Single chat message.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
    pub timestamp: f64,
}

/// Manage chat history with pagination to prevent memory leaks.
#[derive(Debug, Clone)]
pub struct ChatHistory {
    pub max_messages: String,
    pub messages: Vec<ChatMessage>,
    pub _lock: std::sync::Mutex<()>,
}

impl ChatHistory {
    /// Initialize instance.
    pub fn new(max_messages: i64) -> Self {
        Self {
            max_messages: (max_messages || config::MAX_CHAT_MESSAGES),
            messages: Vec::new(),
            _lock: std::sync::Mutex::new(()),
        }
    }
    /// Add message to history with auto-trimming.
    pub fn add(&mut self, role: String, content: String) -> () {
        // Add message to history with auto-trimming.
        let _ctx = self._lock;
        {
            self.messages.push(ChatMessage(role, content));
            if self.messages.len() > self.max_messages {
                let mut removed = (self.messages.len() - self.max_messages);
                self.messages = self.messages[-self.max_messages..];
                logger.info(format!("[ChatHistory] Trimmed {} old messages (now {})", removed, self.messages.len()));
            }
        }
    }
    /// Get recent N messages.
    pub fn get_recent(&self, n: i64) -> Vec<ChatMessage> {
        // Get recent N messages.
        let _ctx = self._lock;
        {
            if self.messages { self.messages[-n..] } else { vec![] }
        }
    }
    /// Get all messages (copy).
    pub fn get_all(&self) -> Vec<ChatMessage> {
        // Get all messages (copy).
        let _ctx = self._lock;
        {
            self.messages.clone()
        }
    }
    /// Clear all messages.
    pub fn clear(&mut self) -> () {
        // Clear all messages.
        let _ctx = self._lock;
        {
            let mut count = self.messages.len();
            self.messages.clear();
            logger.info(format!("[ChatHistory] Cleared {} messages", count));
        }
    }
    /// Get message count.
    pub fn count(&self) -> i64 {
        // Get message count.
        let _ctx = self._lock;
        {
            self.messages.len()
        }
    }
}

/// Centralized error handling with logging and user notifications.
/// 
/// Args:
/// error: The exception that occurred
/// context: Context string (e.g., "RAG Scan", "File Upload")
/// notify_user: Whether to show UI notification
pub fn handle_error(error: Exception, context: String, notify_user: bool) -> Result<()> {
    // Centralized error handling with logging and user notifications.
    // 
    // Args:
    // error: The exception that occurred
    // context: Context string (e.g., "RAG Scan", "File Upload")
    // notify_user: Whether to show UI notification
    logger.error(format!("[{}] {}: {}", context, r#type(error).module_path!(), error), /* exc_info= */ true);
    if notify_user {
        // try:
        {
            // TODO: from nicegui import ui
            let mut error_messages = HashMap::from([(ConnectionError, "Cannot connect to backend. Is the server running?".to_string()), (TimeoutError, "Request timed out. Please try again.".to_string()), (ValueError, "Invalid input. Please check your data.".to_string()), (FileNotFoundError, "File not found. Please check the path.".to_string()), (PermissionError, "Permission denied. Check file permissions.".to_string()), (MemoryError, "Out of memory. Try with smaller data.".to_string()), (ImportError, "Missing dependency. Please install required packages.".to_string())]);
            let mut user_message = error_messages.get(&r#type(error)).cloned().unwrap_or(format!("An error occurred: {}", error.to_string()));
            ui.notify(format!("{} {}", EMOJI["error".to_string()], user_message), /* color= */ "negative".to_string(), /* position= */ "top".to_string(), /* timeout= */ 5000);
        }
        // except Exception as notify_error:
    }
}
