from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.core.constants import CRMSyncStatus


class CRMNoteRead(BaseModel):
    id: int
    call_id: int
    content: str
    created_at: datetime
    extra_metadata: dict | None = None

    class Config:
        from_attributes = True


class CRMTaskRead(BaseModel):
    id: int
    call_id: int
    description: str
    due_date: Optional[date] = None
    completed: bool
    created_at: datetime
    extra_metadata: dict | None = None

    class Config:
        from_attributes = True


class CRMSyncLogRead(BaseModel):
    id: int
    call_id: int
    status: CRMSyncStatus
    message: Optional[str] = None
    created_at: datetime
    payload: dict | None = None

    class Config:
        from_attributes = True
