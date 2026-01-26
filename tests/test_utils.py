# -*- coding: utf-8 -*-
"""
test_utils.py - Shared test utilities for ZenAI
"""
import os
from pathlib import Path

def scan_models(models_dir="C:/AI/Models"):
    """Scan for available GGUF models in a directory and return Path objects."""
    models_path = Path(models_dir)
    if not models_path.exists():
        return []
    return list(models_path.glob("*.gguf"))

# Add other shared test helpers here if needed
