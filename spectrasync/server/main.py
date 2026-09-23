"""FastAPI application factory and server entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import spectrasync as ss
from . import config
from .media import media_store
from .routes import layers, media, registries, runs
from .schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    media_store.init()
    yield
    # Shutdown


def create_app() -> FastAPI:
    app = FastAPI(
        title="SpectraSync Studio API",
        version=ss.__version__,
        lifespan=lifespan,
    )

    # CORS for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health_check() -> HealthResponse:
        from spectrasync.io.video import _backend
        has_video = _backend() is not None
        return HealthResponse(
            ok=True,
            version=ss.__version__,
            video=has_video,
        )

    # API Routes
    app.include_router(registries.router, prefix="/api")
    app.include_router(media.router, prefix="/api")
    app.include_router(layers.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")

    # Mount production static build if it exists
    dist_dir = config.ROOT / "web" / "dist"
    if dist_dir.exists() and (dist_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")

    return app


app = create_app()
