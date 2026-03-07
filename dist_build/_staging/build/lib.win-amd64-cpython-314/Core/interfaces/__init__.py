"""
Application Interface — The CONTRACT.

This abstract interface defines exactly what this application CAN DO.
Every interaction (test, UI, API) goes through this interface.

Adapted from RAG_RAT/Core/interfaces/application_interface.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional

from Core.models import (
    ChatRequest, ChatResponse,
    QueryRequest, QueryResponse,
    SearchRequest, SearchResponse,
    StatusResponse,
    StreamChunk, StreamRequest,
)


class ApplicationInterface(ABC):
    """
    The APPLICATION CONTRACT for ZEN_AI_RAG.

    Defines what the system can do:
      - Answer queries with RAG context
      - Have multi-turn conversations
      - Search the knowledge base
      - Stream responses
      - Report status
    """

    # ─── Core Capabilities ───────────────────────────────

    @abstractmethod
    async def query(self, request: QueryRequest) -> QueryResponse:
        """Execute a single query with RAG context."""

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Chat with RAG context and conversation memory."""

    @abstractmethod
    async def search(self, request: SearchRequest) -> SearchResponse:
        """Search the knowledge base directly."""

    @abstractmethod
    async def stream(self, request: StreamRequest) -> AsyncIterator[StreamChunk]:
        """Stream responses as they're generated."""

    # ─── Lifecycle ───────────────────────────────────────

    @abstractmethod
    async def get_status(self) -> StatusResponse:
        """Get the current operational status."""

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize all services.  Called on startup."""

    @abstractmethod
    async def shutdown(self) -> bool:
        """Gracefully shutdown.  Called on exit."""

    # ─── Optional Capabilities ───────────────────────────

    async def get_chat_history(self, session_id: str, limit: int = 20) -> list:
        """Get chat history for a session (optional)."""
        raise NotImplementedError("Chat history not supported")

    async def clear_chat_session(self, session_id: str) -> bool:
        """Clear a chat session (optional)."""
        raise NotImplementedError("Session management not supported")

    async def get_knowledge_base_stats(self) -> dict:
        """Get statistics about the knowledge base (optional)."""
        raise NotImplementedError("Knowledge base stats not supported")
