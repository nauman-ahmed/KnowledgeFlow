from unittest.mock import MagicMock, patch

import pytest

from app.core.config import get_settings
from app.graph.extractor import extract_from_chunk
from app.graph.pipeline import graph_ingest_enabled
from app.graph.resolver import entity_key, slugify
from app.graph.writer import ChunkExtraction, GraphWriter
from app.ontology.loader import OntologyLoader
from app.ontology.schemas import ExtractionResult


@pytest.fixture
def ontology_loader() -> OntologyLoader:
    return OntologyLoader(get_settings().ontology_path)


def test_slugify_normalizes_names() -> None:
    assert slugify("Compound Interest!") == "compound-interest"
    assert slugify("  Simple   Interest ") == "simple-interest"


def test_entity_key_for_concept_uses_uri_namespace() -> None:
    key = entity_key("Concept", "Compound Interest")
    assert key.endswith("/compound-interest")
    assert entity_key("Concept", "Compound Interest", "http://example.org/c") == "http://example.org/c"


def test_entity_key_for_author_uses_prefix() -> None:
    assert entity_key("Author", "Jane Doe") == "author:jane-doe"


def test_graph_ingest_enabled_requires_neo4j_and_api_key() -> None:
    with patch("app.graph.pipeline.get_settings") as mock_settings:
        mock_settings.return_value.neo4j_enabled = False
        mock_settings.return_value.llm_api_key = "key"
        assert graph_ingest_enabled() is False

        mock_settings.return_value.neo4j_enabled = True
        mock_settings.return_value.llm_api_key = None
        assert graph_ingest_enabled() is False

        mock_settings.return_value.llm_api_key = "key"
        assert graph_ingest_enabled() is True


def test_extract_from_chunk_parses_llm_json(ontology_loader: OntologyLoader) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = """
    {
      "entities": [{"type": "Concept", "name": "compound interest", "uri": null}],
      "relations": [],
      "citations": []
    }
    """
    mock_client.chat.completions.create.return_value = mock_response

    result = extract_from_chunk(
        document_title="Intro",
        document_filename="intro.md",
        chunk_text="Compound interest grows over time.",
        client=mock_client,
        loader=ontology_loader,
    )
    assert len(result.entities) == 1
    assert result.entities[0].name == "compound interest"


def test_extract_from_chunk_rejects_unknown_entity_type(ontology_loader: OntologyLoader) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = (
        '{"entities":[{"type":"Unknown","name":"x"}],"relations":[],"citations":[]}'
    )
    mock_client.chat.completions.create.return_value = mock_response

    with pytest.raises(ValueError, match="Unsupported entity type"):
        extract_from_chunk(
            document_title="Intro",
            document_filename="intro.md",
            chunk_text="text",
            client=mock_client,
            loader=ontology_loader,
        )


def test_graph_writer_upserts_document_and_chunk(ontology_loader: OntologyLoader) -> None:
    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    writer = GraphWriter(mock_driver, ontology_loader)
    chunk_extractions = [
        ChunkExtraction(
            chunk_id="chunk-1",
            chunk_index=0,
            chunk_text="Compound interest is powerful.",
            result=ExtractionResult(
                entities=[{"type": "Concept", "name": "compound interest"}],
                relations=[],
                citations=[],
            ),
        )
    ]
    stats = writer.write_document(
        document_id="doc-1",
        title="Intro",
        filename="intro.md",
        chunk_extractions=chunk_extractions,
    )

    assert stats.chunks == 1
    assert stats.entities >= 1
    assert stats.relations >= 1
    assert mock_session.run.call_count >= 3
