from datetime import datetime, date
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.core.constants import CRMSyncStatus


class CRMNote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    call_id: int = Field(foreign_key="call.id", index=True)
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict | None = Field(default=None, sa_column=Column(JSON))


class CRMTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    call_id: int = Field(foreign_key="call.id", index=True)
    description: str
    due_date: Optional[date] = None
    completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict | None = Field(default=None, sa_column=Column(JSON))


class CRMSyncLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    call_id: int = Field(foreign_key="call.id", index=True)
    status: CRMSyncStatus
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    payload: dict | None = Field(default=None, sa_column=Column(JSON))
