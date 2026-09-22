"""Environment-backed application settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./data/mindbridge.db"
    ai_provider: str = "mock"
    ai_timeout_seconds: float = Field(default=30.0, gt=0)
    ai_temperature: float = Field(default=0.4, ge=0, le=2)
    ai_history_limit: int = Field(default=10, ge=0, le=50)
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]


@lru_cache
def get_settings() -> Settings:
    return Settings()
