"""
Local API - Direct Python Access to the Application

This adapter provides direct Python access to the ApplicationInterface.
Used by:
- Tests (to verify functionality)
- Local scripts (to automate tasks)
- Development (to debug)

NOT used by:
- UIs (they import this but wrap it appropriately)
- External HTTP clients (use HTTP adapter)
"""

from typing import AsyncIterator, List, Dict, Optional
from datetime import datetime
import logging

from Core.interfaces.application_interface import ApplicationInterface
from Core.models import (
    QueryRequest,
    QueryResponse,
    ChatRequest,
    ChatResponse,
    ChatMessage,
    SearchRequest,
    SearchResponse,
    SearchResult,
    StreamRequest,
    StreamChunk,
    StatusResponse,
)


logger = logging.getLogger(__name__)


class ApplicationCore(ApplicationInterface):
    """
    The ACTUAL application implementation.

    Delegates to the real service layer in Core/services/:
    - RAGService  – retrieval-augmented generation pipeline
    - LLMService  – provider-agnostic LLM access
    - DocumentService – knowledge-base management
    - SessionService – conversation history
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._initialized = False
        self._uptime_start: Optional[datetime] = None

        # Real service instances (created in initialize)
        self._rag_service = None  # Core.services.rag_service.RAGService
        self._llm_service = None  # Core.services.llm_service.LLMService
        self._doc_service = None  # Core.services.document_service.DocumentService
        self._session_service = None  # Core.services.session_service.SessionService

        # Configurable defaults (can be overridden via self.config)
        self._provider = self.config.get("provider", "local")
        self._model = self.config.get("model", "default")
        self._api_key = self.config.get("api_key")

        logger.info("ApplicationCore instantiated")

    # ──────────────────────── lifecycle ────────────────────────

    async def initialize(self) -> bool:
        """Instantiate and wire real services from Core/services/."""
        try:
            logger.info("Initializing ApplicationCore…")

            from Core.services.llm_service import LLMService
            from Core.services.rag_service import RAGService
            from Core.services.document_service import DocumentService
            from Core.services.session_service import SessionService

            self._llm_service = LLMService()
            self._rag_service = RAGService()
            self._doc_service = DocumentService()
            self._session_service = SessionService()

            # RAGService lazily creates its own LLMService; wire ours for
            # consistency so every call goes through the same adapter cache.
            self._rag_service.llm_service = self._llm_service

            self._uptime_start = datetime.now()
            self._initialized = True
            logger.info("ApplicationCore initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise

    async def shutdown(self) -> bool:
        """Graceful shutdown - release resources."""
        try:
            logger.info("Shutting down ApplicationCore…")
            self._initialized = False
            self._rag_service = None
            self._llm_service = None
            self._doc_service = None
            self._session_service = None
            logger.info("ApplicationCore shutdown complete")
            return True
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            return False

    # ──────────────────────── query ────────────────────────

    async def query(self, request: QueryRequest) -> QueryResponse:
        """
        Full RAG query: retrieve context → augment prompt → call LLM.
        """
        request.validate()
        logger.info(f"Processing query: {request.query[:50]}…")
        start = datetime.now()

        try:
            # Use the RAG pipeline for a full answer
            answer = await self._rag_service.full_rag_pipeline(
                query=request.query,
                provider=self._provider,
                model=self._model,
                api_key=self._api_key,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            # Retrieve sources separately if requested
            sources: List[Dict] = []
            if request.include_sources:
                sources = await self._rag_service.retrieve_documents(
                    query=request.query,
                    top_k=5,
                )

            elapsed = (datetime.now() - start).total_seconds() * 1000
            response = QueryResponse(
                content=answer,
                sources=sources,
                processing_time_ms=elapsed,
            )
            logger.info(f"Query completed in {elapsed:.1f}ms")
            return response

        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise

    # ──────────────────────── chat ────────────────────────

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Conversational RAG with session history.
        """
        request.validate()
        logger.info(f"Processing chat: session={request.session_id}")
        start = datetime.now()

        try:
            # Ensure session exists
            session = self._session_service.get_session(request.session_id)
            if session is None:
                self._session_service.create_session(user_id=request.session_id)

            # Record user message
            self._session_service.add_message(
                request.session_id,
                role="user",
                content=request.message,
            )

            # Build history context for the LLM
            recent = self._session_service.get_recent_history(
                request.session_id,
                max_messages=request.max_history,
            )
            history_msgs = [{"role": m["role"], "content": m["content"]} for m in recent]

            # Retrieve RAG context
            docs = await self._rag_service.retrieve_documents(
                query=request.message,
                top_k=5,
            )
            if docs:
                ctx_text = "\n\n".join(d.get("content", "")[:1000] for d in docs)
                system_prompt = (
                    "Use the following context to answer the user. "
                    "If the context is not relevant, say so.\n\n"
                    f"Context:\n{ctx_text}"
                )
            else:
                system_prompt = "You are a helpful assistant."

            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history_msgs)

            # Generate response
            answer = await self._llm_service.call_llm(
                provider=self._provider,
                model=self._model,
                messages=messages,
                api_key=self._api_key,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            # Record assistant message
            self._session_service.add_message(
                request.session_id,
                role="assistant",
                content=answer,
            )

            assistant_msg = ChatMessage(role="assistant", content=answer)

            # Build full history for the response
            full_hist = self._session_service.get_history(request.session_id)
            chat_msgs = [ChatMessage(role=m["role"], content=m["content"]) for m in full_hist]

            elapsed = (datetime.now() - start).total_seconds() * 1000
            response = ChatResponse(
                message=assistant_msg,
                history=chat_msgs,
                processing_time_ms=elapsed,
            )
            logger.info(f"Chat completed in {elapsed:.1f}ms")
            return response

        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise

    # ──────────────────────── search ────────────────────────

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Knowledge-base search (embeddings / hybrid).
        """
        request.validate()
        logger.info(f"Searching: {request.query[:50]}…")
        start = datetime.now()

        try:
            raw = await self._rag_service.retrieve_documents(
                query=request.query,
                top_k=request.limit,
            )

            results = [
                SearchResult(
                    content=d.get("content", ""),
                    score=d.get("score", 0.0),
                    document_id=d.get("name", "unknown"),
                )
                for d in raw
                if d.get("score", 0.0) >= request.threshold
            ]

            elapsed = (datetime.now() - start).total_seconds() * 1000
            response = SearchResponse(
                results=results,
                total_count=len(results),
                processing_time_ms=elapsed,
            )
            logger.info(f"Search completed in {elapsed:.1f}ms ({len(results)} hits)")
            return response

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    # ──────────────────────── stream ────────────────────────

    async def stream(self, request: StreamRequest) -> AsyncIterator[StreamChunk]:
        """
        Streaming RAG response - yields chunks as they arrive.
        """
        logger.info(f"Starting stream: {request.query[:50]}…")

        try:
            chunk_id = 0
            async for text in self._rag_service.stream_rag_pipeline(
                query=request.query,
                provider=self._provider,
                model=self._model,
                api_key=self._api_key,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                yield StreamChunk(
                    content=text,
                    chunk_id=chunk_id,
                    is_final=False,
                )
                chunk_id += 1

            # Final empty chunk to signal completion
            yield StreamChunk(content="", chunk_id=chunk_id, is_final=True)

        except Exception as e:
            logger.error(f"Stream failed: {e}")
            raise

    # ──────────────────────── status ────────────────────────

    async def get_status(self) -> StatusResponse:
        """Real status from actual service instances."""
        uptime = (datetime.now() - self._uptime_start).total_seconds() if self._uptime_start else 0.0
        return StatusResponse(
            is_ready=self._initialized,
            rag_engine_ready=self._rag_service is not None,
            llm_service_ready=self._llm_service is not None,
            cache_service_ready=True,  # no separate cache service yet
            uptime_seconds=uptime,
        )

    # ──────────────────── optional interface methods ────────────────────

    async def get_chat_history(self, session_id: str, limit: int = 20) -> list:
        """Return recent chat history for *session_id*."""
        return self._session_service.get_recent_history(session_id, max_messages=limit)

    async def clear_chat_session(self, session_id: str) -> bool:
        """Clear all messages in *session_id*."""
        return self._session_service.clear_session(session_id)

    async def get_knowledge_base_stats(self) -> dict:
        """Aggregate stats from DocumentService."""
        docs = self._doc_service.list_indexed_documents()
        return {
            "total_documents": len(docs),
            "documents": docs,
        }


class LocalAPI:
    """
    Public API for direct Python access.

    This is what tests and scripts use.
    It wraps ApplicationCore and provides a clean interface.

    Example:
        api = LocalAPI()
        await api.initialize()
        response = await api.query("What is RAG?")
        await api.shutdown()
    """

    def __init__(self, config: dict = None):
        """Initialize LocalAPI"""
        self._app = ApplicationCore(config)
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the application"""
        self._initialized = await self._app.initialize()
        return self._initialized

    async def shutdown(self) -> bool:
        """Shutdown the application"""
        return await self._app.shutdown()

    async def query(self, query_text: str, **kwargs) -> QueryResponse:
        """
        Simple query method for tests.

        Example:
            response = await api.query("What is RAG?")
        """
        request = QueryRequest(query=query_text, **kwargs)
        return await self._app.query(request)

    async def chat(self, message: str, session_id: str, **kwargs) -> ChatResponse:
        """
        Simple chat method for tests.

        Example:
            response = await api.chat("Follow up question", session_id="user123")
        """
        request = ChatRequest(message=message, session_id=session_id, **kwargs)
        return await self._app.chat(request)

    async def search(self, query_text: str, **kwargs) -> SearchResponse:
        """
        Simple search method.

        Example:
            response = await api.search("Document about RAG")
        """
        request = SearchRequest(query=query_text, **kwargs)
        return await self._app.search(request)

    async def stream(self, query_text: str, **kwargs) -> AsyncIterator[StreamChunk]:
        """
        Simple stream method.

        Example:
            async for chunk in api.stream("Long question"):
                print(chunk.content, end="")
        """
        request = StreamRequest(query=query_text, **kwargs)
        async for chunk in self._app.stream(request):
            yield chunk

    async def get_status(self) -> StatusResponse:
        """Get application status"""
        return await self._app.get_status()


# ═══════════════════════════════════════════════════════════
# Example Usage in Tests
# ═══════════════════════════════════════════════════════════
#
# # Test:
# @pytest.mark.asyncio
# async def test_query():
#     api = LocalAPI()
#     await api.initialize()
#
#     response = await api.query("What is RAG?")
#     assert response.content
#     assert response.status == ResponseStatus.SUCCESS
#
#     await api.shutdown()
#
# # Script:
# async def main():
#     api = LocalAPI()
#     await api.initialize()
#
#     response = await api.query("Hello?")
#     print(response.content)
#
#     await api.shutdown()
#
# if __name__ == "__main__":
#     asyncio.run(main())
