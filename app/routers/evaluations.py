"""Router for evaluation endpoints."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.evaluation import Evaluation, EvaluationRun
from app.schemas.evaluation import EvaluationResult, EvaluationRunRead, EvaluationRunRequest
from app.utils.logging_setup import get_logger

router = APIRouter(prefix="/evaluations", tags=["evaluations"])
logger = get_logger(__name__)


async def _run_evaluation(run_id: str, request: EvaluationRunRequest) -> None:
    import json
    from app.database import _get_session_factory
    from app.models.evaluation import EvaluationRun, EvalRunStatus
    from app.services.evaluation_runner import EvaluationRunner
    logger.info(f"event=eval_bg_task_start run_id={run_id}")
    factory = _get_session_factory()
    runner = EvaluationRunner(factory)
    try:
        await runner.run(run_id, request)
        logger.info(f"event=eval_bg_task_done run_id={run_id}")
    except Exception as exc:
        logger.error(f"event=eval_bg_task_failed run_id={run_id} err={exc!r}", exc_info=True)
        try:
            async with factory() as session:
                result = await session.execute(
                    select(EvaluationRun).where(EvaluationRun.id == run_id)
                )
                run = result.scalar_one_or_none()
                if run:
                    run.status = EvalRunStatus.failed
                    run.summary_json = json.dumps({"error": type(exc).__name__, "detail": str(exc)})
                    await session.commit()
                    logger.info(f"event=eval_run_marked_failed run_id={run_id}")
                else:
                    logger.error(f"event=eval_run_mark_failed_not_found run_id={run_id}")
        except Exception as inner:
            logger.error(f"event=eval_run_status_update_failed run_id={run_id} err={inner!r}", exc_info=True)


@router.post("/run", response_model=EvaluationRunRead, status_code=202)
async def run_evaluation(
    request: EvaluationRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> EvaluationRunRead:
    """Trigger a full evaluation run on a document subset."""
    from app.models.evaluation import EvalRunStatus
    try:
        run = EvaluationRun(status=EvalRunStatus.running)
        db.add(run)
        await db.flush()
        await db.refresh(run)
    except Exception as exc:
        logger.error(f"event=eval_run_create_failed err={exc!r}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create evaluation run: {type(exc).__name__}: {exc}")
    run_id = run.id
    await db.commit()  # must be visible to the background task's separate session
    background_tasks.add_task(_run_evaluation, run_id, request)
    logger.info(f"event=eval_run_triggered run_id={run_id}")
    return EvaluationRunRead.model_validate(run)


@router.get("/runs/{run_id}", response_model=EvaluationRunRead)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> EvaluationRunRead:
    """Get the status of an evaluation run (status, summary, or error detail)."""
    result = await db.execute(
        select(EvaluationRun).where(EvaluationRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return EvaluationRunRead.model_validate(run)


@router.get("", response_model=list[EvaluationResult])
async def list_evaluations(
    document_id: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[EvaluationResult]:
    """List evaluation results, optionally filtered."""
    stmt = select(Evaluation)
    if document_id:
        stmt = stmt.where(Evaluation.document_id == document_id)
    if category:
        stmt = stmt.where(Evaluation.eval_category == category)
    stmt = stmt.order_by(Evaluation.created_at.desc()).limit(200)
    result = await db.execute(stmt)
    evals = result.scalars().all()
    return [EvaluationResult.model_validate(e) for e in evals]


@router.get("/{evaluation_id}", response_model=EvaluationResult)
async def get_evaluation(
    evaluation_id: str,
    db: AsyncSession = Depends(get_db),
) -> EvaluationResult:
    """Get a single evaluation result."""
    result = await db.execute(
        select(Evaluation).where(Evaluation.id == evaluation_id)
    )
    ev = result.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return EvaluationResult.model_validate(ev)
