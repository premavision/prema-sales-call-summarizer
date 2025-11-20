from fastapi import Depends
from sqlmodel import Session

from app.asr.stub_client import StubTranscriptionClient
from app.asr.whisper_client import WhisperTranscriptionClient
from app.crm.fake_client import FakeCRMClient
from app.core.config import get_settings
from app.db.session import get_session
from app.llm.openai_client import OpenAILLMClient
from app.llm.stub_client import StubLLMClient


def get_settings_dep():
    return get_settings()


def get_db_session() -> Session:
    yield from get_session()


def get_transcription_client(settings=Depends(get_settings_dep)):
    if settings.asr_provider == "whisper" and settings.openai_api_key:
        return WhisperTranscriptionClient(api_key=settings.openai_api_key, model=settings.whisper_model)
    return StubTranscriptionClient()


def get_llm_client(settings=Depends(get_settings_dep)):
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAILLMClient(api_key=settings.openai_api_key, model=settings.llm_model)
    return StubLLMClient()


def get_crm_client(session: Session = Depends(get_db_session)):
    # Only fake client is implemented for now
    return FakeCRMClient(session=session)
