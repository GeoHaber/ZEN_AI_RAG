# -*- coding: utf-8 -*-
"""
test_pdf_extraction.py - Comprehensive tests for PDF text extraction
Tests valid PDFs, corrupted files, empty PDFs, multi-page documents
"""

import pytest
from pathlib import Path
from zena_mode.pdf_extractor import PDFExtractor
import PyPDF2
from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io


class TestPDFExtractor:
    """Test PDF text extraction functionality."""

    @pytest.fixture
    def sample_pdf(self, tmp_path):
        """Create a sample PDF with text."""
        pdf_path = tmp_path / "sample.pdf"

        # Create PDF with reportlab
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "This is a test PDF document.")
        c.drawString(100, 730, "It contains multiple lines of text.")
        c.showPage()
        c.save()

        # Write to file
        pdf_path.write_bytes(buffer.getvalue())
        return pdf_path

    @pytest.fixture
    def multi_page_pdf(self, tmp_path):
        """Create a multi-page PDF."""
        pdf_path = tmp_path / "multipage.pdf"

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)

        # Page 1
        c.drawString(100, 750, "Page 1: Introduction")
        c.drawString(100, 730, "This is the first page.")
        c.showPage()

        # Page 2
        c.drawString(100, 750, "Page 2: Content")
        c.drawString(100, 730, "This is the second page.")
        c.showPage()

        # Page 3
        c.drawString(100, 750, "Page 3: Conclusion")
        c.drawString(100, 730, "This is the final page.")
        c.showPage()

        c.save()
        pdf_path.write_bytes(buffer.getvalue())
        return pdf_path

    @pytest.fixture
    def empty_pdf(self, tmp_path):
        """Create an empty PDF with no text."""
        pdf_path = tmp_path / "empty.pdf"

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.showPage()  # Empty page
        c.save()

        pdf_path.write_bytes(buffer.getvalue())
        return pdf_path

    def test_extract_text_from_valid_pdf(self, sample_pdf):
        """Test extracting text from valid PDF."""
        text = PDFExtractor.extract_text(sample_pdf)

        assert text is not None
        assert "test PDF document" in text
        assert "multiple lines" in text

    def test_extract_text_from_multi_page_pdf(self, multi_page_pdf):
        """Test extracting text from multi-page PDF."""
        text = PDFExtractor.extract_text(multi_page_pdf)

        assert text is not None
        assert "Page 1" in text
        assert "Page 2" in text
        assert "Page 3" in text
        assert "Introduction" in text
        assert "Conclusion" in text

    def test_extract_text_from_empty_pdf(self, empty_pdf):
        """Test extracting text from empty PDF."""
        text = PDFExtractor.extract_text(empty_pdf)

        # Empty PDF should return None or empty string
        assert text is None or text.strip() == ""

    def test_extract_text_from_nonexistent_file(self, tmp_path):
        """Test extracting text from non-existent file."""
        pdf_path = tmp_path / "nonexistent.pdf"
        text = PDFExtractor.extract_text(pdf_path)

        assert text is None

    def test_extract_text_from_corrupted_file(self, tmp_path):
        """Test extracting text from corrupted PDF."""
        pdf_path = tmp_path / "corrupted.pdf"
        pdf_path.write_bytes(b"This is not a valid PDF file")

        text = PDFExtractor.extract_text(pdf_path)

        assert text is None  # Should handle gracefully

    def test_is_pdf_valid_extension(self):
        """Test PDF file detection."""
        assert PDFExtractor.is_pdf("document.pdf") is True
        assert PDFExtractor.is_pdf("document.PDF") is True
        assert PDFExtractor.is_pdf("file.Pdf") is True

    def test_is_pdf_invalid_extension(self):
        """Test non-PDF file detection."""
        assert PDFExtractor.is_pdf("document.txt") is False
        assert PDFExtractor.is_pdf("image.jpg") is False
        assert PDFExtractor.is_pdf("data.json") is False

    def test_extract_text_preserves_structure(self, multi_page_pdf):
        """Test that extracted text preserves page structure."""
        text = PDFExtractor.extract_text(multi_page_pdf)

        # Pages should be separated
        assert "\n\n" in text or text.count("Page") == 3

    def test_extract_large_pdf(self, tmp_path):
        """Test extracting text from large PDF (10 pages)."""
        pdf_path = tmp_path / "large.pdf"

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)

        for i in range(10):
            c.drawString(100, 750, f"Page {i + 1}")
            c.drawString(100, 730, f"Content for page {i + 1}" * 10)
            c.showPage()

        c.save()
        pdf_path.write_bytes(buffer.getvalue())

        text = PDFExtractor.extract_text(pdf_path)

        assert text is not None
        assert len(text) > 100  # Should have substantial content
        assert "Page 1" in text
        assert "Page 10" in text


class TestPDFIntegrationWithRAG:
    """Test PDF integration with RAG pipeline."""

    def test_pdf_can_be_indexed(self, tmp_path):
        """Test that PDF text can be indexed in RAG."""
        from zena_mode.rag_pipeline import LocalRAG

        # Create sample PDF
        pdf_path = tmp_path / "test.pdf"
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "The hospital offers emergency services 24/7.")
        c.showPage()
        c.save()
        pdf_path.write_bytes(buffer.getvalue())

        # Extract text
        text = PDFExtractor.extract_text(pdf_path)
        assert text is not None

        # Create RAG document
        documents = [{"url": str(pdf_path), "title": "Hospital Services", "content": text}]

        # Index in RAG - build_index handles chunking internally
        rag = LocalRAG(cache_dir=tmp_path)
        rag.build_index(documents, filter_junk=False)  # Ensure indexed for test

        assert rag.index is not None
        assert rag.index.ntotal >= 1
        assert len(rag.chunks) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
