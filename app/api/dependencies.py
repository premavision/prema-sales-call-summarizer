from fastapi import Depends
from sqlmodel import Session

from app.asr.stub_client import StubTranscriptionClient
from app.asr.whisper_client import WhisperTranscriptionClient
from app.asr.base import TranscriptionClient
from app.crm.fake_client import FakeCRMClient
from app.crm.base import CRMClient
from app.core.config import get_settings, Settings
from app.db.session import get_session
from app.llm.openai_client import OpenAILLMClient
from app.llm.stub_client import StubLLMClient
from app.llm.base import LLMClient


def get_settings_dep():
    return get_settings()


def get_db_session() -> Session:
    yield from get_session()


def _validate_openai_api_key(api_key: str) -> None:
    """Validate OpenAI API key format."""
    if not api_key:
        return
    api_key = api_key.strip()
    if not api_key.startswith("sk-"):
        raise ValueError(
            f"Invalid OpenAI API key format. API keys should start with 'sk-'. "
            f"Your key starts with '{api_key[:4]}...'. "
            f"Please check your OPENAI_API_KEY in .env file."
        )


def _create_transcription_client(settings: Settings) -> TranscriptionClient:
    """Core logic to create transcription client from settings."""
    if settings.asr_provider == "whisper" and settings.openai_api_key:
        _validate_openai_api_key(settings.openai_api_key)
        return WhisperTranscriptionClient(api_key=settings.openai_api_key, model=settings.whisper_model)
    return StubTranscriptionClient()


def _create_llm_client(settings: Settings) -> LLMClient:
    """Core logic to create LLM client from settings."""
    if settings.llm_provider == "openai" and settings.openai_api_key:
        _validate_openai_api_key(settings.openai_api_key)
        return OpenAILLMClient(api_key=settings.openai_api_key, model=settings.llm_model)
    return StubLLMClient()


def _create_crm_client(session: Session) -> CRMClient:
    """Core logic to create CRM client."""
    # Only fake client is implemented for now
    return FakeCRMClient(session=session)


def get_transcription_client(settings=Depends(get_settings_dep)) -> TranscriptionClient:
    """FastAPI dependency for transcription client."""
    return _create_transcription_client(settings)


def get_llm_client(settings=Depends(get_settings_dep)) -> LLMClient:
    """FastAPI dependency for LLM client."""
    return _create_llm_client(settings)


def get_crm_client(session: Session = Depends(get_db_session)) -> CRMClient:
    """FastAPI dependency for CRM client."""
    return _create_crm_client(session)
