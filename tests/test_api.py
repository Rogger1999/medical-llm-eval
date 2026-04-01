"""API endpoint tests using httpx AsyncClient."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/system/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_public_config_endpoint(client):
    resp = await client.get("/system/config/public")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    # API keys must not be exposed
    for model_cfg in data.get("models", {}).values():
        assert "api_key" not in model_cfg


@pytest.mark.asyncio
async def test_list_documents_empty(client):
    resp = await client.get("/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_documents_with_data(client, db_document):
    resp = await client.get("/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(d["id"] == db_document.id for d in data["items"])


@pytest.mark.asyncio
async def test_get_document_not_found(client):
    resp = await client.get("/documents/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_document_by_id(client, db_document):
    resp = await client.get(f"/documents/{db_document.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == db_document.id
    assert data["title"] == db_document.title


@pytest.mark.asyncio
async def test_download_trigger(client):
    resp = await client.post(
        "/documents/download",
        json={"topic": "malnutrition children", "max_results": 5},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_list_documents_status_filter(client, db_document):
    resp = await client.get("/documents?status=downloaded")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_documents_invalid_status(client):
    resp = await client.get("/documents?status=invalid_status")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_process_document_not_found(client):
    resp = await client.post("/documents/nonexistent-id/process")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_process_document_accepted(client, db_document):
    resp = await client.post(f"/documents/{db_document.id}/process")
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_run_evaluation_returns_run(client):
    resp = await client.post("/evaluations/run", json={})
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_list_evaluations_empty(client):
    resp = await client.get("/evaluations")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_metrics_summary_empty(client):
    resp = await client.get("/metrics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_evaluations" in data
    assert data["total_evaluations"] == 0


@pytest.mark.asyncio
async def test_metrics_fail_cases_empty(client):
    resp = await client.get("/metrics/fail-cases")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_task_not_found(client):
    resp = await client.get("/tasks/nonexistent-task-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_batch_process_accepted(client):
    resp = await client.post("/documents/process-batch")
    assert resp.status_code == 202
