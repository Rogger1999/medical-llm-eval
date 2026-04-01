"""Shared pytest fixtures for the test suite."""
from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import create_app
from app.models.document import Document, DocumentSource, DocumentStatus
from app.models.task import Task, TaskStatus, TaskType


_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_document() -> dict:
    return {
        "id": str(uuid.uuid4()),
        "source_id": "PMC1234567",
        "title": "Therapeutic feeding in severely malnourished children",
        "authors": "Smith J, Jones A",
        "abstract": (
            "Background: Severe acute malnutrition affects 19 million children worldwide. "
            "Methods: RCT of 200 children, RUTF vs standard care. "
            "Results: 85% recovery rate vs 70% in control (p=0.01). "
            "Conclusions: RUTF is more effective."
        ),
        "journal": "Lancet",
        "year": 2020,
        "doi": "10.1000/test.001",
        "pmcid": "PMC1234567",
        "pmid": "98765432",
        "pdf_url": None,
        "local_pdf_path": None,
        "parsed_text_path": None,
        "status": DocumentStatus.downloaded,
        "source": DocumentSource.europe_pmc,
        "topic": "malnutrition children interventions",
    }


@pytest_asyncio.fixture
async def db_document(db_session: AsyncSession, sample_document: dict) -> Document:
    doc = Document(**sample_document)
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest.fixture
def mock_claude_response() -> str:
    return (
        "Summary: This RCT evaluated RUTF vs standard care in 200 malnourished children. "
        "Results showed 85% recovery with RUTF vs 70% in controls (p=0.01). "
        "RUTF appears more effective for treating severe acute malnutrition."
    )


@pytest.fixture
def mock_openai_response() -> str:
    return '{"grounded": true, "issues": []}'


@pytest.fixture
def mock_epmc_results() -> list:
    return [
        {
            "source_id": "PMC111",
            "title": "Zinc supplementation in malnourished children",
            "authors": "Brown K",
            "abstract": "A study of zinc supplementation in 150 children aged 6-24 months.",
            "journal": "BMJ",
            "year": 2019,
            "doi": "10.1000/bmj.001",
            "pmcid": "PMC111",
            "pmid": "11111111",
            "pdf_url": None,
        }
    ]
