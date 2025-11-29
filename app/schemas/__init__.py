from app.schemas.call import CallCreate, CallRead
from app.schemas.analysis import AnalysisRead
from app.schemas.transcript import TranscriptRead
from app.schemas.crm import CRMNoteRead, CRMTaskRead, CRMSyncLogRead
from app.schemas.responses import CallDetail

__all__ = [
    "CallCreate",
    "CallRead",
    "AnalysisRead",
    "TranscriptRead",
    "CRMNoteRead",
    "CRMTaskRead",
    "CRMSyncLogRead",
    "CallDetail",
]
