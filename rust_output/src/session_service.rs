/// Session Service — Conversation Management.
/// 
/// Responsibility: Manage conversation history and context.
/// - Create sessions
/// - Add messages
/// - Track conversation state
/// - Persist history to disk
/// 
/// Pure Python, type hinted, fully testable.
/// Adapted from RAG_RAT/Core/services/session_service::py.

use anyhow::{Result, Context};
use crate::exceptions::{ValidationError};
use std::collections::HashMap;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Service for session management.
/// 
/// Pure business logic — no UI dependencies.
#[derive(Debug, Clone)]
pub struct SessionService {
    pub storage_dir: PathBuf,
    pub _active_sessions: HashMap<String, HashMap<String, Box<dyn std::any::Any>>>,
}

impl SessionService {
    pub fn new(storage_dir: Option<PathBuf>) -> Self {
        Self {
            storage_dir: PathBuf::from(storage_dir),
            _active_sessions: HashMap::new(),
        }
    }
    /// Create a new session.
    pub fn create_session(&mut self, user_id: Option<String>) -> HashMap<String, Box<dyn std::any::Any>> {
        // Create a new session.
        let mut session_id = /* uuid */ "00000000-0000-0000-0000-000000000000".to_string().to_string();
        let mut session = HashMap::from([("id".to_string(), session_id), ("user_id".to_string(), (user_id || "anonymous".to_string())), ("created_at".to_string(), datetime::now().isoformat()), ("updated_at".to_string(), datetime::now().isoformat()), ("messages".to_string(), vec![]), ("metadata".to_string(), HashMap::new())]);
        self._active_sessions[session_id] = session;
        self._save_session(session);
        logger.info(format!("✓ Created session: {}", session_id));
        session
    }
    /// Add a message to a session.
    pub fn add_message(&mut self, session_id: String, role: String, content: String, metadata: Option<HashMap<String, Box<dyn std::any::Any>>>) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
        // Add a message to a session.
        if !session_id {
            return Err(anyhow::anyhow!("ValidationError('Session ID is required', field='session_id')"));
        }
        if !("user".to_string(), "assistant".to_string(), "system".to_string()).contains(&role) {
            return Err(anyhow::anyhow!("ValidationError(f'Invalid role: {role}', field='role')"));
        }
        if (!content || !content.trim().to_string()) {
            return Err(anyhow::anyhow!("ValidationError('Content cannot be empty', field='content')"));
        }
        let mut session = self._get_or_load(session_id);
        let mut msg = HashMap::from([("role".to_string(), role), ("content".to_string(), content), ("timestamp".to_string(), datetime::now().isoformat()), ("metadata".to_string(), (metadata || HashMap::new()))]);
        session["messages".to_string()].push(msg);
        session["updated_at".to_string()] = datetime::now().isoformat();
        self._save_session(session);
        Ok(msg)
    }
    /// Get the last *limit* messages for a session.
    pub fn get_history(&mut self, session_id: String, limit: i64) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Get the last *limit* messages for a session.
        let mut session = self._get_or_load(session_id);
        session["messages".to_string()][-limit..]
    }
    /// Clear all messages in a session.
    pub fn clear_session(&mut self, session_id: String) -> bool {
        // Clear all messages in a session.
        let mut session = self._get_or_load(session_id);
        session["messages".to_string()] = vec![];
        session["updated_at".to_string()] = datetime::now().isoformat();
        self._save_session(session);
        self._active_sessions.remove(&session_id).unwrap_or(None);
        logger.info(format!("✓ Cleared session: {}", session_id));
        true
    }
    /// List all sessions (summaries only).
    pub fn list_sessions(&mut self) -> Result<Vec<HashMap<String, Box<dyn std::any::Any>>>> {
        // List all sessions (summaries only).
        let mut summaries = vec![];
        for path in self.storage_dir.glob("*.json".to_string()).iter() {
            // try:
            {
                let mut data = serde_json::from_str(&path.read_to_string())).unwrap();
                summaries.push(HashMap::from([("id".to_string(), data.get(&"id".to_string()).cloned()), ("user_id".to_string(), data.get(&"user_id".to_string()).cloned()), ("created_at".to_string(), data.get(&"created_at".to_string()).cloned()), ("updated_at".to_string(), data.get(&"updated_at".to_string()).cloned()), ("message_count".to_string(), data.get(&"messages".to_string()).cloned().unwrap_or(vec![]).len())]));
            }
            // except Exception as _e:
        }
        Ok(summaries)
    }
    pub fn _get_or_load(&mut self, session_id: String) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
        if self._active_sessions.contains(&session_id) {
            self._active_sessions[&session_id]
        }
        let mut path = (self.storage_dir / format!("{}.json", session_id));
        if path.exists() {
            // try:
            {
                let mut session = serde_json::from_str(&path.read_to_string())).unwrap();
            }
            // except json::JSONDecodeError as _e:
            self._active_sessions[session_id] = session;
            session
        }
        return Err(anyhow::anyhow!("ValidationError(f'Session not found: {session_i}', field='session_id')"));
    }
    pub fn _save_session(&mut self, session: HashMap<String, Box<dyn std::any::Any>>) -> () {
        let mut path = (self.storage_dir / format!("{}.json", session["id".to_string()]));
        pathstd::fs::write(&serde_json::to_string(&session).unwrap(), /* encoding= */ "utf-8".to_string());
    }
}
