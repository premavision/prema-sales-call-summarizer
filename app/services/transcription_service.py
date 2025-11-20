import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.asr.base import TranscriptionClient
from app.core.constants import CallStatus
from app.models import Call, Transcript

logger = logging.getLogger(__name__)


class TranscriptionService:
    def __init__(self, session: Session, client: TranscriptionClient):
        self.session = session
        self.client = client

    def transcribe_call(self, call_id: int) -> Transcript:
        call = self.session.get(Call, call_id)
        if not call:
            raise ValueError(f"Call {call_id} not found")
        if not call.audio_path:
            raise ValueError("Call is missing audio_path")

        logger.info("Starting transcription for call %s", call_id)
        result = self.client.transcribe(call.audio_path)

        # Overwrite any existing transcript for idempotency
        existing = self.session.exec(
            select(Transcript).where(Transcript.call_id == call_id)
        ).first()
        if existing:
            self.session.delete(existing)
            self.session.commit()

        transcript = Transcript(
            call_id=call_id,
            text=result.text,
            language=result.language,
            confidence=result.confidence,
            metadata=result.metadata,
            created_at=datetime.utcnow(),
        )
        call.status = CallStatus.TRANSCRIBED
        call.updated_at = datetime.utcnow()

        self.session.add(transcript)
        self.session.add(call)
        self.session.commit()
        self.session.refresh(transcript)
        logger.info("Completed transcription for call %s", call_id)
        return transcript
