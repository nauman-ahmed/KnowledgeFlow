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
    document_list: list[dict[str, str]]
    chunk_summaries: list[str]
    answer_messages: list[dict[str, str]]
    steps: Annotated[list[dict[str, Any]], operator.add]


STEP_MESSAGES: dict[str, str] = {
    "planner": "Planning approach…",
    "researcher": "Searching knowledge base…",
    "answer_generator": "Generating answer…",
}
