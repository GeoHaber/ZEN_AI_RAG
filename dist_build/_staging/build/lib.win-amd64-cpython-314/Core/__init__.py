"""
Core package - Business logic, domain models, and service layer.

Adapted from RAG_RAT's proven Clean Architecture pattern.
Provides the foundational types, exceptions, and service abstractions
used throughout ZEN_AI_RAG.
"""

from Core.models import (
    ResponseStatus,
    QueryRequest, QueryResponse,
    ChatRequest, ChatResponse, ChatMessage,
    SearchRequest, SearchResult, SearchResponse,
    StreamRequest, StreamChunk,
    StatusResponse,
)

from Core.exceptions import (
    ZenAIError,
    ConfigurationError,
    ProviderError,
    AuthenticationError,
    LLMError,
    RAGError,
    DocumentError,
    ValidationError,
)

__all__ = [
    # Models
    "ResponseStatus",
    "QueryRequest", "QueryResponse",
    "ChatRequest", "ChatResponse", "ChatMessage",
    "SearchRequest", "SearchResult", "SearchResponse",
    "StreamRequest", "StreamChunk",
    "StatusResponse",
    # Exceptions
    "ZenAIError",
    "ConfigurationError",
    "ProviderError",
    "AuthenticationError",
    "LLMError",
    "RAGError",
    "DocumentError",
    "ValidationError",
]
