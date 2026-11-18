from unittest.mock import MagicMock, patch

from app.agents.graph import answer_generator_node, planner_node, researcher_node


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


def _state(query: str, history: list[dict[str, str]]) -> dict:
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


def test_answer_generator_ends_with_current_question() -> None:
    """Regression: the current question was missing, so follow-up turns
    re-answered the previous question from history."""
    history = [
        {"role": "user", "content": "What are good study habits?"},
        {"role": "assistant", "content": "Use spaced repetition."},
    ]
    result = answer_generator_node(
        _state("What is a major scale?", history), config={"configurable": {}}
    )

    messages = result["answer_messages"]
    assert messages[0]["role"] == "system"
    assert messages[1:3] == history
    assert messages[-1] == {"role": "user", "content": "What is a major scale?"}


@patch("app.agents.graph.get_openai_client")
def test_planner_sees_recent_history(mock_client_fn) -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"search_queries": ["x"]}'))]
    )
    mock_client_fn.return_value = mock_client

    history = [
        {"role": "user", "content": "What is diversification?"},
        {"role": "assistant", "content": "Spreading investments across assets."},
    ]
    planner_node(_state("How does that reduce risk?", history), config={"configurable": {}})

    prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "What is diversification?" in prompt
    assert prompt.rstrip().endswith("User question: How does that reduce risk?")
