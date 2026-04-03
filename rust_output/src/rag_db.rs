/// rag_db::py - SQLite storage for RAG documents and chunks.
/// Replaces monolithic JSON for scalability.

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// RAGDatabase class.
#[derive(Debug, Clone)]
pub struct RAGDatabase {
    pub db_path: String,
    pub conn: Option<serde_json::Value>,
    pub _lock: std::sync::Mutex<()>,
}

impl RAGDatabase {
    /// Initialize instance.
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
        self.db_path.parent().unwrap_or(std::path::Path::new("")).create_dir_all();
        self.conn = /* sqlite3 */ self.db_path, /* check_same_thread= */ false;
        self.conn.row_factory = sqlite3::Row;
        let _ctx = self.conn;
        {
            self.conn.execute("\n                CREATE TABLE IF NOT EXISTS documents (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    url TEXT UNIQUE,\n                    title TEXT,\n                    content_hash TEXT,\n                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n                )\n            ".to_string());
            self.conn.execute("\n                CREATE TABLE IF NOT EXISTS chunks (\n                    id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    doc_id INTEGER,\n                    chunk_index INTEGER,\n                    text TEXT,\n                    vector BLOB, -- Numpy float32 array as bytes\n                    metadata TEXT, \n                    FOREIGN KEY(doc_id) REFERENCES documents(id)\n                )\n            ".to_string());
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_hash ON documents(content_hash)".to_string());
        }
    }
    pub fn close(&self) -> () {
        if self.conn {
            self.conn.close();
        }
    }
    pub fn document_exists(&mut self, content_hash: String) -> bool {
        let _ctx = self._lock;
        {
            let mut cursor = self.conn.execute("SELECT 1 FROM documents WHERE content_hash = ?".to_string(), (content_hash));
            cursor.fetchone().is_some()
        }
    }
    /// Insert document and return ID. Returns existing ID if duplicate URL.
    pub fn add_document(&mut self, url: String, title: String, content: String) -> i64 {
        // Insert document and return ID. Returns existing ID if duplicate URL.
        let _ctx = self._lock;
        {
            let mut cursor = self.conn.execute("SELECT id FROM documents WHERE url = ?".to_string(), (url));
            let mut row = cursor.fetchone();
            if row {
                row["id".to_string()]
            }
            let mut content_hash = hashlib::sha256(content.as_bytes().to_vec()).hexdigest();
            let _ctx = self.conn;
            {
                let mut cursor = self.conn.execute("INSERT INTO documents (url, title, content_hash) VALUES (?, ?, ?)".to_string(), (url, title, content_hash));
                cursor.lastrowid
            }
        }
    }
    /// Batch insert chunks efficiently.
    /// chunks structure: [{'doc_id': int, 'text': str, 'vector': numpy.ndarray, 'chunk_index': int, 'metadata': dict}, ...]
    pub fn add_chunks(&mut self, chunks: Vec<HashMap>) -> Result<()> {
        // Batch insert chunks efficiently.
        // chunks structure: [{'doc_id': int, 'text': str, 'vector': numpy.ndarray, 'chunk_index': int, 'metadata': dict}, ...]
        if !chunks {
            return;
        }
        let _ctx = self._lock;
        {
            let mut data = vec![];
            for c in chunks.iter() {
                let mut vector_blob = if c.get(&"vector".to_string()).cloned().is_some() { c["vector".to_string()].tobytes() } else { None };
                let mut meta_json = serde_json::to_string(&c.get(&"metadata".to_string()).cloned().unwrap_or(HashMap::new())).unwrap();
                data.push((c.get(&"doc_id".to_string()).cloned().unwrap_or(0), c.get(&"chunk_index".to_string()).cloned().unwrap_or(0), c["text".to_string()], vector_blob, meta_json));
            }
            // try:
            {
                let _ctx = self.conn;
                {
                    self.conn.executemany("INSERT INTO chunks (doc_id, chunk_index, text, vector, metadata) VALUES (?, ?, ?, ?, ?)".to_string(), data);
                }
            }
            // except sqlite3::Error as e:
        }
    }
    /// Get total number of chunks in database.
    pub fn count_chunks(&mut self) -> i64 {
        // Get total number of chunks in database.
        let _ctx = self._lock;
        {
            let mut cursor = self.conn.execute("SELECT COUNT(*) as count FROM chunks".to_string());
            let mut row = cursor.fetchone();
            if row { row["count".to_string()] } else { 0 }
        }
    }
    /// Retrieve all chunks for building FAISS index.
    pub fn get_all_chunks(&mut self) -> Result<Vec<HashMap>> {
        // Retrieve all chunks for building FAISS index.
        let _ctx = self._lock;
        {
            let mut cursor = self.conn.execute("\n                SELECT c.id, c.text, c.vector, c.metadata, d.url, d.title\n                FROM chunks c\n                JOIN documents d ON c.doc_id = d.id\n            ".to_string());
        }
        let mut results = vec![];
        for row in cursor.iter() {
            let mut vec_bytes = row["vector".to_string()];
            let mut vector = if vec_bytes { numpy.frombuffer(vec_bytes, /* dtype= */ numpy.float32) } else { None };
            // try:
            {
                let mut meta = if row["metadata".to_string()] { serde_json::from_str(&row["metadata".to_string()]).unwrap() } else { HashMap::new() };
            }
            // except json::JSONDecodeError as _e:
            results.push(HashMap::from([("chunk_id".to_string(), row["id".to_string()]), ("text".to_string(), row["text".to_string()]), ("vector".to_string(), vector), ("url".to_string(), row["url".to_string()]), ("title".to_string(), row["title".to_string()])]));
        }
        Ok(results)
    }
    pub fn get_chunk_text(&mut self, chunk_id: i64) -> String {
        let mut cursor = self.conn.execute("SELECT text FROM chunks WHERE id = ?".to_string(), (chunk_id));
        let mut row = cursor.fetchone();
        if row { row["text".to_string()] } else { "".to_string() }
    }
    /// Clear all documents and chunks from database (DESTRUCTIVE).
    /// 
    /// WHAT:
    /// - Purpose: Remove all indexed data
    /// - Returns: None
    /// - Side effects: Deletes all rows from documents and chunks tables
    /// 
    /// WHY:
    /// - Use case: Remove junk/test data from index
    /// - Problem solved: Clean slate for re-indexing
    /// - Safety: Irreversible operation
    /// 
    /// HOW:
    /// 1. Delete all chunks
    /// 2. Delete all documents
    /// 3. Reset autoincrement counters
    /// - Thread-safe with lock
    pub fn clear_all(&mut self) -> () {
        // Clear all documents and chunks from database (DESTRUCTIVE).
        // 
        // WHAT:
        // - Purpose: Remove all indexed data
        // - Returns: None
        // - Side effects: Deletes all rows from documents and chunks tables
        // 
        // WHY:
        // - Use case: Remove junk/test data from index
        // - Problem solved: Clean slate for re-indexing
        // - Safety: Irreversible operation
        // 
        // HOW:
        // 1. Delete all chunks
        // 2. Delete all documents
        // 3. Reset autoincrement counters
        // - Thread-safe with lock
        let _ctx = self._lock;
        let _ctx = self.conn;
        {
            self.conn.execute("DELETE FROM chunks".to_string());
            self.conn.execute("DELETE FROM documents".to_string());
            self.conn.execute("DELETE FROM sqlite_sequence WHERE name='chunks'".to_string());
            self.conn.execute("DELETE FROM sqlite_sequence WHERE name='documents'".to_string());
            logger.info("[DB] All documents and chunks cleared".to_string());
        }
    }
}
