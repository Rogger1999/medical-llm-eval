"""Router for document parsing and chunking."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.document import Document, DocumentStatus
from app.services.chunker import TextChunker
from app.services.parser import DocumentParser
from app.utils.logging_setup import get_logger

router = APIRouter(prefix="/documents", tags=["processing"])
logger = get_logger(__name__)


async def _process_one(document_id: str) -> None:
    from app.database import _get_session_factory
    factory = _get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            logger.warning(f"event=process_skip reason=not_found doc_id={document_id}")
            return
        parser = DocumentParser(session)
        chunker = TextChunker(session)
        await parser.parse_document(doc)
        await chunker.chunk_document(doc)
        await session.commit()
        logger.info(f"event=process_done doc_id={document_id}")


async def _process_batch() -> None:
    from app.database import _get_session_factory
    factory = _get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Document).where(Document.status == DocumentStatus.downloaded)
        )
        docs = result.scalars().all()
        logger.info(f"event=batch_start count={len(docs)}")
        for doc in docs:
            parser = DocumentParser(session)
            chunker = TextChunker(session)
            try:
                await parser.parse_document(doc)
                await chunker.chunk_document(doc)
                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.error(f"event=batch_error doc_id={doc.id} error={exc!r}")
        logger.info("event=batch_done")


@router.post("/{document_id}/process", status_code=202)
async def process_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Parse and chunk a single document in the background."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    background_tasks.add_task(_process_one, document_id)
    return {"status": "accepted", "document_id": document_id}


@router.post("/process-batch", status_code=202)
async def process_batch(background_tasks: BackgroundTasks) -> dict:
    """Parse and chunk all downloaded documents in the background."""
    background_tasks.add_task(_process_batch)
    return {"status": "accepted", "message": "Batch processing started"}
