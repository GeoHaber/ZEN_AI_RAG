"""
Document Service — Document Management & Processing.

Responsibility: Index, retrieve, and manage documents.
  - Document indexing (text and files)
  - Text extraction
  - Metadata management

Pure Python, type hinted, fully testable.
Adapted from RAG_RAT/Core/services/document_service.py.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from Core.exceptions import DocumentError, ValidationError

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Service for document management.

    Pure business logic — no UI dependencies.
    """

    SUPPORTED_FORMATS = {
        ".txt": "text/plain",
        ".pdf": "application/pdf",
        ".md": "text/markdown",
        ".json": "application/json",
        ".csv": "text/csv",
        ".py": "text/x-python",
        ".html": "text/html",
        ".xml": "text/xml",
        ".rst": "text/x-rst",
        ".rtf": "application/rtf",
    }

    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            try:
                from config_system import config

                storage_dir = config.BASE_DIR / "rag_storage"
            except ImportError:
                storage_dir = Path.cwd() / "rag_storage"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.storage_dir / ".metadata.json"
        logger.info(f"✓ DocumentService initialized: {self.storage_dir}")

    # ─── Index text ──────────────────────────────────────

    def index_text(
        self,
        text: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Index raw text content.

        Returns:
            Document ID.
        """
        if not text or not text.strip():
            raise ValidationError("Text cannot be empty", field="text")
        if not source or not source.strip():
            raise ValidationError("Source cannot be empty", field="source")
        if len(text) > 10 * 1024 * 1024:
            raise ValidationError("Text too large (max 10 MB)", field="text")

        try:
            doc_id = self._generate_id()
            doc_meta = {
                "id": doc_id,
                "name": f"{source}_{doc_id}",
                "source": source,
                "format": "text",
                "size": len(text),
                "created_at": datetime.now().isoformat(),
                "indexed": True,
            }
            if metadata:
                doc_meta.update(metadata)

            content_path = self.storage_dir / f"{doc_id}.txt"
            content_path.write_text(text, encoding="utf-8")
            self._save_metadata(doc_id, doc_meta)

            logger.info(f"✓ Indexed text: {doc_id} ({len(text)} chars)")
            return doc_id
        except (ValidationError, DocumentError):
            raise
        except Exception as exc:
            raise DocumentError(f"Failed to index text: {exc}", file_path=source)

    # ─── Index file ──────────────────────────────────────

    def index_file(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Index a file.

        Returns:
            Document ID.
        """
        fp = Path(file_path)
        if not fp.exists():
            raise DocumentError(f"File not found: {fp}", file_path=str(fp))
        if fp.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise DocumentError(
                f"Unsupported format: {fp.suffix}",
                file_path=str(fp),
                format=fp.suffix,
            )
        if fp.stat().st_size > self.MAX_FILE_SIZE:
            raise ValidationError(
                f"File too large ({fp.stat().st_size} bytes)",
                field="file_size",
            )

        try:
            text = self.extract_text(str(fp))
            return self.index_text(
                text,
                source=fp.name,
                metadata={
                    "original_path": str(fp),
                    "file_format": fp.suffix,
                    **(metadata or {}),
                },
            )
        except (ValidationError, DocumentError):
            raise
        except Exception as exc:
            raise DocumentError(f"Failed to index file: {exc}", file_path=str(fp))

    # ─── Text extraction ────────────────────────────────

    def extract_text(self, file_path: str) -> str:
        """Extract text from a file."""
        fp = Path(file_path)
        suffix = fp.suffix.lower()

        try:
            if suffix == ".pdf":
                return self._extract_pdf(fp)
            return fp.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            raise DocumentError(f"Extraction failed: {exc}", file_path=str(fp))

    # ─── Listing ─────────────────────────────────────────

    def list_indexed_documents(self) -> List[Dict[str, Any]]:
        """List all indexed documents."""
        all_meta = self._load_all_metadata()
        return list(all_meta.values())

    # ─── Private helpers ─────────────────────────────────

    @staticmethod
    def _generate_id() -> str:
        return str(uuid.uuid4())[:8]

    @staticmethod
    def _extract_pdf(path: Path) -> str:
        """Extract text from PDF using PyMuPDF (fitz) if available."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(path))
            pages = [page.get_text() for page in doc]
            doc.close()
            return "\n\n".join(pages)
        except ImportError:
            try:
                from pypdf import PdfReader

                reader = PdfReader(str(path))
                return "\n\n".join(p.extract_text() or "" for p in reader.pages)
            except ImportError:
                raise DocumentError(
                    "No PDF library available (install PyMuPDF or pypdf)",
                    file_path=str(path),
                    format=".pdf",
                )

    def _save_metadata(self, doc_id: str, meta: Dict[str, Any]) -> None:
        all_meta = self._load_all_metadata()
        all_meta[doc_id] = meta
        self.metadata_file.write_text(json.dumps(all_meta, indent=2), encoding="utf-8")

    def _load_all_metadata(self) -> Dict[str, Any]:
        if self.metadata_file.exists():
            try:
                return json.loads(self.metadata_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}
