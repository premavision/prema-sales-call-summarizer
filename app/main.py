from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import health, calls
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import create_db_and_tables


def create_app() -> FastAPI:
    configure_logging()
    create_db_and_tables()
    settings = get_settings()

    app = FastAPI(title="Prema Vision - Sales Call Summarizer", version="0.1.0")
    
    # Configure CORS from settings (defaults to localhost for security)
    cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins if cors_origins else ["http://localhost:8000", "http://localhost:8501"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    app.include_router(health.router, tags=["health"])
    app.include_router(calls.router, tags=["calls"])

    return app


app = create_app()
