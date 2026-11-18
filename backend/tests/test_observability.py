from unittest.mock import MagicMock, patch

from app.core.observability import LangfuseTracer


@patch("app.core.observability.get_settings")
def test_tracer_noop_without_keys(mock_settings) -> None:
    mock_settings.return_value.langfuse_public_key = None
    mock_settings.return_value.langfuse_secret_key = None
    mock_settings.return_value.langfuse_host = "https://cloud.langfuse.com"
    tracer = LangfuseTracer()
    assert tracer.enabled is False
    with tracer.trace("test") as trace:
        assert hasattr(trace, "span")


@patch("app.services.chat_service.get_tracer")
def test_chat_uses_tracer(mock_get_tracer) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    mock_tracer = MagicMock()
    mock_trace = MagicMock()
    mock_tracer.trace.return_value.__enter__ = MagicMock(return_value=mock_trace)
    mock_tracer.trace.return_value.__exit__ = MagicMock(return_value=False)
    mock_get_tracer.return_value = mock_tracer

    with patch("app.services.chat_service.stream_agent_pipeline") as mock_pipeline, patch(
        "app.services.chat_service.generate_structured_answer"
    ) as mock_structured, patch("app.services.chat_service.get_openai_client"):
        from app.schemas.chat import SourceCitation
        from app.schemas.structured import StructuredAnswerResponse

        mock_pipeline.return_value = iter(
            [("final", {"answer_messages": [], "retrieved_chunks": [], "steps": []})]
        )
        mock_structured.return_value = StructuredAnswerResponse(
            summary="Test",
            key_points=["a"],
            sources=[SourceCitation(document="a.txt", excerpt="x")],
            confidence="high",
        )

        client = TestClient(app)
        response = client.post("/api/v1/chat", json={"message": "Hello"})
        assert response.status_code == 200
        mock_tracer.trace.assert_called_once()


@patch("app.core.observability.get_settings")
def test_child_spans_are_parented_explicitly_to_root(mock_settings) -> None:
    """Regression: children used the client + OTel current context, which is lost
    when the streaming generator resumes on another threadpool worker, so every
    step became its own trace in Langfuse."""
    mock_settings.return_value.langfuse_public_key = "pk"
    mock_settings.return_value.langfuse_secret_key = "sk"
    mock_settings.return_value.langfuse_host = "https://cloud.langfuse.com"

    mock_client = MagicMock()
    root = mock_client.start_observation.return_value

    with patch("langfuse.Langfuse", return_value=mock_client):
        tracer = LangfuseTracer()

    with tracer.trace("chat", user_id="u1", session_id="s1") as trace:
        trace.span(name="planner", metadata={"message": "Planning"})

    mock_client.start_observation.assert_called_once()  # only the root
    root.start_observation.assert_called_once_with(
        name="planner", metadata={"message": "Planning"}, as_type="span"
    )
    mock_client.start_as_current_observation.assert_not_called()
    root.end.assert_called_once()
