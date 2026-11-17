import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import build_agent_graph
from app.agents.state import STEP_MESSAGES, AgentState
from app.agents.tools import chunks_from_dicts
from app.core.llm import get_openai_client
from app.core.observability import get_tracer
from app.guardrails.input import GuardrailError, validate_user_message
from app.guardrails.output import generate_structured_answer, stream_summary_text
from app.memory.session import append_session_turn, get_session_history, set_session_history
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
    cached = get_session_history(conversation_id)
    if cached:
        return cached

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
    messages = [{"role": msg.role, "content": msg.content} for msg in rows]
    if messages:
        set_session_history(conversation_id, messages)
    return messages


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


def stream_agent_pipeline(
    db: Session,
    query: str,
    history: list[dict[str, str]],
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Run the agent graph, yielding ("step", event) as each node finishes,
    then ("final", state) once the graph completes."""
    graph = build_agent_graph()
    initial = _initial_agent_state(query, history)
    final_state: dict[str, Any] = dict(initial)

    for event in graph.stream(
        initial,
        config={"configurable": {"db": db}},
        stream_mode="updates",
    ):
        for node_name, update in event.items():
            final_state.update(update)
            yield (
                "step",
                {
                    "phase": node_name,
                    "message": STEP_MESSAGES.get(node_name, node_name),
                },
            )

    yield "final", final_state


# Sync generator on purpose: the agent, LLM and DB calls are all blocking, so
# Starlette must iterate this in its threadpool. An `async def` here would run
# them on the event loop, stalling every request and buffering the whole stream.
def chat_stream(
    db: Session,
    user_id: str,
    message: str,
    conversation_id: str | None,
) -> Iterator[str]:
    try:
        message = validate_user_message(message)
    except GuardrailError as exc:
        yield format_sse("error", {"detail": str(exc)})
        return

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

    tracer = get_tracer()

    try:
        history = load_history_messages(db, conversation.id)

        with tracer.trace(
            "chat",
            user_id=user_id,
            session_id=conversation.id,
            input={"message": message},
            metadata={"conversation_id": conversation.id},
        ) as trace:
            # Sent before the first LLM call so the client gets headers and a
            # status line immediately instead of waiting on the planner.
            yield format_sse("step", {"phase": "start", "message": "Thinking…"})

            final_state: dict[str, Any] = {}
            for kind, payload in stream_agent_pipeline(db, message, history):
                if kind == "final":
                    final_state = payload
                    continue
                step = payload
                yield format_sse("step", step)
                if hasattr(trace, "span"):
                    span = trace.span(
                        name=step.get("phase", "step"),
                        metadata={"message": step.get("message")},
                    )
                    span.end()

            yield format_sse("step", {"phase": "guardrails", "message": "Validating response…"})

            answer_messages = final_state.get("answer_messages") or []
            client = get_openai_client()
            chunks = chunks_from_dicts(final_state.get("retrieved_chunks", []))
            citations = chunks_to_citations(chunks)
            fallback_sources = [SourceCitation(**c) for c in citations]

            if hasattr(trace, "span"):
                retrieval_span = trace.span(
                    name="retrieval",
                    as_type="retriever",
                    metadata={
                        "chunks_retrieved": len(chunks),
                        "documents": list({c.document for c in fallback_sources}),
                        "scores": [
                            c.get("score") for c in final_state.get("retrieved_chunks", [])
                        ],
                    },
                )
                retrieval_span.end()

            structured = generate_structured_answer(
                client,
                answer_messages,
                fallback_sources=fallback_sources,
            )

            for token in stream_summary_text(structured.summary):
                yield format_sse("token", {"content": token})

            sources = structured.sources or fallback_sources
            structured_payload = structured.model_dump()

            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=structured.summary,
                sources=[s.model_dump() for s in sources],
                structured_output=structured_payload,
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
                "confidence": structured.confidence,
            }
            db.commit()
            db.refresh(assistant_msg)

            if hasattr(trace, "update"):
                trace.update(
                    output={
                        "summary": structured.summary,
                        "confidence": structured.confidence,
                        "sources": [s.model_dump() for s in sources],
                    }
                )

            append_session_turn(
                conversation.id,
                message,
                structured.summary,
                existing=history,
            )

            yield format_sse(
                "done",
                {
                    "conversation_id": conversation.id,
                    "message_id": assistant_msg.id,
                    "sources": [s.model_dump() for s in sources],
                    "structured": structured_payload,
                },
            )
    except GuardrailError as exc:
        db.rollback()
        yield format_sse("error", {"detail": str(exc)})
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
