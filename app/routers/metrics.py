"""Router for metrics and reporting endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.evaluators.aggregator import EvalAggregator
from app.models.evaluation import Evaluation
from app.schemas.metrics import FailCase, MetricsSummary
from app.utils.logging_setup import get_logger

router = APIRouter(prefix="/metrics", tags=["metrics"])
logger = get_logger(__name__)


@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    db: AsyncSession = Depends(get_db),
) -> MetricsSummary:
    """Aggregate pass rates by category across all evaluations."""
    result = await db.execute(select(Evaluation))
    evals = result.scalars().all()
    aggregator = EvalAggregator()
    summary = aggregator.compute_summary(evals)
    return summary


@router.get("/fail-cases", response_model=list[FailCase])
async def list_fail_cases(
    category: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[FailCase]:
    """List failed evaluations with document context."""
    from app.models.document import Document

    stmt = select(Evaluation, Document).join(
        Document, Evaluation.document_id == Document.id
    ).where(Evaluation.pass_fail == False)  # noqa: E712

    if category:
        stmt = stmt.where(Evaluation.eval_category == category)

    stmt = stmt.order_by(Evaluation.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    cases = []
    for ev, doc in rows:
        cases.append(FailCase(
            evaluation_id=ev.id,
            document_id=ev.document_id,
            document_title=doc.title,
            category=ev.eval_category.value if ev.eval_category else "",
            score=ev.score,
            details=ev.details,
            created_at=ev.created_at.isoformat() if ev.created_at else None,
        ))
    return cases
