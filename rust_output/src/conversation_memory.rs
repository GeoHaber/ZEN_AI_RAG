/// conversation_memory::py - Lightweight Conversation History RAG
/// 
/// Keeps chat history separate from the main knowledge RAG to:
/// - Maintain conversation context across sessions
/// - Use LLM to summarize/compress old conversations
/// - Enable "remember what we discussed" queries
/// - Not pollute the main knowledge base
/// 
/// Architecture:
/// - Separate SQLite DB (conversation.db)
/// - Rolling window of recent messages (configurable)
/// - LLM-based summarization for older context
/// - Semantic search for relevant past conversations

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Configuration for conversation memory.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryConfig {
    pub RECENT_WINDOW: i64,
    pub MAX_CONTEXT_TOKENS: i64,
    pub SUMMARIZE_THRESHOLD: i64,
    pub DEFAULT_HISTORY_TURNS: i64,
    pub EMBEDDING_MODEL: String,
    pub RELEVANCE_THRESHOLD: f64,
}

/// Single conversation message.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: String,
    pub content: String,
    pub timestamp: datetime,
    pub session_id: String,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl Message {
    pub fn to_dict(&self) -> HashMap {
        HashMap::from([("role".to_string(), self.role), ("content".to_string(), self.content), ("timestamp".to_string(), self.timestamp.isoformat()), ("session_id".to_string(), self.session_id), ("metadata".to_string(), self.metadata)])
    }
    pub fn from_dict(data: HashMap) -> () {
        cls(/* role= */ data["role".to_string()], /* content= */ data["content".to_string()], /* timestamp= */ if data.contains(&"timestamp".to_string()) { datetime::fromisoformat(data["timestamp".to_string()]) } else { datetime::now() }, /* session_id= */ data.get(&"session_id".to_string()).cloned().unwrap_or("default".to_string()), /* metadata= */ data.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new()))
    }
}

/// Compressed summary of older conversations.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationSummary {
    pub summary_text: String,
    pub start_time: datetime,
    pub end_time: datetime,
    pub message_count: i64,
    pub topics: Vec<String>,
}

impl ConversationSummary {
    pub fn to_dict(&self) -> HashMap {
        HashMap::from([("summary_text".to_string(), self.summary_text), ("start_time".to_string(), self.start_time.isoformat()), ("end_time".to_string(), self.end_time.isoformat()), ("message_count".to_string(), self.message_count), ("topics".to_string(), self.topics)])
    }
}

/// SQLite storage for conversation history.
#[derive(Debug, Clone)]
pub struct ConversationDB {
    pub db_path: String,
    pub conn: Option<serde_json::Value>,
    pub _lock: std::sync::Mutex<()>,
}

impl ConversationDB {
    pub fn new(db_path: PathBuf) -> Self {
        Self {
            db_path,
            conn: None,
            _lock: std::sync::Mutex::new(()),
        }
    }
    /// Initialize database schema.
    pub fn _init_db(&mut self) -> Result<()> {
        // Initialize database schema.
        self.conn = /* sqlite3 */ self.db_path.to_string(, /* check_same_thread= */ false);
        self.conn.row_factory = sqlite3::Row;
        let _ctx = self.conn;
        {
            self.conn.execute("\n                CREATE TABLE IF NOT EXISTS messages (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    session_id TEXT NOT NULL,\n                    role TEXT NOT NULL,\n                    content TEXT NOT NULL,\n                    timestamp TEXT NOT NULL,\n                    vector BLOB,\n                    metadata TEXT DEFAULT '{}',\n                    summarized INTEGER DEFAULT 0\n                )\n            ".to_string());
            self.conn.execute("\n                CREATE TABLE IF NOT EXISTS summaries (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    session_id TEXT NOT NULL,\n                    summary_text TEXT NOT NULL,\n                    start_time TEXT NOT NULL,\n                    end_time TEXT NOT NULL,\n                    message_count INTEGER,\n                    topics TEXT DEFAULT '[]',\n                    vector BLOB,\n                    created_at TEXT DEFAULT CURRENT_TIMESTAMP\n                )\n            ".to_string());
            self.conn.execute("\n                CREATE TABLE IF NOT EXISTS sessions (\n                    id TEXT PRIMARY KEY,\n                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,\n                    last_active TEXT,\n                    metadata TEXT DEFAULT '{}'\n                )\n            ".to_string());
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)".to_string());
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)".to_string());
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_summaries_session ON summaries(session_id)".to_string());
        }
    }
    /// Add a message to the database.
    pub fn add_message(&mut self, msg: Message, vector: Option<serde_json::Value>) -> i64 {
        // Add a message to the database.
        let _ctx = self._lock;
        {
            let mut vector_blob = if vector.is_some() { vector.tobytes() } else { None };
            let mut cursor = self.conn.execute("\n                INSERT INTO messages (session_id, role, content, timestamp, vector, metadata)\n                VALUES (?, ?, ?, ?, ?, ?)\n            ".to_string(), (msg.session_id, msg.role, msg.content, msg.timestamp.isoformat(), vector_blob, serde_json::to_string(&msg.metadata).unwrap()));
            self.conn.commit();
            cursor.lastrowid
        }
    }
    /// Get recent messages for a session.
    pub fn get_recent_messages(&mut self, session_id: String, limit: i64) -> Vec<Message> {
        // Get recent messages for a session.
        let _ctx = self._lock;
        {
            let mut cursor = self.conn.execute("\n                SELECT * FROM messages \n                WHERE session_id = ? AND summarized = 0\n                ORDER BY timestamp DESC\n                LIMIT ?\n            ".to_string(), (session_id, limit));
            let mut rows = cursor.fetchall();
            let mut messages = vec![];
            for row in rows.iter().rev().iter() {
                messages.push(Message(/* role= */ row["role".to_string()], /* content= */ row["content".to_string()], /* timestamp= */ datetime::fromisoformat(row["timestamp".to_string()]), /* session_id= */ row["session_id".to_string()], /* metadata= */ if row["metadata".to_string()] { serde_json::from_str(&row["metadata".to_string()]).unwrap() } else { HashMap::new() }));
            }
            messages
        }
    }
    /// Count messages not yet summarized.
    pub fn get_unsummarized_count(&mut self, session_id: String) -> i64 {
        // Count messages not yet summarized.
        let _ctx = self._lock;
        {
            let mut cursor = self.conn.execute("\n                SELECT COUNT(*) FROM messages \n                WHERE session_id = ? AND summarized = 0\n            ".to_string(), (session_id));
            cursor.fetchone()[0]
        }
    }
    /// Mark older messages as summarized.
    pub fn mark_as_summarized(&mut self, session_id: String, before_timestamp: datetime) -> () {
        // Mark older messages as summarized.
        let _ctx = self._lock;
        {
            self.conn.execute("\n                UPDATE messages \n                SET summarized = 1\n                WHERE session_id = ? AND timestamp < ?\n            ".to_string(), (session_id, before_timestamp.isoformat()));
            self.conn.commit();
        }
    }
    /// Store a conversation summary.
    pub fn add_summary(&mut self, session_id: String, summary: ConversationSummary, vector: Option<serde_json::Value>) -> i64 {
        // Store a conversation summary.
        let _ctx = self._lock;
        {
            let mut vector_blob = if vector.is_some() { vector.tobytes() } else { None };
            let mut cursor = self.conn.execute("\n                INSERT INTO summaries (session_id, summary_text, start_time, end_time, \n                                      message_count, topics, vector)\n                VALUES (?, ?, ?, ?, ?, ?, ?)\n            ".to_string(), (session_id, summary.summary_text, summary.start_time.isoformat(), summary.end_time.isoformat(), summary.message_count, serde_json::to_string(&summary.topics).unwrap(), vector_blob));
            self.conn.commit();
            cursor.lastrowid
        }
    }
    /// Get all message vectors for FAISS index building.
    pub fn get_all_vectors(&mut self, session_id: String) -> Vec<(i64, np::ndarray, String)> {
        // Get all message vectors for FAISS index building.
        let _ctx = self._lock;
        {
            let mut cursor = self.conn.execute("\n                SELECT id, vector, content FROM messages \n                WHERE session_id = ? AND vector IS NOT NULL\n            ".to_string(), (session_id));
            let mut results = vec![];
            for row in cursor.iter() {
                if row["vector".to_string()] {
                    let mut vec = np.frombuffer(row["vector".to_string()], /* dtype= */ np.float32);
                    results.push((row["id".to_string()], vec, row["content".to_string()]));
                }
            }
            results
        }
    }
    /// Get all summaries for a session.
    pub fn get_summaries(&mut self, session_id: String) -> Vec<ConversationSummary> {
        // Get all summaries for a session.
        let _ctx = self._lock;
        {
            let mut cursor = self.conn.execute("\n                SELECT * FROM summaries \n                WHERE session_id = ?\n                ORDER BY end_time DESC\n            ".to_string(), (session_id));
            cursor.iter().map(|row| ConversationSummary(/* summary_text= */ row["summary_text".to_string()], /* start_time= */ datetime::fromisoformat(row["start_time".to_string()]), /* end_time= */ datetime::fromisoformat(row["end_time".to_string()]), /* message_count= */ row["message_count".to_string()], /* topics= */ if row["topics".to_string()] { serde_json::from_str(&row["topics".to_string()]).unwrap() } else { vec![] })).collect::<Vec<_>>()
        }
    }
    pub fn close(&self) -> () {
        if self.conn {
            self.conn.close();
        }
    }
}

/// Main class for managing conversation history with semantic search.
/// 
/// Features:
/// - Stores messages with embeddings for semantic retrieval
/// - Auto-summarizes old conversations using LLM
/// - Provides context for follow-up questions
/// - Separate from main RAG to avoid pollution
/// 
/// Usage:
/// memory = ConversationMemory(cache_dir=Path("conv_cache"))
/// 
/// # Add messages
/// memory.add_message("user", "What is Python?", session_id="user123")
/// memory.add_message("assistant", "Python is a programming language...", session_id="user123")
/// 
/// # Get context for new query
/// context = memory.get_relevant_context("Tell me more about Python", session_id="user123")
/// 
/// # Build prompt with history
/// prompt = memory.build_contextual_prompt("How do I install packages?", session_id="user123")
#[derive(Debug, Clone)]
pub struct ConversationMemory {
    pub config: String,
    pub cache_dir: String,
    pub db: ConversationDB,
    pub model: SentenceTransformer,
    pub embedding_dim: String /* self.model.get_sentence_embedding_dimension */,
    pub _indexes: HashMap<String, faiss::IndexFlatIP>,
    pub _index_data: HashMap<String, Vec<(i64, String)>>,
    pub _recent_cache: HashMap<String, deque>,
    pub _lock: std::sync::Mutex<()>,
}

impl ConversationMemory {
    pub fn new(cache_dir: Option<PathBuf>, config: Option<MemoryConfig>) -> Self {
        Self {
            config: (config || MemoryConfig()),
            cache_dir: (cache_dir || PathBuf::from("conversation_cache".to_string())),
            db: ConversationDB((self.cache_dir / "conversation.db".to_string())),
            model: SentenceTransformer(self.config::EMBEDDING_MODEL),
            embedding_dim: self.model.get_sentence_embedding_dimension(),
            _indexes: HashMap::new(),
            _index_data: HashMap::new(),
            _recent_cache: HashMap::new(),
            _lock: std::sync::Mutex::new(()),
        }
    }
    /// Get or create FAISS index for a session.
    pub fn _get_or_create_index(&mut self, session_id: String) -> (faiss::IndexFlatIP, Vec) {
        // Get or create FAISS index for a session.
        if !self._indexes.contains(&session_id) {
            self._indexes[session_id] = faiss.IndexFlatIP(self.embedding_dim);
            self._index_data[session_id] = vec![];
            let mut vectors_data = self.db.get_all_vectors(session_id);
            if vectors_data {
                let mut vectors = np.vstack(vectors_data.iter().map(|v| v[1]).collect::<Vec<_>>()).astype("float32".to_string());
                faiss.normalize_L2(vectors);
                self._indexes[&session_id].insert(vectors);
                self._index_data[session_id] = vectors_data.iter().map(|v| (v[0], v[2])).collect::<Vec<_>>();
            }
        }
        (self._indexes[&session_id], self._index_data[&session_id])
    }
    /// Add a message to conversation history.
    /// 
    /// Args:
    /// role: 'user', 'assistant', or 'system'
    /// content: Message text
    /// session_id: Session identifier (for multi-user support)
    /// metadata: Optional metadata (e.g., model used, response time)
    /// 
    /// Returns:
    /// Message ID
    pub fn add_message(&mut self, role: String, content: String, session_id: String, metadata: Option<HashMap>) -> i64 {
        // Add a message to conversation history.
        // 
        // Args:
        // role: 'user', 'assistant', or 'system'
        // content: Message text
        // session_id: Session identifier (for multi-user support)
        // metadata: Optional metadata (e.g., model used, response time)
        // 
        // Returns:
        // Message ID
        let _ctx = self._lock;
        {
            let mut msg = Message(/* role= */ role, /* content= */ content, /* timestamp= */ datetime::now(), /* session_id= */ session_id, /* metadata= */ (metadata || HashMap::new()));
            let mut embedding = self.model.encode(vec![content], /* convert_to_numpy= */ true, /* normalize_embeddings= */ true)[0].astype("float32".to_string());
            let mut msg_id = self.db.add_message(msg, embedding);
            let (mut index, mut data) = self._get_or_create_index(session_id);
            index.insert(embedding.reshape(1, -1));
            data.push((msg_id, content));
            if !self._recent_cache.contains(&session_id) {
                self._recent_cache[session_id] = deque(/* maxlen= */ self.config::RECENT_WINDOW);
            }
            self._recent_cache[&session_id].push(msg);
            logger.debug(format!("[ConvMemory] Added {} message to session {}", role, session_id));
            msg_id
        }
    }
    /// Get recent conversation history.
    /// 
    /// Args:
    /// session_id: Session identifier
    /// turns: Number of turns (user+assistant pairs) to return
    /// 
    /// Returns:
    /// List of Message objects in chronological order
    pub fn get_recent_history(&mut self, session_id: String, turns: Option<i64>) -> Vec<Message> {
        // Get recent conversation history.
        // 
        // Args:
        // session_id: Session identifier
        // turns: Number of turns (user+assistant pairs) to return
        // 
        // Returns:
        // List of Message objects in chronological order
        let mut turns = (turns || self.config::DEFAULT_HISTORY_TURNS);
        let mut limit = (turns * 2);
        if self._recent_cache.contains(&session_id) {
            let mut cached = self._recent_cache[&session_id].into_iter().collect::<Vec<_>>();
            if cached.len() >= limit {
                cached[-limit..]
            }
        }
        self.db.get_recent_messages(session_id, limit)
    }
    /// Semantic search over conversation history.
    /// 
    /// Args:
    /// query: Search query
    /// session_id: Session identifier
    /// k: Number of results
    /// 
    /// Returns:
    /// List of relevant messages with scores
    pub fn search_history(&mut self, query: String, session_id: String, k: i64) -> Vec<HashMap> {
        // Semantic search over conversation history.
        // 
        // Args:
        // query: Search query
        // session_id: Session identifier
        // k: Number of results
        // 
        // Returns:
        // List of relevant messages with scores
        let _ctx = self._lock;
        {
            let (mut index, mut data) = self._get_or_create_index(session_id);
            if index.ntotal == 0 {
                vec![]
            }
            let mut query_vec = self.model.encode(vec![query], /* convert_to_numpy= */ true, /* normalize_embeddings= */ true).astype("float32".to_string());
            let mut k = k.min(index.ntotal);
            let (mut similarities, mut indices) = index.search(query_vec, k);
            let mut results = vec![];
            for (sim, idx) in similarities[0].iter().zip(indices[0].iter()).iter() {
                if (idx >= 0 && idx < data.len() && sim >= self.config::RELEVANCE_THRESHOLD) {
                    let (mut msg_id, mut content) = data[&idx];
                    results.push(HashMap::from([("id".to_string(), msg_id), ("content".to_string(), content), ("score".to_string(), sim.to_string().parse::<f64>().unwrap_or(0.0))]));
                }
            }
            results
        }
    }
    /// Build context string from relevant history.
    /// 
    /// Combines:
    /// - Recent messages (for continuity)
    /// - Semantically relevant past messages (for topic recall)
    /// 
    /// Args:
    /// query: Current user query
    /// session_id: Session identifier
    /// include_recent: Include recent conversation turns
    /// include_search: Include semantically relevant history
    /// 
    /// Returns:
    /// Formatted context string
    pub fn get_relevant_context(&mut self, query: String, session_id: String, include_recent: bool, include_search: bool) -> String {
        // Build context string from relevant history.
        // 
        // Combines:
        // - Recent messages (for continuity)
        // - Semantically relevant past messages (for topic recall)
        // 
        // Args:
        // query: Current user query
        // session_id: Session identifier
        // include_recent: Include recent conversation turns
        // include_search: Include semantically relevant history
        // 
        // Returns:
        // Formatted context string
        let mut context_parts = vec![];
        if include_recent {
            let mut recent = self.get_recent_history(session_id, /* turns= */ 3);
            if recent {
                context_parts.push("=== Recent Conversation ===".to_string());
                for msg in recent.iter() {
                    let mut prefix = if msg.role == "user".to_string() { "User".to_string() } else { "Assistant".to_string() };
                    context_parts.push(format!("{}: {}", prefix, msg.content));
                }
            }
        }
        if include_search {
            let mut relevant = self.search_history(query, session_id, /* k= */ 3);
            let mut recent_contents = self.get_recent_history(session_id).iter().map(|m| m.content).collect::<HashSet<_>>();
            let mut relevant = relevant.iter().filter(|r| !recent_contents.contains(&r["content".to_string()])).map(|r| r).collect::<Vec<_>>();
            if relevant {
                context_parts.push("\n=== Relevant Past Context ===".to_string());
                for r in relevant.iter() {
                    context_parts.push(format!("(Relevance: {:.2}) {}...", r["score".to_string()], r["content".to_string()][..200]));
                }
            }
        }
        if context_parts { context_parts.join(&"\n".to_string()) } else { "".to_string() }
    }
    /// Build a prompt with conversation context.
    /// 
    /// Args:
    /// user_query: Current user question
    /// session_id: Session identifier
    /// system_prompt: Optional system prompt
    /// 
    /// Returns:
    /// Complete prompt with context
    pub fn build_contextual_prompt(&mut self, user_query: String, session_id: String, system_prompt: Option<String>) -> String {
        // Build a prompt with conversation context.
        // 
        // Args:
        // user_query: Current user question
        // session_id: Session identifier
        // system_prompt: Optional system prompt
        // 
        // Returns:
        // Complete prompt with context
        let mut context = self.get_relevant_context(user_query, session_id);
        let mut parts = vec![];
        if system_prompt {
            parts.push(format!("System: {}\n", system_prompt));
        }
        if context {
            parts.push(format!("Conversation Context:\n{}\n", context));
        }
        parts.push(format!("Current Question: {}", user_query));
        parts.join(&"\n".to_string())
    }
    /// Use LLM to summarize older messages (async).
    /// 
    /// Call this periodically to compress old history.
    /// 
    /// Args:
    /// session_id: Session identifier
    /// llm_backend: LLM backend with send_message_async method
    /// 
    /// Returns:
    /// ConversationSummary if summarization occurred, None otherwise
    pub async fn summarize_old_messages(&mut self, session_id: String, llm_backend: String) -> Option<ConversationSummary> {
        // Use LLM to summarize older messages (async).
        // 
        // Call this periodically to compress old history.
        // 
        // Args:
        // session_id: Session identifier
        // llm_backend: LLM backend with send_message_async method
        // 
        // Returns:
        // ConversationSummary if summarization occurred, None otherwise
        let mut count = self.db.get_unsummarized_count(session_id);
        if count < self.config::SUMMARIZE_THRESHOLD {
            logger.debug(format!("[ConvMemory] Only {} unsummarized messages, skipping", count));
            None
        }
        let mut all_messages = self.db.get_recent_messages(session_id, /* limit= */ count);
        let mut to_summarize = all_messages[..-self.config::RECENT_WINDOW];
        if !to_summarize {
            None
        }
        let mut conversation_text = to_summarize.iter().map(|m| format!("{}: {}", m.role.to_uppercase(), m.content)).collect::<Vec<_>>().join(&"\n".to_string());
        let mut summarize_prompt = format!("Summarize this conversation concisely, capturing:\n1. Main topics discussed\n2. Key decisions or conclusions\n3. Important information shared\n\nConversation:\n{}\n\nProvide a brief summary (2-3 paragraphs max):", conversation_text);
        let mut summary_text = "".to_string();
        // async for
        while let Some(chunk) = llm_backend::send_message_async(summarize_prompt).next().await {
            summary_text += chunk;
        }
        let mut topics = self._extract_topics(to_summarize);
        let mut summary = ConversationSummary(/* summary_text= */ summary_text.trim().to_string(), /* start_time= */ to_summarize[0].timestamp, /* end_time= */ to_summarize[-1].timestamp, /* message_count= */ to_summarize.len(), /* topics= */ topics);
        let mut summary_embedding = self.model.encode(vec![summary_text], /* convert_to_numpy= */ true, /* normalize_embeddings= */ true)[0].astype("float32".to_string());
        self.db.add_summary(session_id, summary, summary_embedding);
        self.db.mark_as_summarized(session_id, to_summarize[-1].timestamp);
        logger.info(format!("[ConvMemory] Summarized {} messages for session {}", to_summarize.len(), session_id));
        summary
    }
    /// Extract topic keywords from messages (simple implementation).
    pub fn _extract_topics(&self, messages: Vec<Message>) -> Vec<String> {
        // Extract topic keywords from messages (simple implementation).
        // TODO: from collections import Counter
        // TODO: import re
        let mut stop_words = HashSet::from(["the".to_string(), "a".to_string(), "an".to_string(), "is".to_string(), "are".to_string(), "was".to_string(), "were".to_string(), "be".to_string(), "been".to_string(), "being".to_string(), "have".to_string(), "has".to_string(), "had".to_string(), "do".to_string(), "does".to_string(), "did".to_string(), "will".to_string(), "would".to_string(), "could".to_string(), "should".to_string(), "may".to_string(), "might".to_string(), "must".to_string(), "shall".to_string(), "can".to_string(), "need".to_string(), "dare".to_string(), "to".to_string(), "of".to_string(), "in".to_string(), "for".to_string(), "on".to_string(), "with".to_string(), "at".to_string(), "by".to_string(), "from".to_string(), "as".to_string(), "into".to_string(), "through".to_string(), "during".to_string(), "before".to_string(), "after".to_string(), "above".to_string(), "below".to_string(), "between".to_string(), "under".to_string(), "again".to_string(), "further".to_string(), "then".to_string(), "once".to_string(), "here".to_string(), "there".to_string(), "when".to_string(), "where".to_string(), "why".to_string(), "how".to_string(), "all".to_string(), "each".to_string(), "few".to_string(), "more".to_string(), "most".to_string(), "other".to_string(), "some".to_string(), "such".to_string(), "no".to_string(), "nor".to_string(), "not".to_string(), "only".to_string(), "own".to_string(), "same".to_string(), "so".to_string(), "than".to_string(), "too".to_string(), "very".to_string(), "just".to_string(), "i".to_string(), "me".to_string(), "my".to_string(), "myself".to_string(), "we".to_string(), "our".to_string(), "you".to_string(), "your".to_string(), "he".to_string(), "she".to_string(), "it".to_string(), "they".to_string(), "them".to_string(), "what".to_string(), "which".to_string(), "who".to_string(), "this".to_string(), "that".to_string(), "these".to_string(), "and".to_string(), "but".to_string(), "if".to_string(), "or".to_string(), "because".to_string(), "as".to_string(), "until".to_string(), "while".to_string()]);
        let mut all_words = vec![];
        for msg in messages.iter() {
            let mut words = re::findall("\\b[a-zA-Z]{4,}\\b".to_string(), msg.content.to_lowercase());
            all_words.extend(words.iter().filter(|w| !stop_words.contains(&w)).map(|w| w).collect::<Vec<_>>());
        }
        let mut counter = Counter(all_words);
        counter.most_common(5).iter().map(|(word, _)| word).collect::<Vec<_>>()
    }
    /// Get memory statistics for a session.
    pub fn get_stats(&self, session_id: String) -> HashMap {
        // Get memory statistics for a session.
        HashMap::from([("total_messages".to_string(), self.db.get_unsummarized_count(session_id)), ("index_vectors".to_string(), if self._indexes.contains(&session_id) { self._indexes.get(&session_id).cloned().unwrap_or(faiss.IndexFlatIP(1)).ntotal } else { 0 }), ("summaries".to_string(), self.db.get_summaries(session_id).len()), ("cache_size".to_string(), self._recent_cache.get(&session_id).cloned().unwrap_or(vec![]).len()), ("embedding_model".to_string(), self.config::EMBEDDING_MODEL)])
    }
    /// Clear all data for a session.
    pub fn clear_session(&self, session_id: String) -> () {
        // Clear all data for a session.
        let _ctx = self._lock;
        {
            if self._indexes.contains(&session_id) {
                drop(self._indexes[session_id]);
                drop(self._index_data[session_id]);
            }
            if self._recent_cache.contains(&session_id) {
                drop(self._recent_cache[session_id]);
            }
            logger.info(format!("[ConvMemory] Cleared in-memory data for session {}", session_id));
        }
    }
}

/// Factory function to get a conversation memory instance.
pub fn get_conversation_memory(cache_dir: Option<PathBuf>) -> ConversationMemory {
    // Factory function to get a conversation memory instance.
    let mut default_dir = PathBuf::from("conversation_cache".to_string());
    ConversationMemory(/* cache_dir= */ (cache_dir || default_dir))
}
