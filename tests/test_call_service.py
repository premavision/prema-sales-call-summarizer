from datetime import datetime

from app.core.constants import CallStatus
from app.schemas import CallCreate
from app.services.call_service import CallService


def test_create_call(session):
    service = CallService(session)
    call_data = CallCreate(
        title="Test call",
        recorded_at=datetime.utcnow(),
        participants=["Alex"],
        call_type="discovery",
    )
    call = service.create_call(call_data, audio_path="/tmp/audio.wav")
    assert call.id is not None
    assert call.status == CallStatus.NEW
    assert call.audio_path == "/tmp/audio.wav"
