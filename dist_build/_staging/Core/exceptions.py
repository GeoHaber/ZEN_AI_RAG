"""
Unified Exception Hierarchy for ZEN_AI_RAG.

All exceptions are defined here.  No silent failures — always raise with
clear messages.  Callers (UI layer, API handlers) decide how to present
each exception type.

Hierarchy::

    ZenAIError (base)
    ├── ConfigurationError   (config / setup issues)
    ├── ProviderError        (provider connection / availability)
    ├── AuthenticationError  (API keys, credentials)
    ├── LLMError             (LLM provider failures)
    ├── RAGError             (RAG pipeline failures)
    ├── DocumentError        (document processing)
    └── ValidationError      (invalid user input)

Adapted from RAG_RAT/Core/exceptions.py.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class ZenAIError(Exception):
    """Base exception for all ZEN_AI_RAG errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details: Dict[str, Any] = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} ({self.error_code}): {self.details}"
        return f"{self.message} ({self.error_code})"


class ConfigurationError(ZenAIError):
    """Configuration is invalid or incomplete."""

    def __init__(self, message: str, missing_config: Optional[str] = None):
        super().__init__(message, "CONFIG_ERROR")
        if missing_config:
            self.details["missing"] = missing_config


class ProviderError(ZenAIError):
    """LLM provider is unavailable or not configured."""

    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(message, "PROVIDER_ERROR")
        if provider:
            self.details["provider"] = provider


class AuthenticationError(ZenAIError):
    """Authentication failed (API key, credentials)."""

    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(message, "AUTH_ERROR")
        if provider:
            self.details["provider"] = provider


class LLMError(ZenAIError):
    """LLM call failed (API error, timeout, rate limit, etc.)."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        super().__init__(message, "LLM_ERROR")
        if provider:
            self.details["provider"] = provider
        if status_code:
            self.details["status_code"] = status_code


class RAGError(ZenAIError):
    """RAG pipeline failed (retrieval, augmentation, generation)."""

    def __init__(self, message: str, stage: Optional[str] = None):
        super().__init__(message, "RAG_ERROR")
        if stage:
            self.details["stage"] = stage


class DocumentError(ZenAIError):
    """Document processing failed."""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        format: Optional[str] = None,
    ):
        super().__init__(message, "DOCUMENT_ERROR")
        if file_path:
            self.details["file"] = file_path
        if format:
            self.details["format"] = format


class ValidationError(ZenAIError):
    """Input validation failed."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, "VALIDATION_ERROR")
        if field:
            self.details["field"] = field
