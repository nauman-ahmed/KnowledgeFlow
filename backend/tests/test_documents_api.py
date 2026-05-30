from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_documents_empty_or_populated() -> None:
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "total" in data
    assert data["total"] == len(data["documents"])


def test_document_stats() -> None:
    response = client.get("/api/v1/documents/stats/summary")
    assert response.status_code == 200
    data = response.json()
    assert "documents_total" in data
    assert "chunks_total" in data
