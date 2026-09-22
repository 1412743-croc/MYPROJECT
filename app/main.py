"""FastAPI application entry point for MindBridge."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def create_app() -> FastAPI:
    """Create and configure the web application."""
    app = FastAPI(title="MindBridge", version="0.1.0")

    @app.get("/actuator/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "UP"}

    static_dir = Path(__file__).parent / "static"
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app


app = create_app()
