from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.ingest.embedder import embed_texts
from app.models import Document, DocumentChunk


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_title: str
    document_filename: str
    content: str
    score: float


def retrieve_chunks(db: Session, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    k = top_k or settings.rag_top_k
    query_vector = embed_texts([query])[0]

    distance = DocumentChunk.embedding.cosine_distance(query_vector)
    stmt = (
        select(DocumentChunk, Document, distance.label("distance"))
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(Document.status == "ready")
        .where(DocumentChunk.embedding.isnot(None))
        .order_by(distance)
        .limit(k)
    )
    rows = db.execute(stmt).all()

    results: list[RetrievedChunk] = []
    for chunk, doc, dist in rows:
        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=doc.id,
                document_title=doc.title,
                document_filename=doc.filename,
                content=chunk.content,
                score=1.0 - float(dist),
            )
        )
    return results
