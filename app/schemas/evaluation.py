"""Pydantic schemas for Evaluation endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class CheckResult(BaseModel):
    """Result from a single evaluator check.

    pass_fail=None means 'not applicable' (e.g. no task output to evaluate).
    score=None means 'not measurable'.
    """
    category: str
    pass_fail: Optional[bool]
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    details: Dict[str, Any] = Field(default_factory=dict)
    evaluator_type: str = "rule"


class EvaluationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    task_id: Optional[str] = None
    run_id: Optional[str] = None
    eval_category: str
    pass_fail: Optional[bool] = None
    score: Optional[float] = None
    details: Optional[str] = None
    evaluator_type: str
    created_at: Optional[datetime] = None


class EvaluationRunRequest(BaseModel):
    subset_size: Optional[int] = Field(
        default=None,
        ge=1,
        description="Number of documents to evaluate; defaults to 10% of total",
    )
    categories: Optional[list[str]] = Field(
        default=None,
        description="Specific evaluation categories; defaults to all",
    )
    force_rerun: bool = Field(
        default=False,
        description="Re-evaluate even if results exist",
    )


class EvaluationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    triggered_at: Optional[datetime] = None
    subset_size: Optional[int] = None
    total_docs: Optional[int] = None
    status: str
    summary_json: Optional[str] = None
