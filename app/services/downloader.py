"""Download documents from Europe PMC."""
from __future__ import annotations

import uuid
from typing import List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.europe_pmc import EuropePMCClient
from app.config import get_config
from app.models.document import Document, DocumentSource, DocumentStatus
from app.services.storage import get_pdf_path, save_parsed_text
from app.utils.logging_setup import get_logger
from app.utils.text_utils import clean_text

logger = get_logger(__name__)


class DocumentDownloader:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cfg = get_config()
        self.client = EuropePMCClient()

    async def search_documents(
        self,
        topic: Optional[str] = None,
        max_results: int = 20,
    ) -> List[Document]:
        """Search Europe PMC and persist new documents. Returns created docs."""
        if topic is None:
            topic = self.cfg.topic_defaults.get("query", "malnutrition children")

        results = await self.client.search(topic, page_size=min(max_results, 100))
        created: List[Document] = []

        for item in results[:max_results]:
            source_id = item.get("source_id")
            if not source_id:
                continue
            existing = await self._find_by_source_id(source_id)
            if existing:
                logger.info(f"event=skip_duplicate source_id={source_id}")
                continue

            doc = Document(
                id=str(uuid.uuid4()),
                source_id=source_id,
                title=item.get("title"),
                authors=item.get("authors"),
                abstract=item.get("abstract"),
                journal=item.get("journal"),
                year=item.get("year"),
                doi=item.get("doi"),
                pmcid=item.get("pmcid"),
                pmid=item.get("pmid"),
                pdf_url=item.get("pdf_url"),
                status=DocumentStatus.pending,
                source=DocumentSource.europe_pmc,
                topic=topic,
            )
            self.session.add(doc)
            await self.session.flush()
            await self.session.refresh(doc)

            if doc.pdf_url:
                try:
                    await self._download_pdf(doc)
                except Exception as exc:
                    logger.warning(
                        f"event=pdf_download_fail doc_id={doc.id} err={exc!r}"
                    )

            if doc.status == DocumentStatus.pending:
                doc.status = DocumentStatus.downloaded
                if doc.abstract:
                    save_parsed_text(doc.id, clean_text(doc.abstract))
                    doc.parsed_text_path = str(get_pdf_path(doc.id).parent.parent / "parsed" / f"{doc.id}.txt")

            created.append(doc)

        await self.session.commit()
        logger.info(f"event=search_done topic={topic!r} created={len(created)}")
        return created

    async def _find_by_source_id(self, source_id: str) -> Optional[Document]:
        result = await self.session.execute(
            select(Document).where(Document.source_id == source_id)
        )
        return result.scalar_one_or_none()

    async def _download_pdf(self, doc: Document) -> None:
        """Download PDF to local path. Update doc fields."""
        cfg_dl = self.cfg.downloader
        timeout = cfg_dl.get("pdf_timeout_seconds", 60)
        headers = {"User-Agent": cfg_dl.get("user_agent", "MedRAGEval/1.0")}

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(doc.pdf_url, headers=headers)
            resp.raise_for_status()

        pdf_path = get_pdf_path(doc.id)
        pdf_path.write_bytes(resp.content)
        doc.local_pdf_path = str(pdf_path)
        doc.status = DocumentStatus.downloaded
        logger.info(
            f"event=pdf_saved doc_id={doc.id} bytes={len(resp.content)}"
        )

    async def save_metadata(self, doc: Document) -> None:
        """Persist updated document metadata."""
        self.session.add(doc)
        await self.session.flush()
