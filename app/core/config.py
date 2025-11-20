from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    environment: str = Field("local", description="Runtime environment name")
    database_url: str = Field("sqlite:///./data/app.db", description="Database connection URL")
    audio_dir: str = Field("data/audio", description="Path to store uploaded audio")

    asr_provider: str = Field("stub", description="ASR provider name (stub, whisper)")
    openai_api_key: str | None = Field(default=None, description="OpenAI API key for Whisper/LLM")
    whisper_model: str = Field("whisper-1", description="Whisper model name if using OpenAI API")

    llm_provider: str = Field("openai", description="LLM provider name (openai, stub)")
    llm_model: str = Field("gpt-4o-mini", description="LLM model name")

    crm_mode: str = Field("fake", description="CRM client mode (fake, hubspot, pipedrive)")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
