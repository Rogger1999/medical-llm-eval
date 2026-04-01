"""Parse downloaded PDFs using PyPDF2, with abstract fallback."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_config
from app.models.document import Document, DocumentStatus
from app.services.storage import save_parsed_text
from app.utils.logging_setup import get_logger
from app.utils.text_utils import clean_text

logger = get_logger(__name__)


class DocumentParser:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cfg = get_config()

    async def parse_document(self, doc: Document) -> str:
        """Parse document and persist cleaned text. Returns text."""
        cfg_p = self.cfg.parsing
        min_len = cfg_p.get("min_text_length", 100)
        fallback = cfg_p.get("fallback_to_abstract", True)

        text: Optional[str] = None

        if doc.local_pdf_path and Path(doc.local_pdf_path).exists():
            try:
                text = self._parse_pdf(doc.local_pdf_path)
                logger.info(
                    f"event=pdf_parsed doc_id={doc.id} chars={len(text) if text else 0}"
                )
            except Exception as exc:
                logger.warning(f"event=pdf_parse_fail doc_id={doc.id} err={exc!r}")
                text = None

        if (text is None or len(text) < min_len) and fallback and doc.abstract:
            text = clean_text(doc.abstract or "")
            logger.info(f"event=abstract_fallback doc_id={doc.id}")

        if text is None or len(text) < min_len:
            doc.status = DocumentStatus.failed
            self.session.add(doc)
            logger.warning(
                f"event=parse_failed doc_id={doc.id} reason=insufficient_text"
            )
            return ""

        text = clean_text(text)
        path = save_parsed_text(doc.id, text)
        doc.parsed_text_path = str(path)
        doc.status = DocumentStatus.parsed
        self.session.add(doc)
        return text

    def _parse_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using PyPDF2."""
        import PyPDF2
        cfg_p = self.cfg.parsing
        max_pages = cfg_p.get("max_pages", 50)

        parts: list[str] = []
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = min(len(reader.pages), max_pages)
            for i in range(num_pages):
                page = reader.pages[i]
                try:
                    text = page.extract_text() or ""
                    parts.append(text)
                except Exception as exc:
                    logger.debug(f"event=page_extract_fail page={i} err={exc!r}")
        return "\n".join(parts)

    def parse_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Parse PDF from bytes. Used in tests / manual upload."""
        import io
        import PyPDF2

        cfg_p = self.cfg.parsing
        max_pages = cfg_p.get("max_pages", 50)
        parts: list[str] = []

        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        num_pages = min(len(reader.pages), max_pages)
        for i in range(num_pages):
            try:
                text = reader.pages[i].extract_text() or ""
                parts.append(text)
            except Exception:
                pass
        return clean_text("\n".join(parts))
