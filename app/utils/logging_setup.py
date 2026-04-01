"""Structured logging setup. JSON in prod, human-readable in dev."""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional


_loggers: dict = {}


def _get_log_level() -> int:
    level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_str, logging.INFO)


def _is_json_format() -> bool:
    fmt = os.environ.get("LOG_FORMAT", "text").lower()
    return fmt == "json"


class JsonFormatter(logging.Formatter):
    """Minimal JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        data = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data)


def _build_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    if _is_json_format():
        handler.setFormatter(JsonFormatter())
    else:
        fmt = "%(asctime)s %(levelname)-8s %(name)s  %(message)s"
        handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S"))
    return handler


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a configured logger. Idempotent — safe to call repeatedly."""
    logger_name = name or "app"
    if logger_name in _loggers:
        return _loggers[logger_name]

    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        logger.addHandler(_build_handler())
    logger.setLevel(_get_log_level())
    logger.propagate = False
    _loggers[logger_name] = logger
    return logger


def configure_root_logging() -> None:
    """Configure root logger — call once at app startup."""
    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(_build_handler())
    root.setLevel(_get_log_level())
