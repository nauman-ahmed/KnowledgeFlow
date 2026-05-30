from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "KnowledgeFlow API"
    debug: bool = False

    database_url: str = (
        "postgresql+psycopg://knowledgeflow:knowledgeflow@localhost:5433/knowledgeflow"
    )
    redis_url: str = "redis://localhost:6379/0"

    # Future phases
    clerk_secret_key: str | None = None
    openai_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
