from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    environment: str = Field("local", description="Runtime environment name")
    database_url: str = Field("sqlite:///./data/app.db", description="Database connection URL")
    audio_dir: str = Field("data/audio", description="Path to store uploaded audio")

    asr_provider: str = Field("stub", description="ASR provider name (stub, whisper)")
    openai_api_key: str | None = Field(default=None, description="OpenAI API key for Whisper/LLM")
    whisper_model: str = Field("whisper-1", description="Whisper model name if using OpenAI API")

    llm_provider: str = Field("openai", description="LLM provider name (openai, stub)")
    llm_model: str = Field("gpt-4o-mini", description="LLM model name")

    crm_mode: str = Field("fake", description="CRM client mode (fake, hubspot, pipedrive)")
    demo_mode: bool = Field(False, description="Enable demo mode behavior")

    # Security settings
    cors_origins: str = Field("http://localhost:8000,http://localhost:8501", description="Comma-separated CORS origins")
    max_upload_size_mb: int = Field(100, description="Maximum file upload size in MB")

    backend_url: str = Field("http://localhost:8000", description="Public URL of the backend API")


@lru_cache
def get_settings() -> Settings:
    return Settings()
