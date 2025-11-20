from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, calls
from app.core.logging import configure_logging
from app.db.session import create_db_and_tables


def create_app() -> FastAPI:
    configure_logging()
    create_db_and_tables()

    app = FastAPI(title="Prema Vision - Sales Call Summarizer", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, tags=["health"])
    app.include_router(calls.router, tags=["calls"])

    return app


app = create_app()
