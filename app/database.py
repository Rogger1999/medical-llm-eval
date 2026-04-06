"""Async SQLAlchemy database setup with SQLite/aiosqlite."""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_config
from app.utils.logging_setup import get_logger

logger = get_logger(__name__)

_engine = None
_session_factory = None


class Base(DeclarativeBase):
    pass


def _get_engine():
    global _engine
    if _engine is None:
        cfg = get_config()
        db_url = cfg.get("database", "url", default="sqlite+aiosqlite:///./data/rag.db")
        echo = cfg.get("database", "echo", default=False)
        _engine = create_async_engine(
            db_url,
            echo=echo,
            connect_args={"check_same_thread": False, "timeout": 30},
        )

        @event.listens_for(_engine.sync_engine, "connect")
        def _set_wal_mode(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


async def init_db() -> None:
    """Create all tables."""
    # Import models to register them with Base
    from app.models import document, task, evaluation  # noqa: F401
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("event=db_initialized")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async DB session."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Dispose engine on shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("event=db_closed")
