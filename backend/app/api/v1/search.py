from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.models import Conversation, Document, DocumentChunk, Message
from app.schemas.search import ConversationSearchHit, DocumentSearchHit, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


def _snippet(text: str, query: str, max_len: int = 160) -> str:
    lower = text.lower()
    idx = lower.find(query.lower())
    if idx == -1:
        return text[:max_len].rstrip() + ("…" if len(text) > max_len else "")
    start = max(0, idx - 40)
    excerpt = text[start : start + max_len].strip()
    if start > 0:
        excerpt = "…" + excerpt
    if start + max_len < len(text):
        excerpt = excerpt.rstrip() + "…"
    return excerpt


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, max_length=200),
    type: str = Query("all", pattern="^(all|documents|conversations)$"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> SearchResponse:
    query = q.strip()
    pattern = f"%{query}%"
    doc_hits: list[DocumentSearchHit] = []
    conv_hits: list[ConversationSearchHit] = []

    if type in ("all", "documents"):
        doc_stmt = (
            select(Document)
            .where(
                Document.status == "ready",
                or_(
                    Document.title.ilike(pattern),
                    Document.filename.ilike(pattern),
                ),
            )
            .order_by(Document.updated_at.desc())
            .limit(limit)
        )
        for doc in db.scalars(doc_stmt).all():
            doc_hits.append(
                DocumentSearchHit(
                    id=doc.id,
                    title=doc.title,
                    filename=doc.filename,
                    snippet=doc.title,
                )
            )

        chunk_stmt = (
            select(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(Document.status == "ready", DocumentChunk.content.ilike(pattern))
            .order_by(Document.updated_at.desc())
            .limit(limit)
        )
        seen_doc_ids = {hit.id for hit in doc_hits}
        for chunk, doc in db.execute(chunk_stmt).all():
            if doc.id in seen_doc_ids:
                continue
            seen_doc_ids.add(doc.id)
            doc_hits.append(
                DocumentSearchHit(
                    id=doc.id,
                    title=doc.title,
                    filename=doc.filename,
                    snippet=_snippet(chunk.content, query),
                )
            )
            if len(doc_hits) >= limit:
                break

    if type in ("all", "conversations"):
        title_stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.title.ilike(pattern))
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        for conv in db.scalars(title_stmt).all():
            conv_hits.append(
                ConversationSearchHit(
                    id=conv.id,
                    title=conv.title,
                    snippet=conv.title,
                    updated_at=conv.updated_at.isoformat(),
                )
            )

        msg_stmt = (
            select(Message, Conversation)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.user_id == user_id, Message.content.ilike(pattern))
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        seen_conv_ids = {hit.id for hit in conv_hits}
        for msg, conv in db.execute(msg_stmt).all():
            if conv.id in seen_conv_ids:
                continue
            seen_conv_ids.add(conv.id)
            conv_hits.append(
                ConversationSearchHit(
                    id=conv.id,
                    title=conv.title,
                    snippet=_snippet(msg.content, query),
                    updated_at=conv.updated_at.isoformat(),
                )
            )
            if len(conv_hits) >= limit:
                break

    return SearchResponse(query=query, documents=doc_hits[:limit], conversations=conv_hits[:limit])
