# -*- coding: utf-8 -*-
"""
test_utils.py - Shared test utilities for ZenAI
"""

import os
from pathlib import Path


def _default_models_dir() -> Path:
    """Resolve models directory: env var > config > project-local > fallback."""
    env = os.environ.get("ZENAI_MODEL_DIR", "")
    if env and Path(env).is_dir():
        return Path(env)
    # Try config system
    try:
        from config import MODEL_DIR
        if MODEL_DIR.is_dir():
            return MODEL_DIR
    except Exception:
        pass
    # Project-local models/
    local = Path(__file__).resolve().parent.parent / "models"
    if local.is_dir():
        return local
    return local  # return even if missing; callers check existence


def scan_models(models_dir=None):
    """Scan for available GGUF models in a directory and return Path objects."""
    if models_dir is None:
        models_path = _default_models_dir()
    else:
        models_path = Path(models_dir)
    if not models_path.exists():
        return []
    return list(models_path.glob("*.gguf"))
