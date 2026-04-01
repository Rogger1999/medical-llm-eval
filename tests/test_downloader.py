"""Tests for the document downloader service."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.models.document import Document, DocumentStatus
from app.services.downloader import DocumentDownloader


@pytest.mark.asyncio
async def test_search_documents_creates_records(db_session, mock_epmc_results):
    with patch(
        "app.services.downloader.EuropePMCClient.search",
        new=AsyncMock(return_value=mock_epmc_results),
    ):
        downloader = DocumentDownloader(db_session)
        docs = await downloader.search_documents(
            topic="malnutrition children", max_results=5
        )
    assert len(docs) == 1
    assert docs[0].title == "Zinc supplementation in malnourished children"
    assert docs[0].source_id == "PMC111"


@pytest.mark.asyncio
async def test_search_documents_deduplication(db_session, mock_epmc_results):
    """Second call with same results should not create duplicates."""
    with patch(
        "app.services.downloader.EuropePMCClient.search",
        new=AsyncMock(return_value=mock_epmc_results),
    ):
        downloader = DocumentDownloader(db_session)
        first_call = await downloader.search_documents(topic="malnutrition", max_results=5)

    with patch(
        "app.services.downloader.EuropePMCClient.search",
        new=AsyncMock(return_value=mock_epmc_results),
    ):
        downloader2 = DocumentDownloader(db_session)
        second_call = await downloader2.search_documents(topic="malnutrition", max_results=5)

    assert len(first_call) == 1
    assert len(second_call) == 0  # All duplicates skipped


@pytest.mark.asyncio
async def test_search_documents_sets_status(db_session, mock_epmc_results):
    with patch(
        "app.services.downloader.EuropePMCClient.search",
        new=AsyncMock(return_value=mock_epmc_results),
    ):
        downloader = DocumentDownloader(db_session)
        docs = await downloader.search_documents(topic="test", max_results=5)

    assert all(d.status == DocumentStatus.downloaded for d in docs)


@pytest.mark.asyncio
async def test_search_documents_empty_results(db_session):
    with patch(
        "app.services.downloader.EuropePMCClient.search",
        new=AsyncMock(return_value=[]),
    ):
        downloader = DocumentDownloader(db_session)
        docs = await downloader.search_documents(topic="nothing", max_results=5)

    assert docs == []


@pytest.mark.asyncio
async def test_search_respects_max_results(db_session):
    many_results = [
        {
            "source_id": f"PMC{i}",
            "title": f"Study {i}",
            "authors": "Author A",
            "abstract": f"Abstract for study {i}.",
            "journal": "Journal",
            "year": 2020,
            "doi": None, "pmcid": f"PMC{i}", "pmid": str(i), "pdf_url": None,
        }
        for i in range(10)
    ]
    with patch(
        "app.services.downloader.EuropePMCClient.search",
        new=AsyncMock(return_value=many_results),
    ):
        downloader = DocumentDownloader(db_session)
        docs = await downloader.search_documents(topic="test", max_results=3)

    assert len(docs) <= 3


@pytest.mark.asyncio
async def test_save_metadata_persists(db_session, db_document):
    db_document.topic = "updated_topic"
    downloader = DocumentDownloader(db_session)
    await downloader.save_metadata(db_document)
    await db_session.flush()
    assert db_document.topic == "updated_topic"
