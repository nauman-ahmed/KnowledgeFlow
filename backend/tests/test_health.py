from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_json() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "knowledgeflow-api"
    assert "status" in data
    assert "checks" in data
