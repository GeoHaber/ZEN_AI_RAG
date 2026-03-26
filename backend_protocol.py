# -*- coding: utf-8 -*-
"""
backend_protocol.py — Shared Backend Interface
================================================

Defines the `UIBackend` protocol: every backend operation that ANY UI
(NiceGUI, Flet, FastAPI, CLI) can call.  Both ``zena.py`` and ``app.py``
should route through a concrete implementation of this protocol so that
feature parity is guaranteed.

Usage::

    from backend_protocol import UIBackend
    from backend_impl import create_backend

    backend: UIBackend = create_backend()
    answer = await backend.chat("What is RAG?")
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ─── Data containers ─────────────────────────────────────────────────────────


@dataclass
class RAGResult:
    """Unified RAG query result returned by the backend."""

    answer: str = ""
    context: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    hallucination_score: float = 0.0
    conflicts: list[str] = field(default_factory=list)
    mode: str = "classic"
    intent: str = ""
    stages: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    cached: bool = False


@dataclass
class ModelInfo:
    """Describes a local or remote LLM model."""

    name: str = ""
    filename: str = ""
    description: str = ""
    size: str = ""
    icon: str = "🤖"
    good_for: list[str] = field(default_factory=list)
    speed: str = ""
    quality: str = ""
    repo_id: str = ""


@dataclass
class HealthStatus:
    """Backend health check result."""

    llm_online: bool = False
    hub_online: bool = False
    rag_ready: bool = False
    model_name: str = ""
    error: str = ""


@dataclass
class ScanResult:
    """Result of a web/folder/email scan."""

    text: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
    images: list[Any] = field(default_factory=list)
    chunks: int = 0
    elapsed_s: float = 0.0


# ─── Protocol ─────────────────────────────────────────────────────────────────


@runtime_checkable
class UIBackend(Protocol):
    """Every operation the UI can request from the backend.

    Both NiceGUI (zena.py) and Flet (app.py) import this and call
    the same methods, guaranteeing feature parity.
    """

    # ── Chat ──────────────────────────────────────────────────────────────

    async def chat(
        self,
        prompt: str,
        *,
        session_id: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        rag_enabled: bool = True,
        rag_mode: str = "enhanced",
        streaming: bool = False,
    ) -> RAGResult:
        """Send a chat message and get a response (optionally RAG-augmented)."""
        ...

    async def chat_stream(
        self,
        prompt: str,
        *,
        session_id: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        rag_enabled: bool = True,
        rag_mode: str = "enhanced",
    ) -> AsyncIterator[str]:
        """Stream chat tokens one at a time."""
        ...

    async def council_chat(
        self, prompt: str, *, mode: str = "council"
    ) -> dict[str, Any]:
        """Route prompt through multi-expert swarm/council."""
        ...

    # ── RAG Scanning ─────────────────────────────────────────────────────

    async def scan_web(self, url: str, *, max_pages: int = 10) -> ScanResult:
        """Scrape a website and index into RAG."""
        ...

    async def scan_folder(self, path: str, *, max_files: int = 500) -> ScanResult:
        """Scan a local directory and index into RAG."""
        ...

    async def scan_email(
        self, path_or_config: str, *, mode: str = "local"
    ) -> ScanResult:
        """Ingest emails (.mbox/.pst or IMAP) into RAG."""
        ...

    async def build_index(self, documents: list[str]) -> None:
        """Build (or rebuild) the RAG vector index."""
        ...

    # ── RAG Query (raw, without LLM) ─────────────────────────────────────

    async def rag_search(
        self, query: str, *, top_k: int = 5, alpha: float = 0.5
    ) -> list[dict[str, Any]]:
        """Hybrid search the RAG index (no LLM generation)."""
        ...

    async def rag_stats(self) -> dict[str, Any]:
        """Return index stats: chunk count, sources, collection info."""
        ...

    async def rag_cleanup(self) -> dict[str, Any]:
        """Detect and optionally remove conflicting/duplicate docs."""
        ...

    async def rag_dedup(self) -> dict[str, Any]:
        """Find and report duplicate content in the index."""
        ...

    # ── Models ────────────────────────────────────────────────────────────

    async def list_models(self) -> list[ModelInfo]:
        """List locally available LLM models."""
        ...

    async def load_model(self, filename: str) -> bool:
        """Load / switch to a specific model."""
        ...

    async def download_model(
        self, repo_id: str, filename: str
    ) -> dict[str, Any]:
        """Download a model from HuggingFace."""
        ...

    # ── Voice ─────────────────────────────────────────────────────────────

    async def speak(self, text: str) -> dict[str, Any]:
        """Text-to-speech: returns {audio_url, success, error}."""
        ...

    async def voice_devices(self) -> list[dict[str, Any]]:
        """List available audio input devices."""
        ...

    # ── Health & Diagnostics ──────────────────────────────────────────────

    async def health(self) -> HealthStatus:
        """Check backend health (LLM, Hub, RAG)."""
        ...

    async def benchmark(self) -> dict[str, Any]:
        """Run a quick LLM speed benchmark (tok/s)."""
        ...

    # ── Conversation Memory ───────────────────────────────────────────────

    async def save_message(
        self, role: str, content: str, *, session_id: str = ""
    ) -> None:
        """Persist a message to conversation memory."""
        ...

    async def build_context(
        self, prompt: str, *, session_id: str = ""
    ) -> str:
        """Build contextual prompt from conversation history."""
        ...

    # ── Evaluation & Cache ────────────────────────────────────────────────

    async def cache_stats(self) -> dict[str, Any]:
        """Return semantic cache statistics."""
        ...

    async def eval_stats(self) -> dict[str, Any]:
        """Return evaluation metrics."""
        ...

    # ── Background Services ───────────────────────────────────────────────

    async def start_gateways(self) -> dict[str, bool]:
        """Start Telegram/WhatsApp gateways if configured."""
        ...

    async def check_updates(self) -> dict[str, Any]:
        """Check for app/model updates."""
        ...

    # ── File Extraction ───────────────────────────────────────────────────

    async def extract_text(
        self, data: bytes, filename: str
    ) -> str:
        """Extract text from an uploaded file (PDF, DOCX, image, etc.)."""
        ...
