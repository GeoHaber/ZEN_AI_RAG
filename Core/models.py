"""
Core Application Models — Typed DTOs for ZEN_AI_RAG.

Defines the request/response data-transfer objects used throughout the
application. Every interaction (test, UI, API) uses these models.

Adapted from RAG_RAT/Core/models.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ResponseStatus(str, Enum):
    """Response status codes."""

    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


# ─── Query ───────────────────────────────────────────────


@dataclass
class QueryRequest:
    """Request for a single query with optional RAG context."""

    query: str
    include_sources: bool = True
    max_tokens: int = 1024
    temperature: float = 0.7
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.query or not self.query.strip():
            raise ValueError("Query cannot be empty")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("Temperature must be between 0 and 2")


@dataclass
class QueryResponse:
    """Response from a query operation."""

    content: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    status: ResponseStatus = ResponseStatus.SUCCESS
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    token_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ─── Chat ────────────────────────────────────────────────


@dataclass
class ChatMessage:
    """Single chat message."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatRequest:
    """Request for a chat operation with conversation memory."""

    message: str
    session_id: str
    include_history: bool = True
    max_history: int = 10
    max_tokens: int = 1024
    temperature: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.message or not self.message.strip():
            raise ValueError("Message cannot be empty")
        if not self.session_id:
            raise ValueError("Session ID is required")


@dataclass
class ChatResponse:
    """Response from a chat operation."""

    message: ChatMessage
    history: List[ChatMessage] = field(default_factory=list)
    status: ResponseStatus = ResponseStatus.SUCCESS
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    token_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ─── Search ──────────────────────────────────────────────


@dataclass
class SearchRequest:
    """Request for a RAG knowledge-base search."""

    query: str
    limit: int = 10
    threshold: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.query or not self.query.strip():
            raise ValueError("Query cannot be empty")
        if self.limit <= 0:
            raise ValueError("Limit must be positive")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("Threshold must be between 0 and 1")


@dataclass
class SearchResult:
    """Single search result."""

    content: str
    score: float
    document_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """Response from a search operation."""

    results: List[SearchResult] = field(default_factory=list)
    total_count: int = 0
    status: ResponseStatus = ResponseStatus.SUCCESS
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ─── Streaming ───────────────────────────────────────────


@dataclass
class StreamRequest:
    """Request for a streaming operation."""

    query: str
    max_tokens: int = 2048
    temperature: float = 0.7
    include_sources: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """Single chunk in a streaming response."""

    content: str
    chunk_id: int
    is_final: bool = False
    sources: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


# ─── Status ──────────────────────────────────────────────


@dataclass
class StatusResponse:
    """Application status response."""

    status: ResponseStatus = ResponseStatus.SUCCESS
    components: Dict[str, Any] = field(default_factory=dict)
    uptime_seconds: float = 0.0
    version: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
