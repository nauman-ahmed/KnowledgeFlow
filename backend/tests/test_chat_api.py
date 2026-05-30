from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_chat_requires_message() -> None:
    response = client.post("/api/v1/chat", json={"message": ""})
    assert response.status_code == 422


@patch("app.services.chat_service.get_openai_client")
@patch("app.services.chat_service.run_agent_pipeline")
def test_chat_stream_mocked(mock_pipeline, mock_client_fn) -> None:
    mock_pipeline.return_value = (
        {
            "answer_messages": [
                {"role": "system", "content": "context"},
                {"role": "user", "content": "What is compound interest?"},
            ],
            "retrieved_chunks": [],
            "steps": [],
        },
        [
            {"phase": "planner", "message": "Planning approach…"},
            {"phase": "researcher", "message": "Searching knowledge base…"},
        ],
    )

    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta.content = "Hello"

    mock_stream = iter([mock_chunk, MagicMock(choices=[])])

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_stream
    mock_client_fn.return_value = mock_client

    response = client.post(
        "/api/v1/chat",
        json={"message": "What is compound interest?"},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    body = response.text
    assert "event: step" in body
    assert "event: token" in body or "event: done" in body or "event: error" in body
