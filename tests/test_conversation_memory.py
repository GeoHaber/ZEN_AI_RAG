"""
test_conversation_memory.py - Tests for conversation history RAG

Tests the separate conversation memory system that keeps chat history
without polluting the main knowledge base.
"""

import pytest
import asyncio
import time
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zena_mode.conversation_memory import (
    ConversationMemory,
    ConversationDB,
    Message,
    ConversationSummary,
    MemoryConfig,
    get_conversation_memory,
)


class TestMessage:
    """Test Message data class."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(role="user", content="Hello, how are you?", session_id="test123")

        assert msg.role == "user"
        assert msg.content == "Hello, how are you?"
        assert msg.session_id == "test123"
        assert isinstance(msg.timestamp, datetime)

    def test_message_to_dict(self):
        """Test message serialization."""
        msg = Message(role="assistant", content="I'm doing well!", session_id="s1")
        data = msg.to_dict()

        assert data["role"] == "assistant"
        assert data["content"] == "I'm doing well!"
        assert "timestamp" in data

    def test_message_from_dict(self):
        """Test message deserialization."""
        data = {
            "role": "user",
            "content": "Test message",
            "timestamp": "2026-01-21T10:00:00",
            "session_id": "test",
            "metadata": {"source": "test"},
        }

        msg = Message.from_dict(data)

        assert msg.role == "user"
        assert msg.content == "Test message"
        assert msg.metadata == {"source": "test"}


class TestConversationDB:
    """Test ConversationDB SQLite storage."""

    def test_db_creation(self, tmp_path):
        """Test database initialization."""
        db_path = tmp_path / "test.db"
        db = ConversationDB(db_path)

        assert db_path.exists()
        db.close()

    def test_add_message(self, tmp_path):
        """Test adding a message."""
        db = ConversationDB(tmp_path / "test.db")

        msg = Message(role="user", content="Hello!", session_id="s1")
        msg_id = db.add_message(msg)

        assert msg_id > 0
        db.close()

    def test_get_recent_messages(self, tmp_path):
        """Test retrieving recent messages."""
        db = ConversationDB(tmp_path / "test.db")

        # Add several messages
        for i in range(5):
            msg = Message(role="user" if i % 2 == 0 else "assistant", content=f"Message {i}", session_id="s1")
            db.add_message(msg)

        # Retrieve
        messages = db.get_recent_messages("s1", limit=3)

        assert len(messages) == 3
        assert messages[-1].content == "Message 4"  # Most recent
        db.close()

    def test_session_isolation(self, tmp_path):
        """Test that sessions are isolated."""
        db = ConversationDB(tmp_path / "test.db")

        # Add to different sessions
        db.add_message(Message(role="user", content="Session 1", session_id="s1"))
        db.add_message(Message(role="user", content="Session 2", session_id="s2"))

        # Each session should only see its own messages
        s1_msgs = db.get_recent_messages("s1")
        s2_msgs = db.get_recent_messages("s2")

        assert len(s1_msgs) == 1
        assert s1_msgs[0].content == "Session 1"
        assert len(s2_msgs) == 1
        assert s2_msgs[0].content == "Session 2"
        db.close()


class TestConversationMemory:
    """Test main ConversationMemory class."""

    def test_initialization(self, tmp_path):
        """Test memory initialization."""
        memory = ConversationMemory(cache_dir=tmp_path)

        assert (tmp_path / "conversation.db").exists()
        assert memory.model is not None

    def test_add_and_retrieve(self, tmp_path):
        """Test adding and retrieving messages."""
        memory = ConversationMemory(cache_dir=tmp_path)

        # Add messages
        memory.add_message("user", "What is Python?", session_id="test")
        memory.add_message("assistant", "Python is a programming language.", session_id="test")

        # Retrieve
        history = memory.get_recent_history("test", turns=1)

        assert len(history) == 2
        assert history[0].role == "user"
        assert "Python" in history[0].content

    def test_semantic_search(self, tmp_path):
        """Test semantic search over history."""
        memory = ConversationMemory(cache_dir=tmp_path)

        # Add diverse messages
        memory.add_message("user", "How do I install Python packages?", session_id="test")
        memory.add_message("assistant", "Use pip install package_name", session_id="test")
        memory.add_message("user", "What's the weather like today?", session_id="test")
        memory.add_message("assistant", "I cannot check the weather.", session_id="test")
        memory.add_message("user", "How do I create a virtual environment?", session_id="test")
        memory.add_message("assistant", "Use python -m venv myenv", session_id="test")

        # Search for Python-related
        results = memory.search_history("pip install dependencies", session_id="test", k=3)

        # Should find pip-related message as most relevant
        assert len(results) > 0
        assert "pip" in results[0]["content"].lower() or "install" in results[0]["content"].lower()

    def test_context_building(self, tmp_path):
        """Test building context from history."""
        memory = ConversationMemory(cache_dir=tmp_path)

        # Build conversation
        memory.add_message("user", "My name is Alice", session_id="test")
        memory.add_message("assistant", "Nice to meet you, Alice!", session_id="test")
        memory.add_message("user", "I'm working on a Python project", session_id="test")
        memory.add_message("assistant", "That sounds interesting! What kind of project?", session_id="test")

        # Get context for follow-up
        context = memory.get_relevant_context("Can you help me with it?", session_id="test")

        # Should include recent history
        assert "Alice" in context or "Python project" in context

    def test_contextual_prompt(self, tmp_path):
        """Test building prompts with context."""
        memory = ConversationMemory(cache_dir=tmp_path)

        memory.add_message("user", "I'm building a RAG system", session_id="test")
        memory.add_message("assistant", "RAG systems combine retrieval with generation.", session_id="test")

        prompt = memory.build_contextual_prompt(
            "What embedding model should I use?", session_id="test", system_prompt="You are a helpful AI assistant."
        )

        assert "RAG" in prompt  # Context included
        assert "embedding" in prompt.lower()  # Current question included
        assert "helpful" in prompt  # System prompt included

    def test_stats(self, tmp_path):
        """Test getting memory statistics."""
        memory = ConversationMemory(cache_dir=tmp_path)

        memory.add_message("user", "Test message", session_id="test")

        stats = memory.get_stats("test")

        assert stats["total_messages"] >= 1
        assert "embedding_model" in stats


class TestTopicExtraction:
    """Test topic extraction from conversations."""

    def test_extract_topics(self, tmp_path):
        """Test topic keyword extraction."""
        memory = ConversationMemory(cache_dir=tmp_path)

        messages = [
            Message(role="user", content="How do I train a machine learning model?"),
            Message(role="assistant", content="You need data, a model architecture, and training loop."),
            Message(role="user", content="What about deep learning neural networks?"),
            Message(role="assistant", content="Neural networks learn hierarchical representations."),
        ]

        topics = memory._extract_topics(messages)

        # Should find relevant keywords
        assert len(topics) > 0
        # Common words like 'model', 'learning', 'neural' should appear
        topic_str = " ".join(topics).lower()
        assert any(kw in topic_str for kw in ["model", "learning", "neural", "training", "data"])


class TestMultiSession:
    """Test multi-session support."""

    def test_multiple_sessions(self, tmp_path):
        """Test multiple sessions work independently."""
        memory = ConversationMemory(cache_dir=tmp_path)

        # Add to session 1
        memory.add_message("user", "Session 1 user message", session_id="user1")
        memory.add_message("assistant", "Session 1 response", session_id="user1")

        # Add to session 2
        memory.add_message("user", "Session 2 user message", session_id="user2")
        memory.add_message("assistant", "Session 2 response", session_id="user2")

        # Verify isolation
        history1 = memory.get_recent_history("user1")
        history2 = memory.get_recent_history("user2")

        assert all("Session 1" in m.content for m in history1)
        assert all("Session 2" in m.content for m in history2)

    def test_clear_session(self, tmp_path):
        """Test clearing a session."""
        memory = ConversationMemory(cache_dir=tmp_path)

        memory.add_message("user", "Test message", session_id="to_clear")
        memory.clear_session("to_clear")

        # In-memory should be cleared
        stats = memory.get_stats("to_clear")
        assert stats["cache_size"] == 0


class TestIntegration:
    """Integration tests with mock LLM."""

    def test_full_conversation_flow(self, tmp_path):
        """Test a complete conversation flow."""
        memory = ConversationMemory(cache_dir=tmp_path)
        session = "integration_test"

        # Simulate a conversation
        exchanges = [
            ("What is Python?", "Python is a high-level programming language."),
            ("Is it easy to learn?", "Yes, Python has a gentle learning curve."),
            ("What can I build with it?", "Web apps, data analysis, AI, and more."),
        ]

        for user_msg, assistant_msg in exchanges:
            memory.add_message("user", user_msg, session_id=session)
            memory.add_message("assistant", assistant_msg, session_id=session)

        # Now ask a follow-up
        context = memory.get_relevant_context("Which library should I use?", session_id=session)

        # Should have context about Python
        assert "Python" in context

        # Stats should reflect all messages
        stats = memory.get_stats(session)
        assert stats["total_messages"] == 6


class TestFactoryFunction:
    """Test convenience factory function."""

    def test_get_conversation_memory(self, tmp_path):
        """Test factory creates memory correctly."""
        memory = get_conversation_memory(cache_dir=tmp_path)

        assert isinstance(memory, ConversationMemory)
        assert memory.cache_dir == tmp_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
