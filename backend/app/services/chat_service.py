import json
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import build_agent_graph
from app.agents.state import STEP_MESSAGES, AgentState
from app.agents.tools import chunks_from_dicts
from app.core.llm import get_openai_client
from app.models import AgentRun, Conversation, Message
from app.rag.prompts import chunks_to_citations
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
    from app.core.config import get_settings

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


def stream_chat_completion(client: OpenAI, messages: list[dict]) -> Iterator[str]:
    from app.core.config import get_settings

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


def _initial_agent_state(query: str, history: list[dict[str, str]]) -> AgentState:
    return {
        "query": query,
        "history": history,
        "plan": "",
        "search_queries": [],
        "list_library": False,
        "run_summarize": False,
        "retrieved_chunks": [],
        "document_list": [],
        "chunk_summaries": [],
        "answer_messages": [],
        "steps": [],
    }


def run_agent_pipeline(
    db: Session,
    query: str,
    history: list[dict[str, str]],
) -> tuple[AgentState, list[dict[str, Any]]]:
    """Run LangGraph agent; return final state and step events for SSE."""
    graph = build_agent_graph()
    initial = _initial_agent_state(query, history)
    final_state: dict[str, Any] = dict(initial)
    step_events: list[dict[str, Any]] = []

    for event in graph.stream(
        initial,
        config={"configurable": {"db": db}},
        stream_mode="updates",
    ):
        for node_name, update in event.items():
            final_state.update(update)
            step_events.append(
                {
                    "phase": node_name,
                    "message": STEP_MESSAGES.get(node_name, node_name),
                }
            )

    return final_state, step_events  # type: ignore[return-value]


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

    agent_run = AgentRun(
        conversation_id=conversation.id,
        workflow_trace={"steps": []},
        status="running",
    )
    db.add(agent_run)
    db.flush()

    try:
        history = load_history_messages(db, conversation.id)
        final_state, step_events = run_agent_pipeline(db, message, history)

        for step in step_events:
            yield format_sse("step", step)

        answer_messages = final_state.get("answer_messages") or []
        client = get_openai_client()
        full_content: list[str] = []

        for token in stream_chat_completion(client, answer_messages):
            full_content.append(token)
            yield format_sse("token", {"content": token})

        assistant_text = "".join(full_content)
        chunks = chunks_from_dicts(final_state.get("retrieved_chunks", []))
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

        agent_run.message_id = assistant_msg.id
        agent_run.status = "completed"
        agent_run.workflow_trace = {
            "plan": final_state.get("plan"),
            "steps": final_state.get("steps", []),
            "search_queries": final_state.get("search_queries", []),
            "chunks_retrieved": len(final_state.get("retrieved_chunks", [])),
            "documents_listed": len(final_state.get("document_list", [])),
        }
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
        try:
            error_run = AgentRun(
                conversation_id=conversation.id,
                workflow_trace={"error": str(exc)},
                status="error",
            )
            db.add(error_run)
            db.commit()
        except Exception:
            db.rollback()
        yield format_sse("error", {"detail": str(exc)})
