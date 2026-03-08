"""
directory_scanner.py - Local directory RAG indexing
"""

import os
import time
from pathlib import Path
from typing import List, Dict
import logging
import sys

# Add root to path for utils import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import safe_print

logger = logging.getLogger(__name__)


class DirectoryScanner:
    """DirectoryScanner class."""

    def __init__(self, root_dir: str):
        """Initialize instance."""
        self.root_dir = Path(root_dir)
        self.documents = []
        self.supported_extensions = {
            ".txt",
            ".md",
            ".py",
            ".js",
            ".html",
            ".css",
            ".json",
            ".xml",
            ".csv",
            ".log",
            ".yaml",
            ".yml",
            ".ini",
            ".cfg",
            ".conf",
            ".rst",
            ".tex",
            ".sh",
            ".bat",
            ".ps1",
            ".c",
            ".cpp",
            ".h",
            ".java",
            ".go",
            ".rs",
            ".php",
            ".rb",
            ".swift",
            ".kt",
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".bmp",
            ".tiff",
            ".webp",
        }
        self.skip_dirs = {
            "__pycache__",
            ".git",
            ".svn",
            "node_modules",
            ".venv",
            "venv",
            "env",
            ".env",
            "dist",
            "build",
            ".idea",
            ".vscode",
            "target",
            ".cache",
            "cache",
            "tmp",
            "temp",
            ".pytest_cache",
            ".mypy_cache",
        }
        self.max_file_size = 10 * 1024 * 1024  # 10 MB max for text files
        self.max_pdf_size = 50 * 1024 * 1024  # 50 MB max for PDFs

        # Initialize UniversalExtractor for heavy lifting
        try:
            from .universal_extractor import UniversalExtractor

            self.extractor = UniversalExtractor()
        except ImportError:
            self.extractor = None
            logger.warning("[DirScanner] UniversalExtractor not found, PDF/Image OCR disabled")

    def should_skip_dir(self, dir_path: Path) -> bool:
        """Check if directory should be skipped."""
        return dir_path.name in self.skip_dirs or dir_path.name.startswith(".")

    def should_index_file(self, file_path: Path) -> bool:
        """Check if file should be indexed."""
        suffix = file_path.suffix.lower()
        if suffix not in self.supported_extensions:
            return False

        # Check size based on type
        try:
            size_limit = self.max_pdf_size if suffix == ".pdf" else self.max_file_size
            if file_path.stat().st_size > size_limit:
                logger.debug(f"[DirScanner] Skipping large file: {file_path}")
                return False
        except Exception:
            return False

        return True

    def read_file_safe(self, file_path: Path) -> str:
        """Safely read file content based on type."""
        suffix = file_path.suffix.lower()

        # 1. Handle PDFs and Images via UniversalExtractor
        if suffix in {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"} and self.extractor:
            try:
                chunks, stats = self.extractor.process(file_path)
                if chunks:
                    # Join chunks with double newline for RAG builder to re-chunk correctly
                    return "\n\n".join([c.text for c in chunks])
                return ""
            except Exception as e:
                logger.error(f"[DirScanner] Extraction failed for {file_path}: {e}")
                return ""

        # 2. Handle standard text files
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                logger.error(f"[DirScanner] Error reading {file_path}: {e}")
                return ""

        return ""


def _scan_part1_part2(self):
    """Scan part1 part 2."""

    def get_stats(self) -> Dict:
        """Get scanning statistics."""
        if not self.documents:
            return {}

        extensions = {}
        for doc in self.documents:
            ext = doc["extension"]
            extensions[ext] = extensions.get(ext, 0) + 1

        return {
            "total_files": len(self.documents),
            "total_size": sum(doc["size"] for doc in self.documents),
            "extensions": extensions,
            "root_dir": str(self.root_dir),
        }

    def check_project_dependencies(self):
        """Analyze project imports and check for updates."""
        try:
            # Import our new manager
            import sys

            sys.path.append(str(self.root_dir))
            try:
                import dependency_manager

                safe_print(f"\n📦 Analyzing dependencies for: {self.root_dir}")
                dependency_manager.generate_requirements(self.root_dir)
                dependency_manager.check_updates()
                return True
            except ImportError:
                logger.error("[DirScanner] dependency_manager.py not found in project root")
                return False
        except Exception as e:
            logger.error(f"[DirScanner] Dependency check failed: {e}")
            return False


def _scan_part1(self):
    """Scan part 1."""

    logger.info(f"[DirScanner] ✅ Completed: {len(self.documents)} files in {total_time:.2f}s")
    logger.info(f"[DirScanner] Total content: {total_size / 1024:.1f} KB ({total_size / (1024 * 1024):.2f} MB)")

    return self.documents

    def scan(self, max_files: int = 1000) -> List[Dict]:
        """Recursively scan directory and extract text content."""
        start_time = time.time()
        file_count = 0

        logger.info(f"[DirScanner] Starting scan of {self.root_dir}")

        for root, dirs, files in os.walk(self.root_dir):
            root_path = Path(root)

            # Filter out directories to skip
            dirs[:] = [d for d in dirs if not self.should_skip_dir(root_path / d)]

            for file in files:
                if file_count < max_files:
                    continue
                logger.info(f"[DirScanner] Reached max files limit: {max_files}")
                break

                file_path = root_path / file

                if not self.should_index_file(file_path):
                    continue

                try:
                    file_start = time.time()
                    content = self.read_file_safe(file_path)

                    if len(content) > 50:  # Skip empty/tiny files
                        relative_path = file_path.relative_to(self.root_dir)

                        self.documents.append(
                            {
                                "url": str(file_path),
                                "title": str(relative_path),
                                "content": content,
                                "extension": file_path.suffix,
                                "size": len(content),
                            }
                        )

                        file_time = time.time() - file_start
                        file_count += 1

                        if file_count % 100 == 0:
                            logger.info(f"[DirScanner] Indexed {file_count} files...")

                        logger.debug(
                            f"[DirScanner] ✅ Indexed: {relative_path} ({len(content)} chars) | Time: {file_time:.2f}s"
                        )

                except Exception as e:
                    logger.error(f"[DirScanner] Error processing {file_path}: {e}")

            if file_count >= max_files:
                break

        time.time() - start_time
        sum(doc["size"] for doc in self.documents)
        _scan_part1(self)

    _scan_part1_part2(self)
