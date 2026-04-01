"""Tests for the document parser service."""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from app.models.document import Document, DocumentStatus
from app.services.parser import DocumentParser


def _make_minimal_pdf_bytes() -> bytes:
    """Return valid minimal PDF bytes for testing."""
    try:
        import PyPDF2
        from PyPDF2 import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()
    except Exception:
        # Return a minimal PDF header that PyPDF2 can read (may have 0 pages)
        return b"%PDF-1.4\n%%EOF"


@pytest.mark.asyncio
async def test_parse_document_uses_abstract_fallback(db_session, db_document):
    """Document with no PDF should fall back to abstract text."""
    parser = DocumentParser(db_session)
    db_document.local_pdf_path = None
    text = await parser.parse_document(db_document)
    assert len(text) > 0
    assert "malnutrition" in text.lower() or "rutf" in text.lower()
    assert db_document.status == DocumentStatus.parsed


@pytest.mark.asyncio
async def test_parse_document_marks_failed_on_empty(db_session, db_document):
    """Document with no PDF and no abstract should fail."""
    db_document.local_pdf_path = None
    db_document.abstract = None
    parser = DocumentParser(db_session)
    text = await parser.parse_document(db_document)
    assert text == "" or len(text) < 100
    assert db_document.status == DocumentStatus.failed


@pytest.mark.asyncio
async def test_parse_document_updates_parsed_path(db_session, db_document):
    """After parsing, parsed_text_path should be set."""
    db_document.local_pdf_path = None
    parser = DocumentParser(db_session)
    await parser.parse_document(db_document)
    assert db_document.parsed_text_path is not None


def test_parse_pdf_bytes_returns_text():
    """parse_pdf_bytes should handle PDF bytes without file I/O."""
    pdf_bytes = _make_minimal_pdf_bytes()
    parser = DocumentParser(MagicMock())
    # Should not raise even if PDF has no extractable text
    result = parser.parse_pdf_bytes(pdf_bytes)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_parse_document_with_bad_pdf_path_falls_back(db_session, db_document):
    """Bad PDF path should trigger abstract fallback."""
    db_document.local_pdf_path = "/nonexistent/path/doc.pdf"
    parser = DocumentParser(db_session)
    text = await parser.parse_document(db_document)
    # Should fall back to abstract
    assert len(text) > 0
    assert db_document.status in (DocumentStatus.parsed, DocumentStatus.failed)


@pytest.mark.asyncio
async def test_parse_document_sets_status_parsed(db_session, db_document):
    db_document.local_pdf_path = None
    db_document.abstract = "This is a sufficiently long abstract about malnutrition in children. " * 3
    parser = DocumentParser(db_session)
    await parser.parse_document(db_document)
    assert db_document.status == DocumentStatus.parsed
