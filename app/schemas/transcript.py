from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TranscriptRead(BaseModel):
    id: int
    call_id: int
    text: Optional[str] = None
    language: Optional[str] = None
    confidence: Optional[float] = None
    metadata: dict | None = None
    created_at: datetime

    class Config:
        orm_mode = True
