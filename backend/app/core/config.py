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

    # Clerk (M1+)
    clerk_secret_key: str | None = None

    # Qwen / Model Studio — OpenAI-compatible API (M2+)
    dashscope_api_key: str | None = None
    openai_api_key: str | None = None  # fallback alias for dashscope_api_key
    openai_base_url: str = (
        "https://ws-z9nmudic5wazi5z1.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    )
    llm_chat_model: str = "qwen3.6-35b-a3b"
    llm_embedding_model: str = "text-embedding-v4"
    llm_embedding_dimensions: int = 1536

    @property
    def llm_api_key(self) -> str | None:
        return self.dashscope_api_key or self.openai_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
