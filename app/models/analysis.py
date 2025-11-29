from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class CallAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    call_id: int = Field(foreign_key="call.id", index=True)
    summary: Optional[str] = None
    pain_points: Optional[str] = None
    objections: Optional[str] = None
    action_items: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    follow_up_message: Optional[str] = None
    extra_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
