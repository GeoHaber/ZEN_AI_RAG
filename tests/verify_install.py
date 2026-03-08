#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
verify_install.py - ZEN_AI_RAG Installation Verification

Checks that all required dependencies are properly installed.
Run this after installation to verify everything is ready.

Usage:
    python verify_install.py
"""

import sys
import importlib
from pathlib import Path

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check_package(import_name: str, display_name: str, optional: bool = False) -> bool:
    """
    Check if a package is installed.

    Args:
        import_name: Name to use in import statement
        display_name: Human-friendly display name
        optional: If True, missing is a warning not error

    Returns:
        True if package found, False otherwise
    """
    try:
        __import__(import_name)
        status = f"{GREEN}✓{RESET}"
        category = "REQUIRED" if not optional else "OPTIONAL"
        # [X-Ray auto-fix] print(f"  {status} {display_name:45} [{category}]")
        return True
    except ImportError:
        status = f"{RED}✗{RESET}"
        category = "WARNING" if optional else "ERROR"
        # [X-Ray auto-fix] print(f"  {status} {display_name:45} [{category}]")
        return False


def check_file(filepath: str, display_name: str, optional: bool = False) -> bool:
    """Check if a file/directory exists."""
    path = Path(filepath)
    exists = path.exists()
    status = f"{GREEN}✓{RESET}" if exists else f"{RED}✗{RESET}"
    category = "WARNING" if optional and not exists else "REQUIRED" if not exists else "OK"
    # [X-Ray auto-fix] print(f"  {status} {display_name:45} [{category}]")
    return exists


def _do_do_main_setup_setup():
    """Helper: setup phase for _do_main_setup."""

    print("\n" + "=" * 85)
    # [X-Ray auto-fix] print(f"{BOLD}{CYAN}ZEN_AI_RAG Installation Verification{RESET}")
    print("=" * 85 + "\n")

    results = {
        "required": {"passed": 0, "failed": 0},
        "optional": {"passed": 0, "failed": 0},
        "files": {"passed": 0, "failed": 0},
    }

    # Core dependencies (required)
    # [X-Ray auto-fix] print(f"{BOLD}Core Dependencies (REQUIRED):{RESET}")
    core_packages = [
        ("nicegui", "NiceGUI - Web UI Framework"),
        ("uvicorn", "Uvicorn - ASGI Server"),
        ("requests", "Requests - HTTP Client"),
        ("httpx", "HTTPX - Async HTTP"),
        ("bs4", "BeautifulSoup4 - HTML Parsing"),
    ]
    for import_name, display_name in core_packages:
        if check_package(import_name, display_name):
            results["required"]["passed"] += 1
        else:
            results["required"]["failed"] += 1
    print()

    # LLM & RAG (required)
    # [X-Ray auto-fix] print(f"{BOLD}LLM & RAG Integration (REQUIRED):{RESET}")
    rag_packages = [
        ("qdrant_client", "Qdrant Client - Vector Database"),
        ("sentence_transformers", "Sentence Transformers - Embeddings"),
        ("rank_bm25", "BM25 - Ranking Algorithm"),
    ]
    for import_name, display_name in rag_packages:
        if check_package(import_name, display_name):
            results["required"]["passed"] += 1
        else:
            results["required"]["failed"] += 1
    print()

    return display_name, import_name, results


def _do_main_setup():
    """Helper: setup phase for main."""
    display_name, import_name, results = _do_do_main_setup_setup()
    # Document Processing (required)
    # [X-Ray auto-fix] print(f"{BOLD}Document Processing (REQUIRED):{RESET}")
    doc_packages = [
        ("PyPDF2", "PyPDF2 - PDF Processing"),
        ("fitz", "PyMuPDF - PDF/Image Processing"),
        ("pypdf", "PyPDF - Modern PDF Library"),
    ]
    for import_name, display_name in doc_packages:
        if check_package(import_name, display_name):
            results["required"]["passed"] += 1
        else:
            results["required"]["failed"] += 1
    print()

    # Audio (required for voice)
    # [X-Ray auto-fix] print(f"{BOLD}Audio Processing (REQUIRED for Voice):{RESET}")
    audio_packages = [
        ("faster_whisper", "Faster Whisper - STT"),
        ("piper", "Piper TTS - Text-to-Speech"),
        ("sounddevice", "SoundDevice - Audio I/O"),
    ]
    for import_name, display_name in audio_packages:
        if check_package(import_name, display_name):
            results["required"]["passed"] += 1
        else:
            results["required"]["failed"] += 1
    print()

    return display_name, import_name, results


def _do_main_init():
    """Helper: setup phase for main."""

    display_name, import_name, results = _do_main_setup()
    # ML & Utilities (required)
    # [X-Ray auto-fix] print(f"{BOLD}ML & Utilities (REQUIRED):{RESET}")
    util_packages = [
        ("numpy", "NumPy - Numerical Computing"),
        ("scipy", "SciPy - Scientific Computing"),
        ("pydantic", "Pydantic - Data Validation"),
        ("dotenv", "Python-dotenv - Config Management"),
    ]
    for import_name, display_name in util_packages:
        if check_package(import_name, display_name):
            results["required"]["passed"] += 1
        else:
            results["required"]["failed"] += 1
    print()

    # Testing (optional)
    # [X-Ray auto-fix] print(f"{BOLD}Testing Tools (OPTIONAL):{RESET}")
    test_packages = [
        ("pytest", "Pytest - Testing Framework"),
        ("pytest_asyncio", "Pytest AsyncIO - Async Testing"),
    ]
    for import_name, display_name in test_packages:
        if check_package(import_name, display_name, optional=True):
            results["optional"]["passed"] += 1
        else:
            results["optional"]["failed"] += 1
    print()

    # Vision (optional)
    # [X-Ray auto-fix] print(f"{BOLD}Vision Tools (OPTIONAL):{RESET}")
    vision_packages = [
        ("cv2", "OpenCV - Computer Vision"),
        ("PIL", "Pillow - Image Processing"),
    ]
    for import_name, display_name in vision_packages:
        if check_package(import_name, display_name, optional=True):
            results["optional"]["passed"] += 1
        else:
            results["optional"]["failed"] += 1
    print()

    return display_name, results


def main():
    """Run verification checks."""
    display_name, results = _do_main_init()
    # Directory structure
    # [X-Ray auto-fix] print(f"{BOLD}Directory Structure:{RESET}")
    dirs = [
        ("zena_mode", "Core application module"),
        ("ui", "UI components"),
        ("local_llm", "Local LLM management"),
        ("models", "AI model storage directory"),
        ("qdrant_storage", "Vector database storage"),
    ]
    for dirname, display_name in dirs:
        if check_file(dirname, display_name, optional=True):
            results["files"]["passed"] += 1
        else:
            results["files"]["failed"] += 1
    print()

    # Summary
    print("=" * 85)
    # [X-Ray auto-fix] print(f"{BOLD}Summary:{RESET}")
    print("=" * 85)

    required_ok = results["required"]["failed"] == 0
    results["optional"]["failed"] == 0

    print(
        f"\n  Required Packages: {GREEN}{results['required']['passed']}{RESET} passed, {RED}{results['required']['failed']}{RESET} failed"
    )
    print(
        f"  Optional Packages: {GREEN}{results['optional']['passed']}{RESET} passed, {YELLOW}{results['optional']['failed']}{RESET} warnings"
    )
    print(
        f"  Directory Structure: {GREEN}{results['files']['passed']}{RESET} OK, {YELLOW}{results['files']['failed']}{RESET} missing (optional)"
    )

    if required_ok:
        # [X-Ray auto-fix] print(f"\n{GREEN}{BOLD}✓ Installation Verified - Ready to Use!{RESET}")
        # [X-Ray auto-fix] print(f"\nNext: Run 'python zena.py' to start the application")
        print("=" * 85 + "\n")
        return 0
    else:
        # [X-Ray auto-fix] print(f"\n{RED}{BOLD}✗ Installation Failed - Missing required packages{RESET}")
        # [X-Ray auto-fix] print(f"\nFix with: pip install -r requirements.txt")
        print("=" * 85 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
