import time
from collections.abc import Callable
from dataclasses import asdict
from typing import TypeVar

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.llm import get_openai_client
from app.models import Document
from app.rag.hybrid_retriever import HybridRetrievalResult, retrieve_hybrid
from app.rag.retriever import RetrievedChunk

T = TypeVar("T")


def chunk_to_dict(chunk: RetrievedChunk) -> dict:
    return asdict(chunk)


def chunks_from_dicts(items: list[dict]) -> list[RetrievedChunk]:
    return [RetrievedChunk(**item) for item in items]


def with_retry(fn: Callable[[], T], max_attempts: int = 3, base_delay: float = 1.0) -> T:
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts - 1:
                break
            time.sleep(base_delay * (2**attempt))
    assert last_error is not None
    raise last_error


def search_documents(db: Session, query: str, top_k: int | None = None) -> list[dict]:
    result = retrieve_hybrid(db, query, top_k=top_k)
    return [chunk_to_dict(c) for c in result.chunks]


def search_documents_hybrid(
    db: Session, query: str, top_k: int | None = None
) -> HybridRetrievalResult:
    return retrieve_hybrid(db, query, top_k=top_k)


def query_graph_cypher(nl_query: str) -> dict:
    from app.graph.cypher_executor import query_graph_cypher as run_cypher_query

    return run_cypher_query(nl_query)


def list_documents(db: Session) -> list[dict[str, str]]:
    stmt = select(Document).where(Document.status == "ready").order_by(Document.title)
    docs = db.scalars(stmt).all()
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "filename": doc.filename,
            "chunk_count": str(doc.chunk_count),
        }
        for doc in docs
    ]


def summarize_text(text: str, client: OpenAI | None = None) -> str:
    settings = get_settings()
    llm = client or get_openai_client()
    trimmed = text.strip()
    if len(trimmed) > 4000:
        trimmed = trimmed[:4000] + "..."

    def _call() -> str:
        response = llm.chat.completions.create(
            model=settings.llm_chat_model,
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the following text in 2-4 concise bullet points.",
                },
                {"role": "user", "content": trimmed},
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content or ""

    return with_retry(_call)
