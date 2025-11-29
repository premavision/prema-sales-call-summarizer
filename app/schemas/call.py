from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.core.constants import CallStatus


class CallBase(BaseModel):
    title: str
    participants: List[str] = []
    call_type: Optional[str] = None
    recorded_at: datetime
    contact_name: Optional[str] = None
    company: Optional[str] = None
    crm_deal_id: Optional[str] = None
    external_id: Optional[str] = None


class CallCreate(CallBase):
    pass


class CallRead(CallBase):
    id: int
    status: CallStatus
    audio_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
