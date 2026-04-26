from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import routes_analyze, routes_chat, routes_pdf, routes_setup
from backend.config import get_settings


def _setup_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ]
    )


def create_app() -> FastAPI:
    s = get_settings()
    _setup_logging(s.log_level)

    app = FastAPI(
        title="HepVar API",
        version="0.1.0",
        description="Hepatology rare-variant clinical intelligence powered by Opus 4.7.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[s.allowed_origin, "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(routes_analyze.router, prefix="/api")
    app.include_router(routes_chat.router, prefix="/api")
    app.include_router(routes_pdf.router, prefix="/api")
    app.include_router(routes_setup.router, prefix="/api")

    @app.get("/health")
    async def health() -> dict:
        return {
            "ok": True,
            "demo_mode": s.demo_mode,
            "model": s.opus_model,
            "anthropic_configured": s._looks_real(s.anthropic_api_key),
            "alphagenome_configured": s._looks_real(s.alphagenome_api_key),
            "ncbi_key_configured": s._looks_real(s.ncbi_api_key),
        }

    return app


app = create_app()
