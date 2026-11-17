from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.chat import SourceCitation
from app.schemas.structured import StructuredAnswerResponse

client = TestClient(app)


def test_chat_requires_message() -> None:
    response = client.post("/api/v1/chat", json={"message": ""})
    assert response.status_code == 422


@patch("app.services.chat_service.generate_structured_answer")
@patch("app.services.chat_service.get_openai_client")
@patch("app.services.chat_service.stream_agent_pipeline")
def test_chat_stream_mocked(mock_pipeline, mock_client_fn, mock_structured) -> None:
    mock_pipeline.return_value = iter(
        [
            ("step", {"phase": "planner", "message": "Planning approach…"}),
            (
                "final",
                {
                    "answer_messages": [
                        {"role": "system", "content": "context"},
                        {"role": "user", "content": "What is compound interest?"},
                    ],
                    "retrieved_chunks": [],
                    "steps": [],
                },
            ),
        ]
    )
    mock_structured.return_value = StructuredAnswerResponse(
        summary="Hello structured world",
        key_points=["Point one"],
        sources=[SourceCitation(document="compound-interest.txt", excerpt="Growth on growth")],
        confidence="high",
    )
    mock_client_fn.return_value = MagicMock()

    response = client.post(
        "/api/v1/chat",
        json={"message": "What is compound interest?"},
    )

    assert response.status_code == 200
    body = response.text
    assert "event: step" in body
    assert "event: token" in body
    assert "Hello structured" in body
    assert "event: done" in body
    assert "Planning approach" in body
    assert body.index("event: step") < body.index("event: token") < body.index("event: done")
