import pytest
from sqlmodel import create_engine, Session, SQLModel

from app.models import Call, Transcript, CallAnalysis, CRMNote, CRMTask, CRMSyncLog  # noqa: F401


@pytest.fixture()
def engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def session(engine):
    with Session(engine) as session:
        yield session
