from typing import Any

from neo4j import Driver


class GraphRepository:
    """Minimal CRUD helpers for the knowledge graph."""

    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def upsert_document(self, doc_id: str, title: str, filename: str) -> dict[str, Any]:
        query = """
        MERGE (d:Document {id: $id})
        SET d.title = $title,
            d.filename = $filename,
            d.updated_at = datetime()
        RETURN d.id AS id, d.title AS title, d.filename AS filename
        """
        record = self._run_single(query, id=doc_id, title=title, filename=filename)
        return dict(record) if record else {}

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        query = """
        MATCH (d:Document {id: $id})
        RETURN d.id AS id, d.title AS title, d.filename AS filename
        """
        record = self._run_single(query, id=doc_id)
        return dict(record) if record else None

    def delete_document(self, doc_id: str) -> bool:
        query = """
        MATCH (d:Document {id: $id})
        DETACH DELETE d
        RETURN count(d) AS deleted
        """
        record = self._run_single(query, id=doc_id)
        return bool(record and record["deleted"] > 0)

    def _run_single(self, query: str, **params: Any) -> Any:
        with self._driver.session() as session:
            result = session.run(query, **params)
            return result.single()
