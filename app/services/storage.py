"""File storage helpers for PDFs, parsed text, and chunks."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from app.config import get_config
from app.utils.file_utils import ensure_dir, safe_read, safe_write
from app.utils.logging_setup import get_logger

logger = get_logger(__name__)


def _cfg_paths() -> dict:
    cfg = get_config()
    return cfg.paths


def get_pdf_path(doc_id: str) -> Path:
    paths = _cfg_paths()
    directory = Path(paths.get("pdfs_dir", "./data/pdfs"))
    ensure_dir(directory)
    return directory / f"{doc_id}.pdf"


def get_parsed_path(doc_id: str) -> Path:
    paths = _cfg_paths()
    directory = Path(paths.get("parsed_dir", "./data/parsed"))
    ensure_dir(directory)
    return directory / f"{doc_id}.txt"


def get_chunks_path(doc_id: str) -> Path:
    paths = _cfg_paths()
    directory = Path(paths.get("chunks_dir", "./data/chunks"))
    ensure_dir(directory)
    return directory / f"{doc_id}.json"


def save_chunks(doc_id: str, chunks: list[dict]) -> Path:
    """Serialise chunk list to JSON and return path."""
    path = get_chunks_path(doc_id)
    safe_write(path, json.dumps(chunks, ensure_ascii=False, indent=2))
    logger.info(f"event=chunks_saved doc_id={doc_id} count={len(chunks)}")
    return path


def load_chunks(doc_id: str) -> Optional[list[dict]]:
    """Load chunks from JSON file, or None if not found."""
    path = get_chunks_path(doc_id)
    raw = safe_read(path)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"event=chunks_parse_error doc_id={doc_id} err={exc!r}")
        return None


def save_parsed_text(doc_id: str, text: str) -> Path:
    path = get_parsed_path(doc_id)
    safe_write(path, text)
    logger.info(f"event=parsed_saved doc_id={doc_id} chars={len(text)}")
    return path


def load_parsed_text(doc_id: str) -> Optional[str]:
    path = get_parsed_path(doc_id)
    return safe_read(path)
