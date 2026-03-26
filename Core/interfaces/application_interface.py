"""
Application Interface - The CONTRACT

This abstract interface defines exactly what this application CAN DO.
Every interaction (test, UI, API) goes through this interface.

ANY UI framework must implement these methods to work with the core logic.
ANY test uses this interface to verify functionality.
ANY API adapter uses this interface to provide access.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator
from Core.models import (
    QueryRequest,
    QueryResponse,
    ChatRequest,
    ChatResponse,
    SearchRequest,
    SearchResponse,
    StreamRequest,
    StreamChunk,
    StatusResponse,
)


class ApplicationInterface(ABC):
    """
    The APPLICATION CONTRACT.

    This defines what ZEN_RAG CAN DO:
    - Answer queries with RAG context
    - Have multi-turn conversations
    - Search the knowledge base
    - Stream responses
    - Report status

    All UIs, tests, and APIs access the app through this interface.
    """

    # ─────────────────────────────────────────────────────
    # CORE CAPABILITIES
    # ─────────────────────────────────────────────────────

    @abstractmethod
    async def query(self, request: QueryRequest) -> QueryResponse:
        """
        Execute a single query with RAG context.

        This is the CORE feature: Take a question, search RAG, get answered.

        Args:
            request: QueryRequest with the question and settings

        Returns:
            QueryResponse with answer and sources

        Raises:
            InvalidQueryException: If query is invalid
            RAGEngineException: If RAG search fails
            LLMException: If LLM generation fails
        """
        pass

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Chat with RAG context and conversation memory.

        This enables multi-turn conversations where each response
        uses both the chat history and RAG context.

        Args:
            request: ChatRequest with message and session

        Returns:
            ChatResponse with response and updated history

        Raises:
            InvalidChatException: If message is invalid
            SessionException: If session doesn't exist
        """
        pass

    @abstractmethod
    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Search the knowledge base directly.

        Used when you want to explore available knowledge before querying.

        Args:
            request: SearchRequest with query and filters

        Returns:
            SearchResponse with matching documents

        Raises:
            InvalidSearchException: If search parameters invalid
            RAGEngineException: If search fails
        """
        pass

    @abstractmethod
    async def stream(self, request: StreamRequest) -> AsyncIterator[StreamChunk]:
        """
        Stream responses as they're generated.

        Useful for long responses or real-time UI updates.
        The caller should iterate this to get chunks as they arrive.

        Args:
            request: StreamRequest with query and settings

        Yields:
            StreamChunk objects as they're generated

        Raises:
            InvalidStreamException: If stream request invalid
            LLMException: If streaming fails
        """
        pass

    # ─────────────────────────────────────────────────────
    # MANAGEMENT OPERATIONS
    # ─────────────────────────────────────────────────────

    @abstractmethod
    async def get_status(self) -> StatusResponse:
        """
        Get the current status of the application.

        Returns operational status of all components.

        Returns:
            StatusResponse with component statuses
        """
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the application.

        Called on startup to set up all services.

        Returns:
            True if initialization successful

        Raises:
            InitializationException: If setup fails
        """
        pass

    @abstractmethod
    async def shutdown(self) -> bool:
        """
        Gracefully shutdown the application.

        Called on exit to clean up resources.

        Returns:
            True if shutdown successful
        """
        pass

    # ─────────────────────────────────────────────────────
    # OPTIONAL CAPABILITIES (For advanced UIs)
    # ─────────────────────────────────────────────────────

    async def get_chat_history(self, session_id: str, limit: int = 20) -> list:
        """
        Get chat history for a session.

        Optional: Only implement if storing histories.
        """
        raise NotImplementedError("Chat history not supported")

    async def clear_chat_session(self, session_id: str) -> bool:
        """
        Clear a chat session.

        Optional: Only implement if managing sessions.
        """
        raise NotImplementedError("Session management not supported")

    async def get_knowledge_base_stats(self) -> dict:
        """
        Get statistics about the knowledge base.

        Optional: For analytics dashboards.
        """
        raise NotImplementedError("Knowledge base stats not supported")


# ═══════════════════════════════════════════════════════════
# IMPORTANT NOTE
# ═══════════════════════════════════════════════════════════
#
# This interface is the CONTRACT.
#
# To use ZEN_RAG:
# 1. Implement ApplicationInterface in a service
# 2. Use it directly in tests (LocalAPI)
# 3. Wrap it in HTTP adapters (FastAPI)
# 4. Call it from UIs (Streamlit, NiceUI, Web)
#
# The UIs are just skins. The REAL app is here.
