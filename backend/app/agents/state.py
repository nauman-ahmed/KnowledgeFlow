import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict):
    query: str
    history: list[dict[str, str]]
    plan: str
    search_queries: list[str]
    list_library: bool
    run_summarize: bool
    retrieved_chunks: list[dict[str, Any]]
    graph_paths: list[dict[str, Any]]
    retrieval_mode: str
    graph_query: str
    cypher_query: str
    graph_query_results: list[dict[str, Any]]
    cypher_error: str | None
    document_list: list[dict[str, str]]
    chunk_summaries: list[str]
    answer_messages: list[dict[str, str]]
    steps: Annotated[list[dict[str, Any]], operator.add]


STEP_MESSAGES: dict[str, str] = {
    "planner": "Planning approach…",
    "researcher": "Searching knowledge base…",
    "graph_researcher": "Searching knowledge graph…",
    "cypher_generator": "Generating Cypher query…",
    "answer_generator": "Generating answer…",
}
