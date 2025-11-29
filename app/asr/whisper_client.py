import logging
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

from app.asr.base import TranscriptionClient, TranscriptionResult

logger = logging.getLogger(__name__)


class WhisperTranscriptionClient(TranscriptionClient):
    def __init__(self, api_key: str, model: str = "whisper-1"):
        if OpenAI is None:
            raise ImportError("openai package is required for WhisperTranscriptionClient")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        logger.info("Transcribing %s with Whisper model %s", audio_path, self.model)
        with open(audio_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(model=self.model, file=audio_file)

        text = response.text  # type: ignore[attr-defined]
        language = getattr(response, "language", None)
        confidence = getattr(response, "confidence", None)
        return TranscriptionResult(
            text=text,
            language=language,
            confidence=confidence,
            metadata={"provider": "openai", "model": self.model},
        )
