"""SQLAlchemy Evaluation and EvaluationRun models."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EvalCategory(str, enum.Enum):
    ingest = "ingest"
    retrieval = "retrieval"
    grounding = "grounding"
    hallucination = "hallucination"
    numeric = "numeric"
    abstention = "abstention"
    adversarial = "adversarial"
    overclaiming = "overclaiming"


class EvaluatorType(str, enum.Enum):
    rule = "rule"
    llm = "llm"
    hybrid = "hybrid"


class EvalRunStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False
    )
    task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tasks.id"), nullable=True
    )
    run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("evaluation_runs.id"), nullable=True
    )
    eval_category: Mapped[EvalCategory] = mapped_column(
        Enum(EvalCategory), nullable=False
    )
    pass_fail: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluator_type: Mapped[EvaluatorType] = mapped_column(
        Enum(EvaluatorType), default=EvaluatorType.rule, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "eval_category": self.eval_category.value if self.eval_category else None,
            "pass_fail": self.pass_fail,
            "score": self.score,
            "details": self.details,
            "evaluator_type": self.evaluator_type.value if self.evaluator_type else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    subset_size: Mapped[int | None] = mapped_column(nullable=True)
    total_docs: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[EvalRunStatus] = mapped_column(
        Enum(EvalRunStatus), default=EvalRunStatus.running, nullable=False
    )
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "subset_size": self.subset_size,
            "total_docs": self.total_docs,
            "status": self.status.value if self.status else None,
            "summary_json": self.summary_json,
        }
