import json
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.llm import get_openai_client
from app.models import Conversation, Message
from app.rag.prompts import build_system_message, chunks_to_citations
from app.rag.retriever import retrieve_chunks
from app.schemas.chat import SourceCitation


def truncate_title(text: str, max_len: int = 60) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_len:
        return cleaned or "New chat"
    return cleaned[: max_len - 3].rstrip() + "..."


def get_or_create_conversation(
    db: Session,
    user_id: str,
    conversation_id: str | None,
    first_message: str,
) -> Conversation:
    if conversation_id:
        conversation = db.get(Conversation, conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise ValueError("Conversation not found")
        return conversation

    conversation = Conversation(
        user_id=user_id,
        title=truncate_title(first_message),
    )
    db.add(conversation)
    db.flush()
    return conversation


def load_history_messages(db: Session, conversation_id: str) -> list[dict[str, str]]:
    settings = get_settings()
    limit = settings.chat_history_turns * 2
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = list(reversed(db.scalars(stmt).all()))
    return [{"role": msg.role, "content": msg.content} for msg in rows]


def build_llm_messages(db: Session, conversation_id: str, query: str) -> tuple[list[dict], list]:
    chunks = retrieve_chunks(db, query)
    system_message = build_system_message(chunks)
    history = load_history_messages(db, conversation_id)
    llm_messages = [{"role": "system", "content": system_message}, *history]
    return llm_messages, chunks


def stream_chat_completion(client: OpenAI, messages: list[dict]) -> Iterator[str]:
    settings = get_settings()
    stream = client.chat.completions.create(
        model=settings.llm_chat_model,
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


def format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def chat_stream(
    db: Session,
    user_id: str,
    message: str,
    conversation_id: str | None,
) -> AsyncIterator[str]:
    try:
        conversation = get_or_create_conversation(db, user_id, conversation_id, message)
    except ValueError:
        yield format_sse("error", {"detail": "Conversation not found"})
        return

    user_msg = Message(conversation_id=conversation.id, role="user", content=message)
    db.add(user_msg)
    conversation.updated_at = datetime.now(UTC)
    db.commit()

    try:
        llm_messages, chunks = build_llm_messages(db, conversation.id, message)
        client = get_openai_client()
        full_content: list[str] = []

        for token in stream_chat_completion(client, llm_messages):
            full_content.append(token)
            yield format_sse("token", {"content": token})

        assistant_text = "".join(full_content)
        citations = chunks_to_citations(chunks)
        sources = [SourceCitation(**c) for c in citations]

        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_text,
            sources=[s.model_dump() for s in sources],
        )
        db.add(assistant_msg)
        conversation.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(assistant_msg)

        yield format_sse(
            "done",
            {
                "conversation_id": conversation.id,
                "message_id": assistant_msg.id,
                "sources": [s.model_dump() for s in sources],
            },
        )
    except Exception as exc:
        db.rollback()
        yield format_sse("error", {"detail": str(exc)})
