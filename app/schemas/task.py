"""Pydantic schemas for Task endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    task_type: str
    question: Optional[str] = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    task_type: str
    status: str
    primary_model: Optional[str] = None
    primary_output: Optional[str] = None
    checker_model: Optional[str] = None
    checker_output: Optional[str] = None
    question: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class SummarizeRequest(BaseModel):
    document_id: str = Field(..., description="UUID of the document to summarize")
    max_length: Optional[int] = Field(default=500, ge=100, le=2000)


class ExtractRequest(BaseModel):
    document_id: str = Field(..., description="UUID of the document to extract from")
    fields: Optional[list[str]] = Field(
        default=None,
        description="Specific fields to extract; defaults to all standard fields",
    )


class QARequest(BaseModel):
    document_id: str = Field(..., description="UUID of the document to query")
    question: str = Field(..., min_length=5, max_length=1000)
    top_k: Optional[int] = Field(default=5, ge=1, le=20)
