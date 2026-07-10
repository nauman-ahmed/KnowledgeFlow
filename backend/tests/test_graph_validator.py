from unittest.mock import patch

import pytest

from app.core.config import get_settings
from app.graph.validator import (
    enforce_shacl_report,
    sanitize_extraction_result,
    validate_graph_extractions,
    validate_rdf_graph,
)
from app.graph.writer import ChunkExtraction
from app.ontology.loader import OntologyLoader
from app.ontology.schemas import ExtractionResult


@pytest.fixture
def ontology_loader() -> OntologyLoader:
    return OntologyLoader(get_settings().ontology_path)


def test_sanitize_removes_empty_entity_names(ontology_loader: OntologyLoader) -> None:
    result = ExtractionResult(
        entities=[
            {"type": "Concept", "name": "compound interest"},
            {"type": "Concept", "name": "   "},
            {"type": "Unknown", "name": "bad"},
        ],
        relations=[],
        citations=[],
    )
    sanitized = sanitize_extraction_result(result, ontology_loader)
    assert len(sanitized.entities) == 1
    assert sanitized.entities[0].name == "compound interest"


def test_sanitize_drops_relations_with_invalid_predicate(ontology_loader: OntologyLoader) -> None:
    result = ExtractionResult(
        entities=[{"type": "Concept", "name": "alpha"}, {"type": "Concept", "name": "beta"}],
        relations=[
            {
                "predicate": "relatedTo",
                "source_type": "Concept",
                "source_name": "alpha",
                "target_type": "Concept",
                "target_name": "beta",
            },
            {
                "predicate": "invalidPredicate",
                "source_type": "Concept",
                "source_name": "alpha",
                "target_type": "Concept",
                "target_name": "beta",
            },
        ],
        citations=[],
    )
    sanitized = sanitize_extraction_result(result, ontology_loader)
    assert len(sanitized.relations) == 1
    assert sanitized.relations[0].predicate == "relatedTo"


def test_validate_rdf_graph_accepts_valid_extraction(ontology_loader: OntologyLoader) -> None:
    chunk_extractions = [
        ChunkExtraction(
            chunk_id="chunk-1",
            chunk_index=0,
            chunk_text="Compound interest grows over time.",
            result=ExtractionResult(
                entities=[{"type": "Concept", "name": "compound interest"}],
                relations=[],
                citations=[{"text": "Smith et al. 2020"}],
            ),
        )
    ]
    report = validate_graph_extractions(
        document_id="doc-1",
        title="Intro",
        filename="intro.md",
        chunk_extractions=chunk_extractions,
        loader=ontology_loader,
    )
    assert report.conforms is True
    assert len(report.sanitized_extractions) == 1


def test_enforce_shacl_report_raises_in_strict_mode(ontology_loader: OntologyLoader) -> None:
    from app.graph.validator import ShaclValidationReport

    report = ShaclValidationReport(
        conforms=False,
        report_text="Violation",
        violations=["Constraint Violation"],
        sanitized_extractions=[],
    )
    with patch("app.graph.validator.get_settings") as mock_settings:
        mock_settings.return_value.graph_shacl_mode = "strict"
        with pytest.raises(RuntimeError, match="SHACL validation failed"):
            enforce_shacl_report(report)


def test_enforce_shacl_report_continues_in_warn_mode(ontology_loader: OntologyLoader) -> None:
    from app.graph.validator import ShaclValidationReport

    report = ShaclValidationReport(
        conforms=False,
        report_text="Violation",
        violations=["Constraint Violation"],
        sanitized_extractions=[],
    )
    with patch("app.graph.validator.get_settings") as mock_settings:
        mock_settings.return_value.graph_shacl_mode = "warn"
        result = enforce_shacl_report(report)
        assert result is report


def test_validate_rdf_graph_rejects_document_without_title() -> None:
    from rdflib import Graph, Literal, Namespace
    from rdflib.namespace import RDF, XSD

    from app.ontology.loader import KF

    data = Graph()
    data.bind("kf", KF)
    doc = Namespace("http://knowledgeflow.io/data/document/")["doc-1"]
    data.add((doc, RDF.type, KF.Document))
    data.add((doc, KF.filename, Literal("intro.md", datatype=XSD.string)))

    conforms, _ = validate_rdf_graph(data)
    assert conforms is False
