from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AnalysisRead(BaseModel):
    id: int
    call_id: int
    summary: Optional[str] = None
    pain_points: Optional[str] = None
    objections: Optional[str] = None
    action_items: List[str]
    follow_up_message: Optional[str] = None
    extra_metadata: dict | None = None
    created_at: datetime

    class Config:
        from_attributes = True
