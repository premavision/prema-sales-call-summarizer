from dataclasses import dataclass
from typing import Protocol, runtime_checkable, Optional, Any


@dataclass
class TranscriptionResult:
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Optional[dict[str, Any]] = None


@runtime_checkable
class TranscriptionClient(Protocol):
    def transcribe(self, audio_path: str) -> TranscriptionResult:
        ...
