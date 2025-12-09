import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

from sqlmodel import Session, select

from app.core.config import get_settings
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
        
        settings = get_settings()
        if settings.demo_mode:
            logger.info("Transcription running in DEMO MODE")
            
            # Check for specific demo files
            # We assume audio_path contains the identifier
            audio_path_str = str(call.audio_path)
            demo_text = ""
            
            if "demo_call_1" in audio_path_str:
                txt_path = Path("data/audio/demo_call_1.txt")
                if txt_path.exists():
                    demo_text = txt_path.read_text(encoding="utf-8")
                else:
                    demo_text = "Error: demo_call_1.txt not found."
            elif "demo_call_2" in audio_path_str:
                txt_path = Path("data/audio/demo_call_2.txt")
                if txt_path.exists():
                    demo_text = txt_path.read_text(encoding="utf-8")
                else:
                    demo_text = "Error: demo_call_2.txt not found."
            else:
                demo_text = (
                    "DEMO MODE ACTIVE.\n\n"
                    "Real transcription is disabled in this demo environment.\n"
                    "This text is a placeholder for manually uploaded files.\n"
                    "Please use the 'Load Demo Call' buttons to see the full capabilities with prepared data."
                )

            # Mock the result object
            class MockTranscriptionResult:
                def __init__(self, text):
                    self.text = text
                    self.language = "en"
                    self.confidence = 0.99
                    self.metadata = {"demo_mode": True, "source": "pre-generated"}
            
            result = MockTranscriptionResult(demo_text)
        else:
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
            extra_metadata=result.metadata,
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
