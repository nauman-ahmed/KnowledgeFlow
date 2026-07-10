import json
import re

from langgraph.graph import END, START, StateGraph
from langgraph.types import RunnableConfig
from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.agents.tools import (
    list_documents,
    query_graph_cypher,
    search_documents_hybrid,
    summarize_text,
    with_retry,
)
from app.core.config import get_settings
from app.core.llm import get_openai_client
from app.rag.graph_retriever import GraphPath, graph_retrieval_enabled
from app.rag.prompts import (
    SYSTEM_PROMPT,
    format_context,
    format_cypher_context,
    format_graph_context,
)
from app.rag.retriever import RetrievedChunk, retrieve_chunks


def _get_db(config: RunnableConfig) -> Session:
    return config["configurable"]["db"]


def _parse_planner_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _default_retrieval_mode() -> str:
    if graph_retrieval_enabled():
        return "hybrid"
    return "vector"


def _normalize_retrieval_mode(value: str | None) -> str:
    mode = (value or _default_retrieval_mode()).lower()
    if mode not in {"vector", "graph", "hybrid"}:
        return _default_retrieval_mode()
    if mode in {"graph", "hybrid"} and not graph_retrieval_enabled():
        return "vector"
    return mode


def planner_node(state: AgentState, config: RunnableConfig) -> dict:
    settings = get_settings()
    client = get_openai_client()
    query = state["query"]

    prompt = (
        "You are a planning agent for a knowledge library assistant with vector search "
        "and a Neo4j knowledge graph.\n"
        "Return ONLY valid JSON with keys:\n"
        '- "plan": one sentence strategy\n'
        '- "search_queries": 1-3 search strings for semantic retrieval\n'
        '- "retrieval_mode": one of "vector", "graph", or "hybrid"\n'
        '- "graph_query": natural language graph question for Cypher when graph/hybrid '
        "is useful, otherwise empty string\n"
        '- "list_library": boolean, true if user asks what documents exist\n'
        '- "run_summarize": boolean, true if a summary of sources would help\n'
        "Use retrieval_mode=graph for relationship/author/citation questions.\n"
        "Use retrieval_mode=hybrid for questions needing both document text and graph links.\n"
        "Use retrieval_mode=vector for straightforward factual lookup.\n"
        f"\nUser question: {query}"
    )

    def _call() -> dict:
        response = client.chat.completions.create(
            model=settings.llm_chat_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            data = _parse_planner_json(raw)
        except json.JSONDecodeError:
            data = {
                "plan": "Search the library and answer from retrieved context.",
                "search_queries": [query],
                "retrieval_mode": _default_retrieval_mode(),
                "graph_query": query if graph_retrieval_enabled() else "",
                "list_library": False,
                "run_summarize": False,
            }
        retrieval_mode = _normalize_retrieval_mode(data.get("retrieval_mode"))
        graph_query = str(data.get("graph_query") or "").strip()
        if retrieval_mode == "graph" and not graph_query:
            graph_query = query
        if retrieval_mode == "vector":
            graph_query = ""
        return {
            "plan": str(data.get("plan", "")),
            "search_queries": list(data.get("search_queries") or [query])[:3],
            "retrieval_mode": retrieval_mode,
            "graph_query": graph_query,
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
    graph_paths: list[dict] = []
    retrieval_mode = state.get("retrieval_mode", "vector")

    for search_query in state.get("search_queries") or [state["query"]]:
        if retrieval_mode == "vector":
            chunks = retrieve_chunks(db, search_query)
            for chunk in chunks:
                chunk_dict = {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "document_title": chunk.document_title,
                    "document_filename": chunk.document_filename,
                    "content": chunk.content,
                    "score": chunk.score,
                }
                if chunk_dict["chunk_id"] in seen_chunk_ids:
                    continue
                seen_chunk_ids.add(chunk_dict["chunk_id"])
                merged.append(chunk_dict)
        else:
            result = search_documents_hybrid(db, search_query)
            retrieval_mode = result.retrieval_mode
            for path in result.graph_paths:
                graph_paths.append(
                    {
                        "path_id": path.path_id,
                        "description": path.description,
                        "score": path.score,
                        "document_filename": path.document_filename,
                        "concepts": path.concepts,
                    }
                )
            for chunk in result.chunks:
                chunk_dict = {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "document_title": chunk.document_title,
                    "document_filename": chunk.document_filename,
                    "content": chunk.content,
                    "score": chunk.score,
                }
                if chunk_dict["chunk_id"] in seen_chunk_ids:
                    continue
                seen_chunk_ids.add(chunk_dict["chunk_id"])
                merged.append(chunk_dict)

    document_list: list[dict[str, str]] = []
    if state.get("list_library"):
        document_list = list_documents(db)

    summaries: list[str] = []
    if state.get("run_summarize") and merged:
        combined = "\n\n".join(c["content"] for c in merged[:3])
        summaries.append(summarize_text(combined, client=client))

    detail = f"Retrieved {len(merged)} chunk(s)"
    if graph_paths:
        detail += f" with {len(graph_paths)} graph path(s)"
    if document_list:
        detail += f", listed {len(document_list)} document(s)"
    if summaries:
        detail += ", generated summary"

    steps = [{"phase": "researcher", "detail": detail}]
    if graph_paths:
        steps.append(
            {
                "phase": "graph_researcher",
                "detail": f"Graph retrieval found {len(graph_paths)} path(s)",
            }
        )

    return {
        "retrieved_chunks": merged,
        "graph_paths": graph_paths,
        "retrieval_mode": retrieval_mode,
        "document_list": document_list,
        "chunk_summaries": summaries,
        "steps": steps,
    }


def graph_researcher_node(state: AgentState, config: RunnableConfig) -> dict:
    graph_query = state.get("graph_query") or state["query"]
    steps = [{"phase": "cypher_generator", "detail": f"Generating Cypher for: {graph_query}"}]

    result = query_graph_cypher(graph_query)
    if result["success"]:
        detail = f"Cypher returned {len(result['records'])} row(s)"
    else:
        detail = f"Cypher failed: {result.get('error')}"

    steps.append({"phase": "graph_researcher", "detail": detail})

    return {
        "cypher_query": result.get("cypher_query", ""),
        "graph_query_results": result.get("records", []),
        "cypher_error": result.get("error"),
        "steps": steps,
    }


def _build_context(state: AgentState) -> str:
    chunks = [RetrievedChunk(**c) for c in state.get("retrieved_chunks", [])]
    graph_paths = [GraphPath(**p) for p in state.get("graph_paths", [])]
    parts: list[str] = [format_context(chunks)]
    if graph_paths:
        parts.append(format_graph_context(graph_paths))
    if state.get("cypher_query"):
        parts.append(
            format_cypher_context(
                state["cypher_query"],
                state.get("graph_query_results", []),
                error=state.get("cypher_error"),
            )
        )

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
    answer_messages = [
        {"role": "system", "content": system_message},
        *history,
        {"role": "user", "content": state["query"]},
    ]
    return {
        "answer_messages": answer_messages,
        "steps": [{"phase": "answer_generator", "detail": "Answer context prepared"}],
    }


def route_after_planner(state: AgentState) -> str:
    if state.get("retrieval_mode") == "graph":
        return "graph_researcher"
    return "researcher"


def route_after_researcher(state: AgentState) -> str:
    if state.get("retrieval_mode") == "hybrid" and state.get("graph_query"):
        return "graph_researcher"
    return "answer_generator"


def build_agent_graph():
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("graph_researcher", graph_researcher_node)
    graph.add_node("answer_generator", answer_generator_node)
    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", route_after_planner)
    graph.add_conditional_edges("researcher", route_after_researcher)
    graph.add_edge("graph_researcher", "answer_generator")
    graph.add_edge("answer_generator", END)
    return graph.compile()


def _initial_agent_state(query: str, history: list[dict[str, str]]) -> AgentState:
    return {
        "query": query,
        "history": history,
        "plan": "",
        "search_queries": [],
        "list_library": False,
        "run_summarize": False,
        "retrieved_chunks": [],
        "graph_paths": [],
        "retrieval_mode": _default_retrieval_mode(),
        "graph_query": "",
        "cypher_query": "",
        "graph_query_results": [],
        "cypher_error": None,
        "document_list": [],
        "chunk_summaries": [],
        "answer_messages": [],
        "steps": [],
    }


def run_agent(db: Session, query: str, history: list[dict[str, str]]) -> AgentState:
    graph = build_agent_graph()
    initial = _initial_agent_state(query, history)
    return graph.invoke(initial, config={"configurable": {"db": db}})
