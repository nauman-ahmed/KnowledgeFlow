import logging
from dataclasses import dataclass, field
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

from app.core.config import get_settings
from app.graph.rdf_builder import build_extraction_rdf
from app.graph.writer import ChunkExtraction
from app.ontology.loader import OntologyLoader
from app.ontology.schemas import ExtractedEntity, ExtractedRelation, ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class ShaclValidationReport:
    conforms: bool
    report_text: str
    violations: list[str] = field(default_factory=list)
    sanitized_extractions: list[ChunkExtraction] = field(default_factory=list)


def sanitize_extraction_result(
    result: ExtractionResult, loader: OntologyLoader
) -> ExtractionResult:
    allowed_types = set(loader.extractable_entity_types())
    properties = {prop.local_name: prop for prop in loader.list_object_properties()}

    entities: list[ExtractedEntity] = []
    for entity in result.entities:
        if entity.type not in allowed_types:
            continue
        if not entity.name.strip():
            continue
        entities.append(entity.model_copy(update={"name": entity.name.strip()}))

    citations = [c for c in result.citations if c.text.strip()]
    entity_index = {(e.type, e.name.lower()) for e in entities}
    citation_index = {c.text.lower() for c in citations}

    relations: list[ExtractedRelation] = []
    for relation in result.relations:
        if relation.predicate not in properties:
            continue
        prop = properties[relation.predicate]
        if prop.domain and relation.source_type != prop.domain:
            continue
        if prop.range and relation.target_type != prop.range:
            continue
        if relation.source_type == "Document":
            pass
        elif (relation.source_type, relation.source_name.lower()) not in entity_index:
            continue
        if relation.target_type == "Citation":
            if relation.target_name.lower() not in citation_index:
                continue
        elif (relation.target_type, relation.target_name.lower()) not in entity_index:
            continue
        relations.append(relation)

    return ExtractionResult(entities=entities, relations=relations, citations=citations)


def sanitize_chunk_extractions(
    chunk_extractions: list[ChunkExtraction], loader: OntologyLoader
) -> list[ChunkExtraction]:
    sanitized: list[ChunkExtraction] = []
    for chunk_extraction in chunk_extractions:
        sanitized.append(
            ChunkExtraction(
                chunk_id=chunk_extraction.chunk_id,
                chunk_index=chunk_extraction.chunk_index,
                chunk_text=chunk_extraction.chunk_text,
                result=sanitize_extraction_result(chunk_extraction.result, loader),
            )
        )
    return sanitized


def _parse_violations(report_text: str) -> list[str]:
    if not report_text.strip():
        return []
    lines = [line.strip() for line in report_text.splitlines() if line.strip()]
    violations = [line for line in lines if "Constraint Violation" in line or "Focus Node" in line]
    if violations:
        return violations
    return [line for line in lines if line.startswith("Violation") or "sh:" in line][:10]


def _load_graph(path: Path) -> Graph:
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def validate_rdf_graph(data_graph: Graph) -> tuple[bool, str]:
    settings = get_settings()
    ontology_graph = _load_graph(settings.ontology_path)
    shapes_graph = _load_graph(settings.shacl_shapes_path)
    conforms, _report_graph, report_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        ont_graph=ontology_graph,
        inference="none",
        abort_on_first=False,
    )
    return bool(conforms), str(report_text)


def validate_graph_extractions(
    *,
    document_id: str,
    title: str,
    filename: str,
    chunk_extractions: list[ChunkExtraction],
    loader: OntologyLoader,
) -> ShaclValidationReport:
    sanitized = sanitize_chunk_extractions(chunk_extractions, loader)
    data_graph = build_extraction_rdf(
        document_id=document_id,
        title=title,
        filename=filename,
        chunk_extractions=sanitized,
        loader=loader,
    )
    conforms, report_text = validate_rdf_graph(data_graph)
    violations = [] if conforms else _parse_violations(report_text)
    return ShaclValidationReport(
        conforms=conforms,
        report_text=report_text,
        violations=violations,
        sanitized_extractions=sanitized,
    )


def enforce_shacl_report(report: ShaclValidationReport) -> ShaclValidationReport:
    settings = get_settings()
    mode = settings.graph_shacl_mode.lower()
    if report.conforms or mode == "warn":
        if not report.conforms:
            logger.warning(
                "SHACL validation reported %d violation(s); continuing in warn mode",
                len(report.violations),
            )
        return report
    summary = report.violations[0] if report.violations else report.report_text[:500]
    raise RuntimeError(f"SHACL validation failed: {summary}")
