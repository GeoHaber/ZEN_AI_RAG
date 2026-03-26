"""
Startup Package - Environment Initialization
=============================================
Handles initialization and dependency management for ZEN_RAG.

IMPORTANT: This package is lazy-loaded. No side effects occur on import.
All functions are called explicitly by the application.

Modules:
    dependency_check - Package installation and Tesseract setup
"""

from .dependency_check import (
    check_and_install_dependencies,
    setup_tesseract,
    find_tesseract,
    install_tesseract,
    get_latest_versions,
)

__all__ = [
    "check_and_install_dependencies",
    "setup_tesseract",
    "find_tesseract",
    "install_tesseract",
    "get_latest_versions",
]
