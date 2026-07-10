import os
from unittest.mock import MagicMock, patch

import pytest

from app.graph.neo4j_client import (
    _load_schema_statements,
    check_neo4j,
    init_graph_schema,
    reset_neo4j_driver_for_tests,
)
from app.graph.repository import GraphRepository


@pytest.fixture(autouse=True)
def reset_neo4j_state() -> None:
    reset_neo4j_driver_for_tests()
    yield
    reset_neo4j_driver_for_tests()


def test_load_schema_statements_parses_constraints() -> None:
    statements = _load_schema_statements()
    assert len(statements) >= 6
    assert all("CREATE" in statement for statement in statements)
    assert any("Document" in statement for statement in statements)


def test_check_neo4j_returns_none_when_disabled() -> None:
    with patch("app.graph.neo4j_client.get_settings") as mock_settings:
        mock_settings.return_value.neo4j_enabled = False
        assert check_neo4j() is None


def test_check_neo4j_returns_true_when_connected() -> None:
    mock_driver = MagicMock()
    with (
        patch("app.graph.neo4j_client.get_settings") as mock_settings,
        patch("app.graph.neo4j_client.get_neo4j_driver", return_value=mock_driver),
    ):
        mock_settings.return_value.neo4j_enabled = True
        assert check_neo4j() is True
        mock_driver.verify_connectivity.assert_called_once()


def test_init_graph_schema_skips_when_disabled() -> None:
    with patch("app.graph.neo4j_client.get_neo4j_driver", return_value=None) as mock_get_driver:
        init_graph_schema()
        mock_get_driver.assert_called_once()


def test_repository_upsert_and_get_document() -> None:
    upsert_record = MagicMock()
    upsert_record.data.return_value = {
        "id": "doc-1",
        "title": "Intro",
        "filename": "intro.md",
    }
    get_record = MagicMock()
    get_record.data.return_value = {
        "id": "doc-1",
        "title": "Intro",
        "filename": "intro.md",
    }

    mock_result_upsert = MagicMock()
    mock_result_upsert.single.return_value = upsert_record
    mock_result_get = MagicMock()
    mock_result_get.single.return_value = get_record

    mock_session = MagicMock()
    mock_session.run.side_effect = [mock_result_upsert, mock_result_get]

    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    repo = GraphRepository(mock_driver)
    created = repo.upsert_document("doc-1", "Intro", "intro.md")
    fetched = repo.get_document("doc-1")

    assert created == {"id": "doc-1", "title": "Intro", "filename": "intro.md"}
    assert fetched == {"id": "doc-1", "title": "Intro", "filename": "intro.md"}
    assert mock_session.run.call_count == 2


@pytest.mark.integration
def test_neo4j_live_insert_and_query() -> None:
    if os.getenv("NEO4J_INTEGRATION") != "1":
        pytest.skip("Set NEO4J_INTEGRATION=1 to run live Neo4j tests")

    from app.core.config import get_settings
    from app.graph.neo4j_client import close_neo4j_driver, get_neo4j_driver, init_graph_schema

    get_settings.cache_clear()
    with patch.dict(
        os.environ,
        {
            "NEO4J_ENABLED": "true",
            "NEO4J_URI": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            "NEO4J_USER": os.getenv("NEO4J_USER", "neo4j"),
            "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", "knowledgeflow"),
        },
        clear=False,
    ):
        get_settings.cache_clear()
        close_neo4j_driver()
        driver = get_neo4j_driver()
        assert driver is not None

        init_graph_schema()
        repo = GraphRepository(driver)
        doc_id = "integration-test-doc"
        try:
            repo.upsert_document(doc_id, "Integration Test", "integration-test.md")
            doc = repo.get_document(doc_id)
            assert doc is not None
            assert doc["title"] == "Integration Test"
        finally:
            repo.delete_document(doc_id)
            close_neo4j_driver()
