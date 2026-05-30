from functools import lru_cache

from openai import OpenAI

from app.core.config import Settings, get_settings


@lru_cache
def get_openai_client() -> OpenAI:
    """OpenAI SDK client pointed at Qwen / Model Studio compatible-mode API."""
    settings = get_settings()
    api_key = settings.llm_api_key
    if not api_key:
        raise RuntimeError(
            "LLM API key missing. Set DASHSCOPE_API_KEY (or OPENAI_API_KEY) in .env"
        )
    return OpenAI(api_key=api_key, base_url=settings.openai_base_url)


def embedding_kwargs(settings: Settings | None = None) -> dict:
    """Keyword args for embeddings.create aligned with pgvector schema."""
    s = settings or get_settings()
    return {
        "model": s.llm_embedding_model,
        "dimensions": s.llm_embedding_dimensions,
        "encoding_format": "float",
    }
