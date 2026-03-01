# -*- coding: utf-8 -*-
"""
ui_flet/persistence.py — Disk persistence for user preferences
================================================================

Saves/loads user settings to ``data/user_settings.json`` so they
survive across application restarts.
"""

from __future__ import annotations

import json
import logging
import tempfile
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = ROOT / "data" / "user_settings.json"

# Keys that are persisted to disk
_PERSISTENT_KEYS = (
    "onboarded",
    "dark_mode",
    "council_mode",
    "deep_thinking",
    "quiet_cot",
    "tts_enabled",
    "rag_enabled",
    "language",
)

# Lock to prevent concurrent read/write corruption
_settings_lock = threading.Lock()


def load_settings() -> dict[str, Any]:
    """Load saved settings from disk. Returns empty dict on error."""
    with _settings_lock:
        if not SETTINGS_FILE.exists():
            return {}
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return {k: v for k, v in data.items() if k in _PERSISTENT_KEYS}
        except Exception as exc:
            logger.warning("Could not load settings: %s", exc)
            return {}


def save_settings(state: dict[str, Any]) -> None:
    """Persist the relevant subset of *state* to disk (atomic write)."""
    with _settings_lock:
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {k: state[k] for k in _PERSISTENT_KEYS if k in state}
            content = json.dumps(data, indent=2, ensure_ascii=False)
            # Atomic write: write to temp file then rename
            fd, tmp_path = tempfile.mkstemp(
                dir=SETTINGS_FILE.parent, suffix=".tmp"
            )
            try:
                import os
                os.write(fd, content.encode("utf-8"))
                os.close(fd)
                Path(tmp_path).replace(SETTINGS_FILE)
            except Exception:
                os.close(fd) if not os.get_inheritable(fd) else None  # noqa
                Path(tmp_path).unlink(missing_ok=True)
                raise
            logger.info("Settings saved → %s", SETTINGS_FILE)
        except Exception as exc:
            logger.warning("Could not save settings: %s", exc)


def apply_settings(state: dict[str, Any]) -> None:
    """Load from disk and merge into *state* (disk wins)."""
    saved = load_settings()
    state.update(saved)
