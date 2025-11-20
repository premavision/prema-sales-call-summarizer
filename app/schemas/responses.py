from typing import List, Optional

from pydantic import Field

from pydantic import BaseModel

from app.schemas.call import CallRead
from app.schemas.transcript import TranscriptRead
from app.schemas.analysis import AnalysisRead
from app.schemas.crm import CRMNoteRead, CRMTaskRead, CRMSyncLogRead


class CallDetail(BaseModel):
    call: CallRead
    transcript: Optional[TranscriptRead] = None
    analysis: Optional[AnalysisRead] = None
    crm_notes: List[CRMNoteRead] = Field(default_factory=list)
    crm_tasks: List[CRMTaskRead] = Field(default_factory=list)
    crm_sync_logs: List[CRMSyncLogRead] = Field(default_factory=list)
