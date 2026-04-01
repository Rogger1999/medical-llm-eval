"""SQLAlchemy Task model."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaskType(str, enum.Enum):
    summarize = "summarize"
    extract = "extract"
    qa = "qa"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False
    )
    task_type: Mapped[TaskType] = mapped_column(
        Enum(TaskType), nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.pending, nullable=False
    )
    primary_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    primary_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    checker_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checker_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Task id={self.id} type={self.task_type} status={self.status}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "task_type": self.task_type.value if self.task_type else None,
            "status": self.status.value if self.status else None,
            "primary_model": self.primary_model,
            "primary_output": self.primary_output,
            "checker_model": self.checker_model,
            "checker_output": self.checker_output,
            "question": self.question,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
