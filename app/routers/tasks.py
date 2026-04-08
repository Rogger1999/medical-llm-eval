"""Router for LLM task endpoints."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import get_db, _get_session_factory
from app.models.task import Task
from app.schemas.task import ExtractRequest, QARequest, SummarizeRequest, TaskRead
from app.services.task_runner import TaskRunner
from app.utils.logging_setup import get_logger

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = get_logger(__name__)


def get_task_factory() -> async_sessionmaker:
    return _get_session_factory()


@router.get("", response_model=List[TaskRead])
async def list_tasks(
    document_id: Optional[str] = Query(default=None),
    task_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> List[TaskRead]:
    """List tasks, newest first. Optionally filter by document or type."""
    q = select(Task).order_by(desc(Task.created_at)).limit(limit)
    if document_id:
        q = q.where(Task.document_id == document_id)
    if task_type:
        q = q.where(Task.task_type == task_type)
    result = await db.execute(q)
    return [TaskRead.model_validate(t) for t in result.scalars().all()]


async def _summarize_all_bg() -> None:
    """Background job: summarize every chunked document that has no summarize task yet."""
    from app.models.document import Document, DocumentStatus
    from app.models.task import TaskType
    factory = _get_session_factory()

    async with factory() as session:
        done_result = await session.execute(
            select(Task.document_id).where(Task.task_type == TaskType.summarize).distinct()
        )
        already_done = set(done_result.scalars().all())
        all_result = await session.execute(
            select(Document.id).where(Document.status == DocumentStatus.chunked)
        )
        doc_ids = [d for d in all_result.scalars().all() if d not in already_done]

    logger.info(f"event=summarize_all_start count={len(doc_ids)}")
    runner = TaskRunner(factory)
    for doc_id in doc_ids:
        try:
            await runner.run_summarize(doc_id)
            logger.info(f"event=summarize_all_done doc_id={doc_id}")
        except Exception as exc:
            logger.error(f"event=summarize_all_error doc_id={doc_id} err={exc!r}")


@router.post("/summarize-all", status_code=202)
async def summarize_all(background_tasks: BackgroundTasks) -> dict:
    """Summarize every chunked document that doesn't have a summarize task yet."""
    background_tasks.add_task(_summarize_all_bg)
    return {"status": "accepted", "message": "Batch summarisation started"}


@router.post("/summarize", response_model=TaskRead, status_code=201)
async def summarize(
    request: SummarizeRequest,
    factory: async_sessionmaker = Depends(get_task_factory),
) -> TaskRead:
    """Run summarization on a document using Claude, checked by OpenAI."""
    runner = TaskRunner(factory)
    try:
        task = await runner.run_summarize(request.document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"event=summarize_error doc={request.document_id} err={exc!r}")
        raise HTTPException(status_code=500, detail="Summarization failed")
    return TaskRead.model_validate(task)


@router.post("/extract", response_model=TaskRead, status_code=201)
async def extract(
    request: ExtractRequest,
    factory: async_sessionmaker = Depends(get_task_factory),
) -> TaskRead:
    """Run structured extraction on a document."""
    runner = TaskRunner(factory)
    try:
        task = await runner.run_extract(request.document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"event=extract_error doc={request.document_id} err={exc!r}")
        raise HTTPException(status_code=500, detail="Extraction failed")
    return TaskRead.model_validate(task)


@router.post("/qa", response_model=TaskRead, status_code=201)
async def question_answer(
    request: QARequest,
    factory: async_sessionmaker = Depends(get_task_factory),
) -> TaskRead:
    """Run grounded QA on a document."""
    runner = TaskRunner(factory)
    try:
        task = await runner.run_qa(request.document_id, request.question)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"event=qa_error doc={request.document_id} err={exc!r}")
        raise HTTPException(status_code=500, detail="QA failed")
    return TaskRead.model_validate(task)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    """Get a task by ID."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskRead.model_validate(task)
