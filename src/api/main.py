"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import __version__
from src.api.routes import router
from src.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="HR Document Search",
        description="Local RAG system for HR knowledge base.",
        version=__version__,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "hr-document-search", "version": __version__}

    return app


app = create_app()
