"""
Content Extractor v2.1 — Modular Architecture (Facade)

This file maintains the backward-compatible API for content extraction
while delegating the actual work to specialized submodules in src.extractors.
"""

import logging
from typing import List, Dict, Tuple, Optional, Callable
from pathlib import Path

# Import from modularized extractors (absolute imports so the module works
# both as ``src.content_extractor`` and as top-level ``content_extractor``
# when src/ is on sys.path).
from extractors.markdown_converter import (
    HTMLToStructuredMarkdown,
)
from extractors.web_extractor import WebScanner
from extractors.file_extractor import (
    FolderScanner,
)

logger = logging.getLogger(__name__)

# Singletons/Default instances for backward compatibility
_html_converter = HTMLToStructuredMarkdown()


def scan_web(
    start_url: str,
    max_pages: int = 1,
    progress_callback: Optional[Callable] = None,
    page_callback: Optional[Callable] = None,
    **kwargs,
) -> Tuple[str, List[Dict], List[Dict]]:
    """Scan website and extract structured content."""
    scanner = WebScanner()
    return scanner.scan(
        start_url,
        max_pages=max_pages,
        progress_callback=progress_callback,
        page_callback=page_callback,
        completed_items=kwargs.get("completed_items"),
    )


def check_scan_path_allowed(folder: str) -> Optional[str]:
    """Validate folder path before scanning."""
    if not folder or not str(folder).strip():
        return "Folder path is empty"
    folder_path = Path(folder).resolve()
    if not folder_path.exists():
        return "Folder not found"
    if not folder_path.is_dir():
        return "Path is not a directory"
    # Call the class method directly if it exists, otherwise use a default implementation
    return FolderScanner._scan_blocked_reason(folder_path) if hasattr(FolderScanner, "_scan_blocked_reason") else None


def scan_folder(
    folder: str,
    progress_callback: Optional[Callable] = None,
    max_depth: int = 5,
    max_files: int = 500,
    **kwargs,
) -> Tuple[str, List[Dict], List[Dict]]:
    """Scan folder and extract content from all supported file types."""
    scanner = FolderScanner(max_depth=max_depth, max_files=max_files)
    return scanner.scan(
        folder,
        progress_callback=progress_callback,
        completed_items=kwargs.get("completed_items"),
    )


# Re-export helpers expected by other modules
_HAS_OCR = getattr(FolderScanner, '_HAS_OCR', False)


def count_files_in_path(folder: str, max_depth: int = 5) -> int:
    """Count files in a directory tree up to *max_depth* levels."""
    try:
        folder_path = Path(folder)
        if not folder_path.exists() or not folder_path.is_dir():
            return 0
        count = 0
        for item in folder_path.rglob("*"):
            if item.is_file():
                rel = item.relative_to(folder_path)
                if len(rel.parts) <= max_depth:
                    count += 1
        return count
    except Exception:
        return 0
