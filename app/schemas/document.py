"""Pydantic schemas for Document endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    pmcid: Optional[str] = None
    pmid: Optional[str] = None
    pdf_url: Optional[str] = None
    source: str = "europe_pmc"
    topic: Optional[str] = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    pmcid: Optional[str] = None
    pmid: Optional[str] = None
    pdf_url: Optional[str] = None
    local_pdf_path: Optional[str] = None
    parsed_text_path: Optional[str] = None
    status: str
    source: str
    topic: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[DocumentRead]
    total: int
    page: int
    page_size: int


class DownloadRequest(BaseModel):
    topic: str = Field(
        default="malnutrition undernutrition children interventions",
        description="Search query for document retrieval",
    )
    max_results: int = Field(default=20, ge=1, le=200)
    source: str = Field(default="europe_pmc")
    year_from: Optional[int] = Field(default=None)
