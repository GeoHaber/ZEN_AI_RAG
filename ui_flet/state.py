# -*- coding: utf-8 -*-
"""
ui_flet/state.py — Centralised application state
==================================================

All mutable runtime state lives in ``page.data["_state"]``.
This module defines the default shape and helper accessors.
"""

from __future__ import annotations

import copy
from typing import Any

DEFAULT_STATE: dict[str, Any] = {
    # ── RAG data ──────────────────────────────────────────────────────────
    "rag_content": "",
    "rag_sources": [],
    "rag_images": [],
    "rag_source_name": "",
    "rag_source_type": "",
    "rag_enabled": True,
    # ── UI navigation ────────────────────────────────────────────────────
    "active_panel": "chat",
    # ── Chat ──────────────────────────────────────────────────────────────
    "chat_history": [],
    "is_streaming": False,
    "attachment": None,
    # ── Models ────────────────────────────────────────────────────────────
    "active_model": "",
    "available_models": [],
    # ── Smart mode ────────────────────────────────────────────────────────
    "council_mode": False,
    "deep_thinking": False,
    "quiet_cot": False,
    # ── Voice ─────────────────────────────────────────────────────────────
    "voice_recording": False,
    "tts_enabled": False,
    # ── Backend health ────────────────────────────────────────────────────
    "llm_online": False,
    "backend_online": False,
    # ── Onboarding ────────────────────────────────────────────────────────
    "onboarded": False,
}


def get_state(page) -> dict[str, Any]:
    """Return the per-page state dict, initialising if needed."""
    if not hasattr(page, "data") or page.data is None:
        page.data = {}
    if "_state" not in page.data:
        page.data["_state"] = copy.deepcopy(DEFAULT_STATE)
    return page.data["_state"]
