import json
import re

from langgraph.graph import END, START, StateGraph
from langgraph.types import RunnableConfig
from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.agents.tools import list_documents, search_documents, summarize_text, with_retry
from app.core.config import get_settings
from app.core.llm import get_openai_client
from app.rag.prompts import SYSTEM_PROMPT, format_context
from app.rag.retriever import RetrievedChunk


def _get_db(config: RunnableConfig) -> Session:
    return config["configurable"]["db"]


def _parse_planner_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def planner_node(state: AgentState, config: RunnableConfig) -> dict:
    settings = get_settings()
    client = get_openai_client()
    query = state["query"]

    prompt = (
        "You are a planning agent for a knowledge library assistant.\n"
        "Return ONLY valid JSON with keys:\n"
        '- "plan": one sentence strategy\n'
        '- "search_queries": 1-3 search strings for semantic retrieval\n'
        '- "list_library": boolean, true if user asks what documents exist\n'
        '- "run_summarize": boolean, true if a summary of sources would help\n'
        f"\nUser question: {query}"
    )

    def _call() -> dict:
        response = client.chat.completions.create(
            model=settings.llm_chat_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            data = _parse_planner_json(raw)
        except json.JSONDecodeError:
            data = {
                "plan": "Search the library and answer from retrieved context.",
                "search_queries": [query],
                "list_library": False,
                "run_summarize": False,
            }
        return {
            "plan": str(data.get("plan", "")),
            "search_queries": list(data.get("search_queries") or [query])[:3],
            "list_library": bool(data.get("list_library", False)),
            "run_summarize": bool(data.get("run_summarize", False)),
        }

    result = with_retry(_call)
    return {
        **result,
        "steps": [{"phase": "planner", "detail": result["plan"]}],
    }


def researcher_node(state: AgentState, config: RunnableConfig) -> dict:
    db = _get_db(config)
    client = get_openai_client()
    seen_chunk_ids: set[str] = set()
    merged: list[dict] = []

    for search_query in state.get("search_queries") or [state["query"]]:
        for chunk in search_documents(db, search_query):
            if chunk["chunk_id"] in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk["chunk_id"])
            merged.append(chunk)

    document_list: list[dict[str, str]] = []
    if state.get("list_library"):
        document_list = list_documents(db)

    summaries: list[str] = []
    if state.get("run_summarize") and merged:
        combined = "\n\n".join(c["content"] for c in merged[:3])
        summaries.append(summarize_text(combined, client=client))

    detail = f"Retrieved {len(merged)} chunk(s)"
    if document_list:
        detail += f", listed {len(document_list)} document(s)"
    if summaries:
        detail += ", generated summary"

    return {
        "retrieved_chunks": merged,
        "document_list": document_list,
        "chunk_summaries": summaries,
        "steps": [{"phase": "researcher", "detail": detail}],
    }


def _build_context(state: AgentState) -> str:
    chunks = [RetrievedChunk(**c) for c in state.get("retrieved_chunks", [])]
    parts: list[str] = [format_context(chunks)]

    if state.get("document_list"):
        lines = ["## Library index"]
        for doc in state["document_list"]:
            lines.append(f"- {doc['title']} ({doc['filename']}) — {doc['chunk_count']} chunks")
        parts.append("\n".join(lines))

    if state.get("chunk_summaries"):
        parts.append("## Summaries\n" + "\n".join(state["chunk_summaries"]))

    if state.get("plan"):
        parts.insert(0, f"## Plan\n{state['plan']}")

    return "\n\n".join(parts)


def answer_generator_node(state: AgentState, config: RunnableConfig) -> dict:
    context = _build_context(state)
    system_message = f"{SYSTEM_PROMPT}\n\n## Retrieved context\n\n{context}"
    history = state.get("history") or []
    answer_messages = [{"role": "system", "content": system_message}, *history]
    return {
        "answer_messages": answer_messages,
        "steps": [{"phase": "answer_generator", "detail": "Answer context prepared"}],
    }


def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("answer_generator", answer_generator_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "answer_generator")
    graph.add_edge("answer_generator", END)
    return graph.compile()


def run_agent(db: Session, query: str, history: list[dict[str, str]]) -> AgentState:
    graph = build_agent_graph()
    initial: AgentState = {
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
    return graph.invoke(initial, config={"configurable": {"db": db}})
