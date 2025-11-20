import logging
from pathlib import Path

from app.asr.base import TranscriptionClient, TranscriptionResult

logger = logging.getLogger(__name__)


class StubTranscriptionClient(TranscriptionClient):
    def transcribe(self, audio_path: str) -> TranscriptionResult:
        file_name = Path(audio_path).name
        logger.info("Stub transcribing %s", file_name)
        text = (
            f"(Stub) Transcription for {file_name}: Discussed product fit, pricing, "
            "timeline, and next steps."
        )
        return TranscriptionResult(
            text=text,
            language="en",
            confidence=0.9,
            metadata={"mode": "stub"},
        )
