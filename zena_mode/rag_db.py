
"""
rag_db.py - SQLite storage for RAG documents and chunks.
Replaces monolithic JSON for scalability.
"""
import sqlite3
import hashlib
import json
import logging
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class RAGDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
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
        cursor = self.conn.execute("SELECT 1 FROM documents WHERE content_hash = ?", (content_hash,))
        return cursor.fetchone() is not None

    def add_document(self, url: str, title: str, content: str) -> int:
        """Insert document and return ID. Returns existing ID if duplicate URL."""
        # Check URL collision first
        cursor = self.conn.execute("SELECT id FROM documents WHERE url = ?", (url,))
        row = cursor.fetchone()
        if row:
            return row['id']
            
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Check Content Hash collision (same content, different URL?)
        # For strict deduplication, we might want to skip. 
        # But RAG usually indexes everything. Let's just store.
        
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO documents (url, title, content_hash) VALUES (?, ?, ?)",
                (url, title, content_hash)
            )
            return cursor.lastrowid

    def add_chunks(self, doc_id: int, chunks: List[Dict]):
        """
        Batch insert chunks.
        chunks structure: [{'text': str, 'vector': np.ndarray, 'index': int, 'metadata': dict}]
        """
        data = []
        for c in chunks:
            vector_blob = c['vector'].tobytes() if c.get('vector') is not None else None
            meta_json = json.dumps(c.get('metadata', {}))
            data.append((doc_id, c.get('chunk_index', 0), c['text'], vector_blob, meta_json))
        
        with self.conn:
            self.conn.executemany(
                "INSERT INTO chunks (doc_id, chunk_index, text, vector, metadata) VALUES (?, ?, ?, ?, ?)",
                data
            )

    def get_all_chunks(self) -> List[Dict]:
        """Retrieve all chunks for building FAISS index."""
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
