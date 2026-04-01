"""Pydantic schemas for Metrics endpoints."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CategoryMetrics(BaseModel):
    category: str
    total: int
    passed: int
    failed: int
    pass_rate: float = Field(ge=0.0, le=1.0)
    avg_score: Optional[float] = None


class FailCase(BaseModel):
    evaluation_id: str
    document_id: str
    document_title: Optional[str] = None
    category: str
    score: Optional[float] = None
    details: Optional[str] = None
    created_at: Optional[str] = None


class MetricsSummary(BaseModel):
    total_evaluations: int
    total_passed: int
    total_failed: int
    overall_pass_rate: float = Field(ge=0.0, le=1.0)
    weighted_score: Optional[float] = None
    by_category: Dict[str, CategoryMetrics] = Field(default_factory=dict)
    latest_run_id: Optional[str] = None
