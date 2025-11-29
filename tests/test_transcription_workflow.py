from datetime import datetime

from app.asr.stub_client import StubTranscriptionClient
from app.schemas import CallCreate
from app.services.call_service import CallService
from app.services.transcription_service import TranscriptionService


def test_transcription_workflow(session, tmp_path):
    audio_path = tmp_path / "audio.wav"
    audio_path.write_text("fake audio data")

    call_service = CallService(session)
    call = call_service.create_call(
        CallCreate(title="Call", recorded_at=datetime.utcnow()), audio_path=str(audio_path)
    )

    service = TranscriptionService(session, StubTranscriptionClient())
    transcript = service.transcribe_call(call.id)

    assert transcript.call_id == call.id
    assert "Stub" in transcript.text
