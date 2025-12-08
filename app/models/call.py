from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.core.constants import CallStatus


class Call(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: Optional[str] = Field(default=None, index=True)
    title: str = Field(index=True)
    participants: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    call_type: Optional[str] = Field(default=None, index=True)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    status: CallStatus = Field(default=CallStatus.NEW)
    audio_path: Optional[str] = None
    contact_name: Optional[str] = None
    company: Optional[str] = None
    crm_deal_id: Optional[str] = None
    session_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
