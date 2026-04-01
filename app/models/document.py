"""SQLAlchemy Document model."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    downloaded = "downloaded"
    parsed = "parsed"
    chunked = "chunked"
    failed = "failed"


class DocumentSource(str, enum.Enum):
    europe_pmc = "europe_pmc"
    pubmed = "pubmed"
    manual = "manual"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    authors: Mapped[str | None] = mapped_column(Text, nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    journal: Mapped[str | None] = mapped_column(String(512), nullable=True)
    year: Mapped[int | None] = mapped_column(nullable=True)
    doi: Mapped[str | None] = mapped_column(String(256), nullable=True)
    pmcid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pmid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_text_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.pending, nullable=False
    )
    source: Mapped[DocumentSource] = mapped_column(
        Enum(DocumentSource), default=DocumentSource.europe_pmc, nullable=False
    )
    topic: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} status={self.status} title={self.title!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "journal": self.journal,
            "year": self.year,
            "doi": self.doi,
            "pmcid": self.pmcid,
            "pmid": self.pmid,
            "pdf_url": self.pdf_url,
            "local_pdf_path": self.local_pdf_path,
            "parsed_text_path": self.parsed_text_path,
            "status": self.status.value if self.status else None,
            "source": self.source.value if self.source else None,
            "topic": self.topic,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
