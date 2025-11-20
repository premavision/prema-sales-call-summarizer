import logging

from sqlmodel import Session

from app.asr.base import TranscriptionClient
from app.crm.base import CRMClient
from app.llm.base import LLMClient
from app.services.analysis_service import AnalysisService
from app.services.crm_service import CRMService
from app.services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(
        self,
        session: Session,
        transcription_client: TranscriptionClient,
        llm_client: LLMClient,
        crm_client: CRMClient,
    ):
        self.transcription_service = TranscriptionService(session, transcription_client)
        self.analysis_service = AnalysisService(session, llm_client)
        self.crm_service = CRMService(session, crm_client)

    def process_call(self, call_id: int) -> None:
        self.transcription_service.transcribe_call(call_id)
        self.analysis_service.analyze_call(call_id)
        self.crm_service.sync_call(call_id)
        logger.info("Pipeline completed for call %s", call_id)
