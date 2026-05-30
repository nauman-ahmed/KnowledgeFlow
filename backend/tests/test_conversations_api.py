from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_conversations_empty() -> None:
    response = client.get("/api/v1/conversations")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == len(data["conversations"])


def test_get_conversation_not_found() -> None:
    response = client.get("/api/v1/conversations/nonexistent-id")
    assert response.status_code == 404


def test_delete_conversation_not_found() -> None:
    response = client.delete("/api/v1/conversations/nonexistent-id")
    assert response.status_code == 404
