"""FastAPI application entry point for MindBridge."""

from contextlib import asynccontextmanager
from pathlib import Path
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.bootstrap import initialize_database, seed_demo_users
from app.core.database import SessionLocal


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    initialize_database()
    with SessionLocal() as db:
        seed_demo_users(db)
    yield


def create_app() -> FastAPI:
    """Create and configure the web application."""
    app = FastAPI(title="MindBridge", version="0.2.0", lifespan=lifespan)

    @app.get("/actuator/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "UP"}

    app.include_router(router)
    static_dir = Path(__file__).parent / "static"
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app


app = create_app()
