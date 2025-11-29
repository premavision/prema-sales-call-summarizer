from datetime import datetime

from app.asr.stub_client import StubTranscriptionClient
from app.crm.fake_client import FakeCRMClient
from app.llm.stub_client import StubLLMClient
from app.schemas import CallCreate
from app.services.analysis_service import AnalysisService
from app.services.call_service import CallService
from app.services.crm_service import CRMService
from app.services.transcription_service import TranscriptionService


def test_crm_sync(session, tmp_path):
    audio_path = tmp_path / "audio.wav"
    audio_path.write_text("fake audio data")
    call_service = CallService(session)
    call = call_service.create_call(
        CallCreate(title="Call", recorded_at=datetime.utcnow()), audio_path=str(audio_path)
    )

    TranscriptionService(session, StubTranscriptionClient()).transcribe_call(call.id)
    AnalysisService(session, StubLLMClient()).analyze_call(call.id)

    crm_service = CRMService(session, FakeCRMClient(session))
    log = crm_service.sync_call(call.id)

    assert log.status.name == "SUCCESS"
