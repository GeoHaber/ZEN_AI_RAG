# -*- coding: utf-8 -*-
"""
state_management.py - Thread-safe state management for ZenAI
"""
import threading
import time
import asyncio
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from config_system import config, EMOJI
import logging

logger = logging.getLogger(__name__)


@dataclass
class AttachmentState:
    """Thread-safe attachment state management."""
    name: Optional[str] = None
    content: Optional[str] = None
    preview: Optional[str] = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    
    def set(self, name: str, content: str, preview: str) -> None:
        """Set attachment data (thread-safe)."""
        with self._lock:
            self.name = name
            self.content = content
            self.preview = preview
            logger.debug(f"[Attachment] Set: {name} ({len(content)} chars)")
    
    def get(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get attachment data (thread-safe)."""
        with self._lock:
            return (self.name, self.content, self.preview)
    
    def clear(self) -> None:
        """Clear attachment data (thread-safe)."""
        with self._lock:
            self.name = None
            self.content = None
            self.preview = None
            logger.debug("[Attachment] Cleared")
    
    def has_attachment(self) -> bool:
        """Check if attachment exists."""
        with self._lock:
            return self.name is not None


@dataclass
class ChatMessage:
    """Single chat message."""
    role: str  # 'user' or 'assistant' or 'system'
    content: str
    timestamp: float = field(default_factory=time.time)


class ChatHistory:
    """Manage chat history with pagination to prevent memory leaks."""
    
    def __init__(self, max_messages: int = None):
        self.max_messages = max_messages or config.MAX_CHAT_MESSAGES
        self.messages: List[ChatMessage] = []
        self._lock = threading.Lock()
        logger.info(f"[ChatHistory] Initialized with max {self.max_messages} messages")
    
    def add(self, role: str, content: str) -> None:
        """Add message to history with auto-trimming."""
        with self._lock:
            self.messages.append(ChatMessage(role, content))
            
            # Auto-trim old messages
            if len(self.messages) > self.max_messages:
                removed = len(self.messages) - self.max_messages
                self.messages = self.messages[-self.max_messages:]
                logger.info(f"[ChatHistory] Trimmed {removed} old messages (now {len(self.messages)})")
    
    def get_recent(self, n: int = 10) -> List[ChatMessage]:
        """Get recent N messages."""
        with self._lock:
            return self.messages[-n:] if self.messages else []
    
    def get_all(self) -> List[ChatMessage]:
        """Get all messages (copy)."""
        with self._lock:
            return self.messages.copy()
    
    def clear(self) -> None:
        """Clear all messages."""
        with self._lock:
            count = len(self.messages)
            self.messages.clear()
            logger.info(f"[ChatHistory] Cleared {count} messages")
    
    def count(self) -> int:
        """Get message count."""
        with self._lock:
            return len(self.messages)


def handle_error(
    error: Exception, 
    context: str, 
    notify_user: bool = True
) -> None:
    """
    Centralized error handling with logging and user notifications.
    
    Args:
        error: The exception that occurred
        context: Context string (e.g., "RAG Scan", "File Upload")
        notify_user: Whether to show UI notification
    """
    # Log error with full context
    logger.error(f"[{context}] {type(error).__name__}: {error}", exc_info=True)
    
    if notify_user:
        try:
            from nicegui import ui
            
            # Map exceptions to user-friendly messages
            error_messages = {
                ConnectionError: "Cannot connect to backend. Is the server running?",
                TimeoutError: "Request timed out. Please try again.",
                ValueError: "Invalid input. Please check your data.",
                FileNotFoundError: "File not found. Please check the path.",
                PermissionError: "Permission denied. Check file permissions.",
                MemoryError: "Out of memory. Try with smaller data.",
                ImportError: "Missing dependency. Please install required packages.",
            }
            
            user_message = error_messages.get(
                type(error), 
                f"An error occurred: {str(error)}"
            )
            
            ui.notify(
                f"{EMOJI['error']} {user_message}",
                color='negative',
                position='top',
                timeout=5000
            )
        except Exception as notify_error:
            # If notification fails, just log it
            logger.error(f"[{context}] Failed to notify user: {notify_error}")


# Global instances
attachment_state = AttachmentState()
chat_history = ChatHistory()
