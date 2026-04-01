"""FastAPI application bootstrap."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_config
from app.database import close_db, init_db
from app.routers import documents, evaluations, metrics, processing, system, tasks
from app.utils.logging_setup import configure_root_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    configure_root_logging()
    cfg = get_config()

    # Ensure data directories exist
    paths = cfg.paths
    for dir_key in ("data_dir", "pdfs_dir", "parsed_dir", "chunks_dir", "logs_dir"):
        dir_path = paths.get(dir_key, "./data")
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    await init_db()
    logger.info("event=startup service=medical-rag-eval")

    yield

    await close_db()
    logger.info("event=shutdown service=medical-rag-eval")


def create_app() -> FastAPI:
    cfg = get_config()
    app = FastAPI(
        title=cfg.frontend.get("title", "Medical LLM Evaluator"),
        description=cfg.frontend.get("description", ""),
        version="1.0.0",
        lifespan=lifespan,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routers
    app.include_router(system.router)
    app.include_router(documents.router)
    app.include_router(processing.router)
    app.include_router(tasks.router)
    app.include_router(evaluations.router)
    app.include_router(metrics.router)

    # Redirect root to /app so /docs and /redoc remain accessible
    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/app/index.html")

    # Mount frontend at /app (not /) so FastAPI's /docs and /redoc are not shadowed
    frontend_dir = Path(cfg.frontend.get("static_dir", "./frontend"))
    if frontend_dir.exists():
        app.mount(
            "/app",
            StaticFiles(directory=str(frontend_dir), html=True),
            name="frontend",
        )

    return app


app = create_app()
