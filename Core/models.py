"""
Core Application Models
Defines the request/response DTOs used throughout the application.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ResponseStatus(str, Enum):
    """Response status codes"""

    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


@dataclass
class QueryRequest:
    """Request for a query operation"""

    query: str
    include_sources: bool = True
    max_tokens: int = 1024
    temperature: float = 0.7
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate request"""
        if not self.query or not self.query.strip():
            raise ValueError("Query cannot be empty")
        if self.temperature < 0 or self.temperature > 1:
            raise ValueError("Temperature must be between 0 and 1")


@dataclass
class QueryResponse:
    """Response from a query operation"""

    content: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    status: ResponseStatus = ResponseStatus.SUCCESS
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    token_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatRequest:
    """Request for a chat operation"""

    message: str
    session_id: str
    include_history: bool = True
    max_history: int = 10
    max_tokens: int = 1024
    temperature: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate request"""
        if not self.message or not self.message.strip():
            raise ValueError("Message cannot be empty")
        if not self.session_id:
            raise ValueError("Session ID is required")


@dataclass
class ChatMessage:
    """Single chat message"""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    """Response from a chat operation"""

    message: ChatMessage
    history: List[ChatMessage] = field(default_factory=list)
    status: ResponseStatus = ResponseStatus.SUCCESS
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    token_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchRequest:
    """Request for a search operation"""

    query: str
    limit: int = 10
    threshold: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate request"""
        if not self.query or not self.query.strip():
            raise ValueError("Query cannot be empty")
        if self.limit <= 0:
            raise ValueError("Limit must be positive")
        if self.threshold < 0 or self.threshold > 1:
            raise ValueError("Threshold must be between 0 and 1")


@dataclass
class SearchResult:
    """Single search result"""

    content: str
    score: float
    document_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """Response from a search operation"""

    results: List[SearchResult] = field(default_factory=list)
    total_count: int = 0
    status: ResponseStatus = ResponseStatus.SUCCESS
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamRequest:
    """Request for a streaming operation"""

    query: str
    max_tokens: int = 2048
    temperature: float = 0.7
    include_sources: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """Single chunk in a stream"""

    content: str
    chunk_id: int
    is_final: bool = False
    sources: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class StatusResponse:
    """Status of the application"""

    is_ready: bool
    rag_engine_ready: bool
    llm_service_ready: bool
    cache_service_ready: bool
    error_message: Optional[str] = None
    uptime_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
