
"""
rag_db.py - SQLite storage for RAG documents and chunks.
Replaces monolithic JSON for scalability.
"""
import sqlite3
import hashlib
import json
import logging
import threading
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class RAGDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self._lock = threading.RLock()  # Thread-safe access
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        with self.conn:
            # Documents Table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    title TEXT,
                    content_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Chunks Table
            # chunk_metadata is a JSON string for flexibility
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER,
                    chunk_index INTEGER,
                    text TEXT,
                    vector BLOB, -- Numpy float32 array as bytes
                    metadata TEXT, 
                    FOREIGN KEY(doc_id) REFERENCES documents(id)
                )
            """)
            
            # Index for fast duplicate checks
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_hash ON documents(content_hash)")

    def close(self):
        if self.conn:
            self.conn.close()

    def document_exists(self, content_hash: str) -> bool:
        with self._lock:
            cursor = self.conn.execute("SELECT 1 FROM documents WHERE content_hash = ?", (content_hash,))
            return cursor.fetchone() is not None

    def add_document(self, url: str, title: str, content: str) -> int:
        """Insert document and return ID. Returns existing ID if duplicate URL."""
        with self._lock:
            # Check URL collision first
            cursor = self.conn.execute("SELECT id FROM documents WHERE url = ?", (url,))
            row = cursor.fetchone()
            if row:
                return row['id']
                
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # Check Content Hash collision (same content, different URL?)
            # For strict deduplication, we might want to skip. 
            # But RAG usually indexes everything. Let's just store.
            
            with self.conn:
                cursor = self.conn.execute(
                    "INSERT INTO documents (url, title, content_hash) VALUES (?, ?, ?)",
                    (url, title, content_hash)
                )
                return cursor.lastrowid

    def add_chunks(self, chunks: List[Dict]):
        """
        Batch insert chunks efficiently.
        chunks structure: [{'doc_id': int, 'text': str, 'vector': np.ndarray, 'chunk_index': int, 'metadata': dict}, ...]
        """
        if not chunks:
            return
        
        with self._lock:
            data = []
            for c in chunks:
                vector_blob = c['vector'].tobytes() if c.get('vector') is not None else None
                meta_json = json.dumps(c.get('metadata', {}))
                data.append((c.get('doc_id', 0), c.get('chunk_index', 0), c['text'], vector_blob, meta_json))
            
            try:
                with self.conn:
                    self.conn.executemany(
                        "INSERT INTO chunks (doc_id, chunk_index, text, vector, metadata) VALUES (?, ?, ?, ?, ?)",
                        data
                    )
            except sqlite3.Error as e:
                logger.error(f"[DB] Bulk insert failed: {e}")
                raise

    def count_chunks(self) -> int:
        """Get total number of chunks in database."""
        with self._lock:
            cursor = self.conn.execute("SELECT COUNT(*) as count FROM chunks")
            row = cursor.fetchone()
            return row['count'] if row else 0

    def get_all_chunks(self) -> List[Dict]:
        """Retrieve all chunks for building FAISS index."""
        with self._lock:
            cursor = self.conn.execute("""
                SELECT c.id, c.text, c.vector, c.metadata, d.url, d.title
                FROM chunks c
                JOIN documents d ON c.doc_id = d.id
            """)
        
        results = []
        for row in cursor:
            # Reconstruct dictionary expected by rag_pipeline
            # Vector is retrieved as bytes, convert back to numpy
            vec_bytes = row['vector']
            vector = np.frombuffer(vec_bytes, dtype=np.float32) if vec_bytes else None
            
            meta = json.loads(row['metadata']) if row['metadata'] else {}
            
            results.append({
                "chunk_id": row['id'], # DB ID
                "text": row['text'],
                "vector": vector,
                "url": row['url'],
                "title": row['title'],
                **meta
            })
        return results

    def get_chunk_text(self, chunk_id: int) -> str:
        cursor = self.conn.execute("SELECT text FROM chunks WHERE id = ?", (chunk_id,))
        row = cursor.fetchone()
        return row['text'] if row else ""

    def clear_all(self):
        """
        Clear all documents and chunks from database (DESTRUCTIVE).

        WHAT:
            - Purpose: Remove all indexed data
            - Returns: None
            - Side effects: Deletes all rows from documents and chunks tables

        WHY:
            - Use case: Remove junk/test data from index
            - Problem solved: Clean slate for re-indexing
            - Safety: Irreversible operation

        HOW:
            1. Delete all chunks
            2. Delete all documents
            3. Reset autoincrement counters
            - Thread-safe with lock
        """
        with self._lock:
            with self.conn:
                self.conn.execute("DELETE FROM chunks")
                self.conn.execute("DELETE FROM documents")
                # Reset autoincrement
                self.conn.execute("DELETE FROM sqlite_sequence WHERE name='chunks'")
                self.conn.execute("DELETE FROM sqlite_sequence WHERE name='documents'")
                logger.info("[DB] All documents and chunks cleared")
