from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_search_requires_query() -> None:
    response = client.get("/api/v1/search")
    assert response.status_code == 422


def test_search_empty_results() -> None:
    response = client.get("/api/v1/search", params={"q": "zzzznonexistentquery999"})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "zzzznonexistentquery999"
    assert data["documents"] == []
    assert data["conversations"] == []


def test_search_type_filter() -> None:
    response = client.get(
        "/api/v1/search",
        params={"q": "test", "type": "documents"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert data["conversations"] == []
