from app.core.config import get_settings
from app.core.llm import embedding_kwargs, get_openai_client


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    settings = get_settings()
    client = get_openai_client()
    base_kwargs = embedding_kwargs(settings)
    vectors: list[list[float]] = []
    batch_size = settings.embed_batch_size

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = client.embeddings.create(input=batch, **base_kwargs)
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors.extend(item.embedding for item in ordered)

    expected = settings.llm_embedding_dimensions
    for vector in vectors:
        if len(vector) != expected:
            raise ValueError(f"Expected embedding dimension {expected}, got {len(vector)}")

    return vectors
