"""Router for /documents endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentList, DocumentRead, DownloadRequest
from app.services.downloader import DocumentDownloader
from app.utils.logging_setup import get_logger

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger(__name__)


async def _run_download(request: DownloadRequest) -> None:
    """Background task: download documents matching request."""
    from app.database import _get_session_factory
    factory = _get_session_factory()
    async with factory() as session:
        downloader = DocumentDownloader(session)
        docs = await downloader.search_documents(
            topic=request.topic,
            max_results=request.max_results,
        )
        logger.info(
            f"event=download_complete count={len(docs)} topic={request.topic!r}"
        )


@router.post("/download", status_code=202)
async def trigger_download(
    request: DownloadRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    """Trigger async download of documents matching topic."""
    background_tasks.add_task(_run_download, request)
    logger.info(
        f"event=download_triggered topic={request.topic!r} max={request.max_results}"
    )
    return {
        "status": "accepted",
        "message": f"Download job started for topic={request.topic!r}",
        "max_results": request.max_results,
    }


@router.get("", response_model=DocumentList)
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    topic: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> DocumentList:
    """List documents with optional pagination and status filter."""
    stmt = select(Document)
    if status:
        try:
            status_enum = DocumentStatus(status)
            stmt = stmt.where(Document.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if topic:
        stmt = stmt.where(Document.topic.ilike(f"%{topic}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    docs = result.scalars().all()

    return DocumentList(
        items=[DocumentRead.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    """Return a single document by ID."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentRead.model_validate(doc)
