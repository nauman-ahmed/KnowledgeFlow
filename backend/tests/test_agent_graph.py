from unittest.mock import MagicMock, patch

from app.agents.graph import (
    answer_generator_node,
    graph_researcher_node,
    planner_node,
    researcher_node,
    route_after_planner,
    route_after_researcher,
)


@patch("app.agents.graph.get_openai_client")
def test_planner_node_fallback_on_bad_json(mock_client_fn) -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="not json"))]
    )
    mock_client_fn.return_value = mock_client

    state = {
        "query": "What is compound interest?",
        "history": [],
        "plan": "",
        "search_queries": [],
        "list_library": False,
        "run_summarize": False,
        "retrieved_chunks": [],
        "graph_paths": [],
        "retrieval_mode": "vector",
        "graph_query": "",
        "cypher_query": "",
        "graph_query_results": [],
        "cypher_error": None,
        "document_list": [],
        "chunk_summaries": [],
        "answer_messages": [],
        "steps": [],
    }
    result = planner_node(state, config={"configurable": {}})

    assert result["search_queries"] == ["What is compound interest?"]
    assert result["steps"][0]["phase"] == "planner"


@patch("app.agents.graph.search_documents_hybrid")
@patch("app.agents.graph.list_documents")
def test_researcher_node_merges_chunks(mock_list, mock_search) -> None:
    from app.rag.graph_retriever import GraphPath
    from app.rag.hybrid_retriever import HybridRetrievalResult
    from app.rag.retriever import RetrievedChunk

    mock_search.return_value = HybridRetrievalResult(
        chunks=[
            RetrievedChunk(
                chunk_id="c1",
                document_id="d1",
                document_title="Compound Interest",
                document_filename="compound-interest.txt",
                content="Compound interest grows on principal and prior interest.",
                score=0.9,
            )
        ],
        graph_paths=[
            GraphPath(
                path_id="p1",
                description=(
                    "compound interest <-MENTIONS- Compound Interest (compound-interest.txt)"
                ),
                score=1.0,
                document_filename="compound-interest.txt",
            )
        ],
        retrieval_mode="hybrid",
    )
    mock_list.return_value = [
        {
            "id": "d1",
            "title": "Compound Interest",
            "filename": "compound-interest.txt",
            "chunk_count": "1",
        }
    ]

    state = {
        "query": "compound interest",
        "history": [],
        "plan": "Search and answer",
        "search_queries": ["compound interest"],
        "list_library": True,
        "run_summarize": False,
        "retrieved_chunks": [],
        "graph_paths": [],
        "retrieval_mode": "hybrid",
        "graph_query": "",
        "cypher_query": "",
        "graph_query_results": [],
        "cypher_error": None,
        "document_list": [],
        "chunk_summaries": [],
        "answer_messages": [],
        "steps": [],
    }

    db = MagicMock()
    result = researcher_node(state, config={"configurable": {"db": db}})

    assert len(result["retrieved_chunks"]) == 1
    assert len(result["graph_paths"]) == 1
    assert result["retrieval_mode"] == "hybrid"
    assert len(result["document_list"]) == 1
    assert len(result["steps"]) == 2
    assert result["steps"][0]["phase"] == "researcher"


def test_answer_generator_includes_current_query_with_history() -> None:
    state = {
        "query": "Hi",
        "history": [
            {"role": "user", "content": "Explain compound interest in simple terms"},
            {"role": "assistant", "content": "Compound interest is earnings on earnings."},
        ],
        "plan": "Greet the user",
        "search_queries": ["greeting"],
        "list_library": False,
        "run_summarize": False,
        "retrieved_chunks": [],
        "graph_paths": [],
        "retrieval_mode": "vector",
        "graph_query": "",
        "cypher_query": "",
        "graph_query_results": [],
        "cypher_error": None,
        "document_list": [],
        "chunk_summaries": [],
        "answer_messages": [],
        "steps": [],
    }

    result = answer_generator_node(state, config={"configurable": {}})

    messages = result["answer_messages"]
    assert messages[-1] == {"role": "user", "content": "Hi"}
    assert messages[-2]["role"] == "assistant"


@patch("app.agents.graph.query_graph_cypher")
def test_graph_researcher_node_stores_cypher_results(mock_query) -> None:
    mock_query.return_value = {
        "cypher_query": "MATCH (d:Document) RETURN d.filename LIMIT 5",
        "records": [{"filename": "intro.md"}],
        "error": None,
        "success": True,
    }
    state = {
        "query": "List documents",
        "history": [],
        "plan": "Query graph",
        "search_queries": [],
        "list_library": False,
        "run_summarize": False,
        "retrieved_chunks": [],
        "graph_paths": [],
        "retrieval_mode": "graph",
        "graph_query": "List all documents",
        "cypher_query": "",
        "graph_query_results": [],
        "cypher_error": None,
        "document_list": [],
        "chunk_summaries": [],
        "answer_messages": [],
        "steps": [],
    }
    result = graph_researcher_node(state, config={"configurable": {}})
    assert result["cypher_query"].startswith("MATCH")
    assert len(result["graph_query_results"]) == 1
    assert result["steps"][-1]["phase"] == "graph_researcher"


def test_route_after_planner_graph_mode() -> None:
    assert route_after_planner({"retrieval_mode": "graph"}) == "graph_researcher"
    assert route_after_planner({"retrieval_mode": "hybrid"}) == "researcher"


def test_route_after_researcher_hybrid_with_graph_query() -> None:
    assert (
        route_after_researcher({"retrieval_mode": "hybrid", "graph_query": "related concepts"})
        == "graph_researcher"
    )
    assert (
        route_after_researcher({"retrieval_mode": "hybrid", "graph_query": ""})
        == "answer_generator"
    )
