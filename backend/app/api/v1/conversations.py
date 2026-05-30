from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.models import Conversation
from app.schemas.chat import SourceCitation
from app.schemas.conversations import (
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
    MessageOut,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _message_out(msg) -> MessageOut:
    sources = None
    if msg.sources:
        sources = [SourceCitation(**s) for s in msg.sources]
    return MessageOut(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        sources=sources,
        created_at=msg.created_at,
    )


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> ConversationListResponse:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = list(db.scalars(stmt).all())
    return ConversationListResponse(
        conversations=[ConversationSummary.model_validate(c) for c in conversations],
        total=len(conversations),
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> ConversationDetail:
    stmt = (
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .options(selectinload(Conversation.messages))
    )
    conversation = db.scalars(stmt).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = sorted(conversation.messages, key=lambda m: m.created_at)
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[_message_out(m) for m in messages],
    )


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> None:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conversation)
    db.commit()
