# -*- coding: utf-8 -*-
"""
ui_flet/state.py — Centralised application state
==================================================

Provides **AppState** (framework-agnostic mutable bag) used by ``app.py``
and the legacy ``get_state()`` helper for ``zena_flet.py``.

No framework imports here — both NiceGUI and Flet can depend on this.
"""

from __future__ import annotations

import copy
import logging
import uuid
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  Legacy dict-based state (kept for zena_flet.py compatibility)
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_STATE: dict[str, Any] = {
    "rag_content": "",
    "rag_sources": [],
    "rag_images": [],
    "rag_source_name": "",
    "rag_source_type": "",
    "rag_enabled": True,
    "active_panel": "chat",
    "chat_history": [],
    "is_streaming": False,
    "attachment": None,
    "active_model": "",
    "available_models": [],
    "council_mode": False,
    "deep_thinking": False,
    "quiet_cot": False,
    "voice_recording": False,
    "tts_enabled": False,
    "llm_online": False,
    "backend_online": False,
    "onboarded": False,
}


def get_state(page) -> dict[str, Any]:
    """Return the per-page state dict, initialising if needed."""
    if not hasattr(page, "data") or page.data is None:
        page.data = {}
    if "_state" not in page.data:
        page.data["_state"] = copy.deepcopy(DEFAULT_STATE)
    return page.data["_state"]


# ═══════════════════════════════════════════════════════════════════════════════
#  AppState — modern framework-agnostic state used by app.py
# ═══════════════════════════════════════════════════════════════════════════════


class AppState:
    """Observable, dict-backed application state.

    Access attributes naturally::

        state = AppState()
        state.dark_mode = True
        print(state.rag_content)

    Subscribe to changes::

        state.subscribe(lambda: rebuild_ui())
    """

    _DEFAULTS: dict[str, Any] = {
        # Identity
        "session_id": "",
        "app_version": "4.0.0 Pro",
        # Messages
        "messages": [],
        # RAG
        "rag_content": "",
        "rag_sources": [],
        "rag_images": [],
        "rag_source_name": "",
        "rag_source_type": "",
        "rag_enabled": True,
        "rag_pipeline_mode": "enhanced",
        "selected_source": "web",
        # UI
        "active_panel": "zena",
        "dark_mode": True,
        "app_language": "en",
        # Provider / Model
        "provider": "Local",
        "model": "",
        "api_key": "",
        # Settings
        "setting_temperature": 0.7,
        "setting_max_tokens": 2048,
        "setting_streaming": True,
        "setting_save_history": True,
        "setting_hybrid_search": True,
        "setting_hybrid_alpha": 0.5,
        "setting_chunking_strategy": "paragraph",
        "setting_enable_cache": True,
        "setting_enable_evaluation": True,
        # Smart modes
        "council_mode": False,
        "deep_thinking": False,
        # Voice
        "tts_enabled": False,
        "voice_recording": False,
        # Health
        "llm_online": False,
        "backend_online": False,
        # Gateways
        "telegram_enabled": False,
        "whatsapp_enabled": False,
        # Misc
        "last_url": "",
        "onboarded": False,
    }

    def __init__(self) -> None:
        object.__setattr__(self, "_data", copy.deepcopy(self._DEFAULTS))
        object.__setattr__(self, "_subscribers", [])
        self._data["session_id"] = uuid.uuid4().hex[:12]

    # ── Attribute access ──────────────────────────────────────────────────

    def __getattr__(self, name: str) -> Any:
        data = object.__getattribute__(self, "_data")
        if name in data:
            return data[name]
        raise AttributeError(f"AppState has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        data = object.__getattribute__(self, "_data")
        data[name] = value

    # ── Observer ──────────────────────────────────────────────────────────

    def subscribe(self, callback: Callable[[], Any]) -> None:
        self._subscribers.append(callback)

    def notify(self) -> None:
        for cb in self._subscribers:
            try:
                cb()
            except Exception:
                pass

    # ── Computed properties ───────────────────────────────────────────────

    @property
    def has_data(self) -> bool:
        return bool(self.rag_content or self.rag_sources)

    # ── Serialisation ─────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers used by panels
# ═══════════════════════════════════════════════════════════════════════════════


def get_llm_config(state: AppState) -> dict[str, Any]:
    """Build an LLM config dict from current state."""
    return {
        "provider": state.provider,
        "model": state.model,
        "api_key": state.api_key,
        "temperature": state.setting_temperature,
        "max_tokens": state.setting_max_tokens,
        "streaming": state.setting_streaming,
    }


def get_available_providers() -> list[str]:
    """Return names of configured LLM providers."""
    providers = ["Local"]
    try:
        import os
        if os.environ.get("OPENAI_API_KEY"):
            providers.append("OpenAI")
        if os.environ.get("ANTHROPIC_API_KEY"):
            providers.append("Anthropic")
    except Exception:
        pass
    return providers
