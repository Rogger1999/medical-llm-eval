"""System health and config endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import get_config
from app.utils.logging_setup import get_logger

router = APIRouter(prefix="/system", tags=["system"])
logger = get_logger(__name__)


@router.get("/health")
async def health_check() -> dict:
    """Return service health status."""
    return {
        "status": "ok",
        "service": "medical-rag-eval",
        "version": "1.0.0",
    }


@router.get("/config/public")
async def public_config() -> dict:
    """Return non-secret configuration values."""
    cfg = get_config()
    return cfg.public_dict()
