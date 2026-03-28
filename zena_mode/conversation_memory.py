"""
conversation_memory.py - Lightweight Conversation History RAG

Keeps chat history separate from the main knowledge RAG to:
- Maintain conversation context across sessions
- Use LLM to summarize/compress old conversations
- Enable "remember what we discussed" queries
- Not pollute the main knowledge base

Architecture:
- Separate SQLite DB (conversation.db)
- Rolling window of recent messages (configurable)
- LLM-based summarization for older context
- Semantic search for relevant past conversations
"""

from __future__ import annotations
import logging
import sqlite3
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)

# Core dependencies
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np

    DEPS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    faiss = None
    np = None
    DEPS_AVAILABLE = False


# =============================================================================
# Configuration
# =============================================================================
@dataclass
class MemoryConfig:
    """Configuration for conversation memory."""

    # Recent messages kept in full detail
    RECENT_WINDOW: int = 20

    # Max tokens for context injection (approximate)
    MAX_CONTEXT_TOKENS: int = 2000

    # Summarization trigger (messages before summarizing)
    SUMMARIZE_THRESHOLD: int = 50

    # How many past turns to include by default
    DEFAULT_HISTORY_TURNS: int = 5

    # Embedding model (smaller/faster for conversations)
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Similarity threshold for retrieving relevant history
    RELEVANCE_THRESHOLD: float = 0.5


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class Message:
    """Single conversation message."""

    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = "default"
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Message":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            session_id=data.get("session_id", "default"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConversationSummary:
    """Compressed summary of older conversations."""

    summary_text: str
    start_time: datetime
    end_time: datetime
    message_count: int
    topics: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "summary_text": self.summary_text,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "message_count": self.message_count,
            "topics": self.topics,
        }


# =============================================================================
# Conversation Memory Database
# =============================================================================
class ConversationDB:
    """SQLite storage for conversation history."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Ensure numpy is loaded for vectors if needed
        # (Actually vector handling below uses bytes, so numpy only needed for FAISS interaction)

        with self.conn:
            # Messages table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    vector BLOB,
                    metadata TEXT DEFAULT '{}',
                    summarized INTEGER DEFAULT 0
                )
            """)

            # Summaries table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    summary_text TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    message_count INTEGER,
                    topics TEXT DEFAULT '[]',
                    vector BLOB,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Sessions table (for multi-user/multi-session support)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_active TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            # Indexes
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_summaries_session ON summaries(session_id)")

    def add_message(self, msg: Message, vector: Optional["np.ndarray"] = None) -> int:
        """Add a message to the database."""
        with self._lock:
            vector_blob = vector.tobytes() if vector is not None else None
            cursor = self.conn.execute(
                """
                INSERT INTO messages (session_id, role, content, timestamp, vector, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    msg.session_id,
                    msg.role,
                    msg.content,
                    msg.timestamp.isoformat(),
                    vector_blob,
                    json.dumps(msg.metadata),
                ),
            )
            self.conn.commit()
            return cursor.lastrowid

    def get_recent_messages(self, session_id: str, limit: int = 20) -> List[Message]:
        """Get recent messages for a session."""
        with self._lock:
            cursor = self.conn.execute(
                """
                SELECT * FROM messages 
                WHERE session_id = ? AND summarized = 0
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (session_id, limit),
            )

            rows = cursor.fetchall()
            messages = []
            for row in reversed(rows):  # Reverse to get chronological order
                messages.append(
                    Message(
                        role=row["role"],
                        content=row["content"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        session_id=row["session_id"],
                        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    )
                )
            return messages

    def get_unsummarized_count(self, session_id: str) -> int:
        """Count messages not yet summarized."""
        with self._lock:
            cursor = self.conn.execute(
                """
                SELECT COUNT(*) FROM messages 
                WHERE session_id = ? AND summarized = 0
            """,
                (session_id,),
            )
            return cursor.fetchone()[0]

    def mark_as_summarized(self, session_id: str, before_timestamp: datetime):
        """Mark older messages as summarized."""
        with self._lock:
            self.conn.execute(
                """
                UPDATE messages 
                SET summarized = 1
                WHERE session_id = ? AND timestamp < ?
            """,
                (session_id, before_timestamp.isoformat()),
            )
            self.conn.commit()

    def add_summary(
        self,
        session_id: str,
        summary: ConversationSummary,
        vector: Optional["np.ndarray"] = None,
    ) -> int:
        """Store a conversation summary."""
        with self._lock:
            vector_blob = vector.tobytes() if vector is not None else None
            cursor = self.conn.execute(
                """
                INSERT INTO summaries (session_id, summary_text, start_time, end_time, 
                                      message_count, topics, vector)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    summary.summary_text,
                    summary.start_time.isoformat(),
                    summary.end_time.isoformat(),
                    summary.message_count,
                    json.dumps(summary.topics),
                    vector_blob,
                ),
            )
            self.conn.commit()
            return cursor.lastrowid

    def get_all_vectors(self, session_id: str) -> List[Tuple[int, np.ndarray, str]]:
        """Get all message vectors for FAISS index building."""
        with self._lock:
            cursor = self.conn.execute(
                """
                SELECT id, vector, content FROM messages 
                WHERE session_id = ? AND vector IS NOT NULL
            """,
                (session_id,),
            )

            results = []
            for row in cursor:
                if row["vector"]:
                    vec = np.frombuffer(row["vector"], dtype=np.float32)
                    results.append((row["id"], vec, row["content"]))
            return results

    def get_summaries(self, session_id: str) -> List[ConversationSummary]:
        """Get all summaries for a session."""
        with self._lock:
            cursor = self.conn.execute(
                """
                SELECT * FROM summaries 
                WHERE session_id = ?
                ORDER BY end_time DESC
            """,
                (session_id,),
            )

            return [
                ConversationSummary(
                    summary_text=row["summary_text"],
                    start_time=datetime.fromisoformat(row["start_time"]),
                    end_time=datetime.fromisoformat(row["end_time"]),
                    message_count=row["message_count"],
                    topics=json.loads(row["topics"]) if row["topics"] else [],
                )
                for row in cursor
            ]

    def close(self):
        if self.conn:
            self.conn.close()


# =============================================================================
# Conversation Memory Manager
# =============================================================================
class ConversationMemory:
    """
    Main class for managing conversation history with semantic search.

    Features:
    - Stores messages with embeddings for semantic retrieval
    - Auto-summarizes old conversations using LLM
    - Provides context for follow-up questions
    - Separate from main RAG to avoid pollution

    Usage:
        memory = ConversationMemory(cache_dir=Path("conv_cache"))

        # Add messages
        memory.add_message("user", "What is Python?", session_id="user123")
        memory.add_message("assistant", "Python is a programming language...", session_id="user123")

        # Get context for new query
        context = memory.get_relevant_context("Tell me more about Python", session_id="user123")

        # Build prompt with history
        prompt = memory.build_contextual_prompt("How do I install packages?", session_id="user123")
    """

    def __init__(self, cache_dir: Optional[Path] = None, config: Optional[MemoryConfig] = None):
        if not DEPS_AVAILABLE:
            raise ImportError("Install: pip install sentence-transformers faiss-cpu")

        self.config = config or MemoryConfig()
        self.cache_dir = cache_dir or Path("conversation_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Separate DB from main RAG
        self.db = ConversationDB(self.cache_dir / "conversation.db")

        if not DEPS_AVAILABLE:
            raise ImportError("Install: pip install sentence-transformers faiss-cpu numpy")

        self.model = SentenceTransformer(self.config.EMBEDDING_MODEL)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        # Per-session FAISS indexes (lightweight, rebuilt on demand)
        self._indexes: Dict[str, faiss.IndexFlatIP] = {}
        self._index_data: Dict[str, List[Tuple[int, str]]] = {}  # id -> content mapping

        # In-memory recent messages cache (for speed)
        self._recent_cache: Dict[str, deque] = {}

        self._lock = threading.RLock()

        logger.info(f"[ConvMemory] Initialized at {self.cache_dir}")

    def _get_or_create_index(self, session_id: str) -> Tuple[faiss.IndexFlatIP, List]:
        """Get or create FAISS index for a session."""
        if session_id not in self._indexes:
            self._indexes[session_id] = faiss.IndexFlatIP(self.embedding_dim)
            self._index_data[session_id] = []

            # Load existing vectors from DB
            vectors_data = self.db.get_all_vectors(session_id)
            if vectors_data:
                vectors = np.vstack([v[1] for v in vectors_data]).astype("float32")
                faiss.normalize_L2(vectors)
                self._indexes[session_id].add(vectors)
                self._index_data[session_id] = [(v[0], v[2]) for v in vectors_data]

        return self._indexes[session_id], self._index_data[session_id]

    def add_message(
        self,
        role: str,
        content: str,
        session_id: str = "default",
        metadata: Optional[Dict] = None,
    ) -> int:
        """
        Add a message to conversation history.

        Args:
            role: 'user', 'assistant', or 'system'
            content: Message text
            session_id: Session identifier (for multi-user support)
            metadata: Optional metadata (e.g., model used, response time)

        Returns:
            Message ID
        """
        with self._lock:
            msg = Message(
                role=role,
                content=content,
                timestamp=datetime.now(),
                session_id=session_id,
                metadata=metadata or {},
            )

            # Embed the content
            embedding = self.model.encode([content], convert_to_numpy=True, normalize_embeddings=True)[0].astype(
                "float32"
            )

            # Store in DB
            msg_id = self.db.add_message(msg, embedding)

            # Update FAISS index
            index, data = self._get_or_create_index(session_id)
            index.add(embedding.reshape(1, -1))
            data.append((msg_id, content))

            # Update recent cache
            if session_id not in self._recent_cache:
                self._recent_cache[session_id] = deque(maxlen=self.config.RECENT_WINDOW)
            self._recent_cache[session_id].append(msg)

            logger.debug(f"[ConvMemory] Added {role} message to session {session_id}")

            return msg_id

    def get_recent_history(self, session_id: str = "default", turns: Optional[int] = None) -> List[Message]:
        """
        Get recent conversation history.

        Args:
            session_id: Session identifier
            turns: Number of turns (user+assistant pairs) to return

        Returns:
            List of Message objects in chronological order
        """
        turns = turns or self.config.DEFAULT_HISTORY_TURNS
        limit = turns * 2  # Each turn = user + assistant

        # Try cache first
        if session_id in self._recent_cache:
            cached = list(self._recent_cache[session_id])
            if len(cached) >= limit:
                return cached[-limit:]

        # Fall back to DB
        return self.db.get_recent_messages(session_id, limit)

    def search_history(self, query: str, session_id: str = "default", k: int = 5) -> List[Dict]:
        """
        Semantic search over conversation history.

        Args:
            query: Search query
            session_id: Session identifier
            k: Number of results

        Returns:
            List of relevant messages with scores
        """
        with self._lock:
            index, data = self._get_or_create_index(session_id)

            if index.ntotal == 0:
                return []

            # Embed query
            query_vec = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")

            # Search
            k = min(k, index.ntotal)
            similarities, indices = index.search(query_vec, k)

            results = []
            for sim, idx in zip(similarities[0], indices[0]):
                if idx >= 0 and idx < len(data) and sim >= self.config.RELEVANCE_THRESHOLD:
                    msg_id, content = data[idx]
                    results.append({"id": msg_id, "content": content, "score": float(sim)})

            return results

    def get_relevant_context(
        self,
        query: str,
        session_id: str = "default",
        include_recent: bool = True,
        include_search: bool = True,
    ) -> str:
        """
        Build context string from relevant history.

        Combines:
        - Recent messages (for continuity)
        - Semantically relevant past messages (for topic recall)

        Args:
            query: Current user query
            session_id: Session identifier
            include_recent: Include recent conversation turns
            include_search: Include semantically relevant history

        Returns:
            Formatted context string
        """
        context_parts = []

        # Recent history
        if include_recent:
            recent = self.get_recent_history(session_id, turns=3)
            if recent:
                context_parts.append("=== Recent Conversation ===")
                for msg in recent:
                    prefix = "User" if msg.role == "user" else "Assistant"
                    context_parts.append(f"{prefix}: {msg.content}")

        # Semantic search for relevant history
        if include_search:
            relevant = self.search_history(query, session_id, k=3)
            # Filter out messages already in recent
            recent_contents = {m.content for m in self.get_recent_history(session_id)}
            relevant = [r for r in relevant if r["content"] not in recent_contents]

            if relevant:
                context_parts.append("\n=== Relevant Past Context ===")
                for r in relevant:
                    context_parts.append(f"(Relevance: {r['score']:.2f}) {r['content'][:200]}...")

        return "\n".join(context_parts) if context_parts else ""

    def build_contextual_prompt(
        self,
        user_query: str,
        session_id: str = "default",
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Build a prompt with conversation context.

        Args:
            user_query: Current user question
            session_id: Session identifier
            system_prompt: Optional system prompt

        Returns:
            Complete prompt with context
        """
        context = self.get_relevant_context(user_query, session_id)

        parts = []

        if system_prompt:
            parts.append(f"System: {system_prompt}\n")

        if context:
            parts.append(f"Conversation Context:\n{context}\n")

        parts.append(f"Current Question: {user_query}")

        return "\n".join(parts)

    async def summarize_old_messages(self, session_id: str, llm_backend) -> Optional[ConversationSummary]:
        """
        Use LLM to summarize older messages (async).

        Call this periodically to compress old history.

        Args:
            session_id: Session identifier
            llm_backend: LLM backend with send_message_async method

        Returns:
            ConversationSummary if summarization occurred, None otherwise
        """
        count = self.db.get_unsummarized_count(session_id)

        if count < self.config.SUMMARIZE_THRESHOLD:
            logger.debug(f"[ConvMemory] Only {count} unsummarized messages, skipping")
            return None

        # Get messages to summarize (keep recent ones)
        all_messages = self.db.get_recent_messages(session_id, limit=count)
        to_summarize = all_messages[: -self.config.RECENT_WINDOW]

        if not to_summarize:
            return None

        # Build summarization prompt
        conversation_text = "\n".join([f"{m.role.upper()}: {m.content}" for m in to_summarize])

        summarize_prompt = f"""Summarize this conversation concisely, capturing:
1. Main topics discussed
2. Key decisions or conclusions
3. Important information shared

Conversation:
{conversation_text}

Provide a brief summary (2-3 paragraphs max):"""

        # Get summary from LLM
        summary_text = ""
        async for chunk in llm_backend.send_message_async(summarize_prompt):
            summary_text += chunk

        # Extract topics (simple keyword extraction)
        topics = self._extract_topics(to_summarize)

        summary = ConversationSummary(
            summary_text=summary_text.strip(),
            start_time=to_summarize[0].timestamp,
            end_time=to_summarize[-1].timestamp,
            message_count=len(to_summarize),
            topics=topics,
        )

        # Store summary
        summary_embedding = self.model.encode([summary_text], convert_to_numpy=True, normalize_embeddings=True)[
            0
        ].astype("float32")

        self.db.add_summary(session_id, summary, summary_embedding)

        # Mark messages as summarized
        self.db.mark_as_summarized(session_id, to_summarize[-1].timestamp)

        logger.info(f"[ConvMemory] Summarized {len(to_summarize)} messages for session {session_id}")

        return summary

    def _extract_topics(self, messages: List[Message]) -> List[str]:
        """Extract topic keywords from messages (simple implementation)."""
        # Simple word frequency approach
        from collections import Counter
        import re

        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "dare",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "i",
            "me",
            "my",
            "myself",
            "we",
            "our",
            "you",
            "your",
            "he",
            "she",
            "it",
            "they",
            "them",
            "what",
            "which",
            "who",
            "this",
            "that",
            "these",
            "and",
            "but",
            "if",
            "or",
            "because",
            "as",
            "until",
            "while",
        }

        all_words = []
        for msg in messages:
            words = re.findall(r"\b[a-zA-Z]{4,}\b", msg.content.lower())
            all_words.extend([w for w in words if w not in stop_words])

        # Get top 5 most common
        counter = Counter(all_words)
        return [word for word, _ in counter.most_common(5)]

    def get_stats(self, session_id: str = "default") -> Dict:
        """Get memory statistics for a session."""
        return {
            "total_messages": self.db.get_unsummarized_count(session_id),
            "index_vectors": self._indexes.get(session_id, faiss.IndexFlatIP(1)).ntotal
            if session_id in self._indexes
            else 0,
            "summaries": len(self.db.get_summaries(session_id)),
            "cache_size": len(self._recent_cache.get(session_id, [])),
            "embedding_model": self.config.EMBEDDING_MODEL,
        }

    def clear_session(self, session_id: str):
        """Clear all data for a session."""
        with self._lock:
            # Clear FAISS index
            if session_id in self._indexes:
                del self._indexes[session_id]
                del self._index_data[session_id]

            # Clear cache
            if session_id in self._recent_cache:
                del self._recent_cache[session_id]

            # Note: DB data persists - add explicit deletion if needed
            logger.info(f"[ConvMemory] Cleared in-memory data for session {session_id}")


# =============================================================================
# Convenience Functions
# =============================================================================
def get_conversation_memory(cache_dir: Optional[Path] = None) -> ConversationMemory:
    """Factory function to get a conversation memory instance."""
    default_dir = Path("conversation_cache")
    return ConversationMemory(cache_dir=cache_dir or default_dir)
