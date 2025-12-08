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
        try:
            # Check file size before attempting transcription (OpenAI limit is 25MB)
            from pathlib import Path
            file_path = Path(audio_path)
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            max_size_mb = 25.0
            
            if file_size_mb > max_size_mb:
                raise ValueError(
                    f"Audio file is too large ({file_size_mb:.2f} MB). "
                    f"OpenAI Whisper API has a maximum file size limit of {max_size_mb} MB. "
                    f"Please compress or split the audio file."
                )
            
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
        except Exception as e:
            error_msg = str(e)
            # Check for API key errors
            if "api_key" in error_msg.lower() or "401" in error_msg or "invalid" in error_msg.lower():
                logger.error("OpenAI API key error: %s", error_msg)
                raise ValueError(
                    f"Invalid OpenAI API key. Please check your OPENAI_API_KEY in .env file. "
                    f"API keys should start with 'sk-'. Error: {error_msg}"
                )
            # Re-raise other errors as-is
            logger.error("Transcription error: %s", error_msg)
            raise
