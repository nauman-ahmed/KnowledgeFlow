import base64
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _domain_from_publishable_key(publishable_key: str | None) -> str | None:
    if not publishable_key or not publishable_key.startswith("pk_"):
        return None
    parts = publishable_key.split("_", 2)
    if len(parts) < 3:
        return None
    encoded = parts[2].rstrip("$")
    encoded += "=" * (-len(encoded) % 4)
    try:
        return base64.b64decode(encoded).decode("utf-8").rstrip("$")
    except (ValueError, UnicodeDecodeError):
        return None


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
    clerk_publishable_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CLERK_PUBLISHABLE_KEY",
            "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
        ),
    )
    clerk_jwks_url_override: str | None = Field(default=None, validation_alias="CLERK_JWKS_URL")

    # Qwen / Model Studio — OpenAI-compatible API (M2+)
    dashscope_api_key: str | None = None
    openai_api_key: str | None = None  # fallback alias for dashscope_api_key
    openai_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    llm_chat_model: str = "qwen3.6-35b-a3b"
    llm_embedding_model: str = "text-embedding-v4"
    llm_embedding_dimensions: int = 1536

    content_dir: Path = _REPO_ROOT / "content"
    ingest_chunk_size: int = 2000
    ingest_chunk_overlap: int = 200
    embed_batch_size: int = 16

    # RAG / chat (M3+)
    rag_top_k: int = 5
    chat_history_turns: int = 10

    @property
    def llm_api_key(self) -> str | None:
        return self.dashscope_api_key or self.openai_api_key

    @property
    def clerk_frontend_domain(self) -> str | None:
        return _domain_from_publishable_key(self.clerk_publishable_key)

    @property
    def clerk_jwks_url(self) -> str:
        if self.clerk_jwks_url_override:
            return self.clerk_jwks_url_override
        domain = self.clerk_frontend_domain
        if domain:
            return f"https://{domain}/.well-known/jwks.json"
        return "https://api.clerk.com/v1/jwks"

    @property
    def clerk_jwt_issuer(self) -> str | None:
        domain = self.clerk_frontend_domain
        if domain:
            return f"https://{domain}"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
