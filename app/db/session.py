from pathlib import Path

from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from app.core.config import get_settings

settings = get_settings()

# Ensure SQLite directory exists when using a file-based URL
if settings.database_url.startswith("sqlite:///"):
    db_path = settings.database_url.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url, echo=False, future=True)


def get_session() -> Session:
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(bind=engine)
