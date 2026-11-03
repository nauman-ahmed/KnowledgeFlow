from unittest.mock import MagicMock, patch

from app.agents.graph import planner_node, researcher_node


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
        "document_list": [],
        "chunk_summaries": [],
        "answer_messages": [],
        "steps": [],
    }
    result = planner_node(state, config={"configurable": {}})

    assert result["search_queries"] == ["What is compound interest?"]
    assert result["steps"][0]["phase"] == "planner"


@patch("app.agents.graph.get_openai_client")
@patch("app.agents.graph.search_documents")
@patch("app.agents.graph.list_documents")
def test_researcher_node_merges_chunks(mock_list, mock_search, _mock_client) -> None:
    mock_search.return_value = [
        {
            "chunk_id": "c1",
            "document_id": "d1",
            "document_title": "Compound Interest",
            "document_filename": "compound-interest.txt",
            "content": "Compound interest grows on principal and prior interest.",
            "score": 0.9,
        }
    ]
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
        "document_list": [],
        "chunk_summaries": [],
        "answer_messages": [],
        "steps": [],
    }

    db = MagicMock()
    result = researcher_node(state, config={"configurable": {"db": db}})

    assert len(result["retrieved_chunks"]) == 1
    assert len(result["document_list"]) == 1
    assert result["steps"][0]["phase"] == "researcher"
