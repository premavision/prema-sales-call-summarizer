from datetime import datetime

from app.llm.stub_client import StubLLMClient
from app.schemas import CallCreate
from app.services.call_service import CallService
from app.services.transcription_service import TranscriptionService
from app.services.analysis_service import AnalysisService
from app.asr.stub_client import StubTranscriptionClient


def test_analysis_workflow(session, tmp_path):
    audio_path = tmp_path / "audio.wav"
    audio_path.write_text("fake audio data")
    call_service = CallService(session)
    call = call_service.create_call(
        CallCreate(title="Call", recorded_at=datetime.utcnow()), audio_path=str(audio_path)
    )
    transcription_service = TranscriptionService(session, StubTranscriptionClient())
    transcription_service.transcribe_call(call.id)

    analysis_service = AnalysisService(session, StubLLMClient())
    analysis = analysis_service.analyze_call(call.id)

    assert analysis.call_id == call.id
    assert analysis.action_items
