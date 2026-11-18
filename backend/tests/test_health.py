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



def test_api_docs_can_be_disabled() -> None:
    from app.main import api_docs_urls

    assert api_docs_urls(False) == {"docs_url": None, "redoc_url": None, "openapi_url": None}
    assert api_docs_urls(True)["docs_url"] == "/docs"
