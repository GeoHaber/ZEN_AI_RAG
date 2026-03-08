# -*- coding: utf-8 -*-
"""
pdf_extractor.py - Extract text from PDF files for RAG indexing
"""

import logging
from pathlib import Path
from typing import Optional
import PyPDF2

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text from PDF files."""

    @staticmethod
    def extract_text(pdf_path: Path) -> Optional[str]:
        """
        Extract text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text or None if failed
        """
        try:
            with open(pdf_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)

                text_parts = []
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    except Exception as e:
                        logger.warning(f"[PDF] Failed to extract page {page_num}: {e}")

                full_text = "\n\n".join(text_parts)

                if full_text:
                    logger.info(f"[PDF] Extracted {len(full_text)} chars from {pdf_path.name}")
                    return full_text
                else:
                    logger.warning(f"[PDF] No text extracted from {pdf_path.name}")
                    return None

        except Exception as e:
            logger.error(f"[PDF] Failed to read {pdf_path}: {e}")
            return None

    @staticmethod
    def is_pdf(filename: str) -> bool:
        """Check if file is a PDF."""
        return filename.lower().endswith(".pdf")
