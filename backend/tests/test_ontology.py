from pathlib import Path

import pytest

from app.core.config import get_settings
from app.ontology.loader import OntologyLoader, init_ontology, reset_ontology_for_tests
from app.ontology.prompts import build_extraction_system_prompt, build_extraction_user_prompt
from app.ontology.schemas import ExtractionResult


@pytest.fixture(autouse=True)
def reset_ontology_state() -> None:
    reset_ontology_for_tests()
    yield
    reset_ontology_for_tests()


def test_ontology_file_exists() -> None:
    path = get_settings().ontology_path
    assert path.exists()
    assert path.suffix == ".ttl"


def test_loader_lists_core_classes() -> None:
    loader = OntologyLoader(get_settings().ontology_path)
    names = {item.local_name for item in loader.list_classes()}
    assert names >= {
        "Document",
        "Chunk",
        "Author",
        "Organization",
        "Concept",
        "Dataset",
        "Experiment",
        "Citation",
    }


def test_extractable_entity_types() -> None:
    loader = OntologyLoader(get_settings().ontology_path)
    assert loader.extractable_entity_types() == [
        "Author",
        "Organization",
        "Concept",
        "Dataset",
        "Experiment",
        "Citation",
    ]


def test_extractable_relationships() -> None:
    loader = OntologyLoader(get_settings().ontology_path)
    relationships = loader.extractable_relationships()
    assert "mentions" in relationships
    assert "cites" in relationships
    assert "relatedTo" in relationships
    assert "authoredBy" in relationships


def test_neo4j_mappings() -> None:
    loader = OntologyLoader(get_settings().ontology_path)
    assert loader.neo4j_label("Concept") == "Concept"
    assert loader.neo4j_relationship("mentions") == "MENTIONS"
    assert loader.neo4j_relationship("reportsExperiment") == "REPORTS_EXPERIMENT"


def test_init_ontology_caches_loader() -> None:
    first = init_ontology()
    second = init_ontology()
    assert first is second


def test_extraction_system_prompt_includes_ontology_terms() -> None:
    loader = OntologyLoader(get_settings().ontology_path)
    prompt = build_extraction_system_prompt(loader)
    assert "Allowed entity types:" in prompt
    assert "Concept" in prompt
    assert "Allowed relationship predicates:" in prompt
    assert "mentions" in prompt
    assert "cites" in prompt


def test_extraction_user_prompt_includes_document_context() -> None:
    prompt = build_extraction_user_prompt(
        document_title="Intro to Investing",
        document_filename="intro-to-investing.md",
        chunk_text="Compound interest grows over time.",
    )
    assert "Intro to Investing" in prompt
    assert "intro-to-investing.md" in prompt
    assert "Compound interest grows over time." in prompt


def test_extraction_result_schema() -> None:
    result = ExtractionResult.model_validate(
        {
            "entities": [{"type": "Concept", "name": "compound interest"}],
            "relations": [
                {
                    "predicate": "relatedTo",
                    "source_type": "Concept",
                    "source_name": "compound interest",
                    "target_type": "Concept",
                    "target_name": "simple interest",
                }
            ],
            "citations": [{"text": "Smith et al. 2020", "context": "As noted by Smith et al."}],
        }
    )
    assert result.entities[0].type == "Concept"
    assert result.relations[0].predicate == "relatedTo"
    assert result.citations[0].text == "Smith et al. 2020"


def test_loader_rejects_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.ttl"
    with pytest.raises(Exception):
        OntologyLoader(missing)
