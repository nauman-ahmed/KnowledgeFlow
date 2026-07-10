from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.graph.extractor import extract_from_chunk
from app.graph.neo4j_client import get_neo4j_driver, init_graph_schema
from app.graph.validator import enforce_shacl_report, validate_graph_extractions
from app.graph.writer import ChunkExtraction, GraphWriter
from app.models import Document, DocumentChunk
from app.ontology.loader import init_ontology


def graph_ingest_enabled() -> bool:
    settings = get_settings()
    return settings.neo4j_enabled and bool(settings.llm_api_key)


def extract_and_persist_document_graph(session: Session, doc: Document) -> str:
    """Extract entities/relations from document chunks and write to Neo4j."""
    if not get_settings().neo4j_enabled:
        doc.graph_status = "skipped"
        return "graph skipped (neo4j disabled)"

    if not get_settings().llm_api_key:
        doc.graph_status = "failed"
        raise RuntimeError("Graph extraction requires DASHSCOPE_API_KEY or OPENAI_API_KEY")

    driver = get_neo4j_driver()
    if driver is None:
        doc.graph_status = "failed"
        raise RuntimeError("Neo4j driver unavailable")

    init_ontology()
    init_graph_schema()

    chunks = session.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.chunk_index)
    ).all()
    if not chunks:
        doc.graph_status = "failed"
        raise RuntimeError("No chunks available for graph extraction")

    loader = init_ontology()
    writer = GraphWriter(driver, loader)
    chunk_extractions: list[ChunkExtraction] = []

    for chunk in chunks:
        result = extract_from_chunk(
            document_title=doc.title,
            document_filename=doc.filename,
            chunk_text=chunk.content,
            loader=loader,
        )
        chunk_extractions.append(
            ChunkExtraction(
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.content,
                result=result,
            )
        )

    validation = validate_graph_extractions(
        document_id=doc.id,
        title=doc.title,
        filename=doc.filename,
        chunk_extractions=chunk_extractions,
        loader=loader,
    )
    validation = enforce_shacl_report(validation)
    chunk_extractions = validation.sanitized_extractions

    stats = writer.write_document(
        document_id=doc.id,
        title=doc.title,
        filename=doc.filename,
        chunk_extractions=chunk_extractions,
    )
    doc.graph_status = "extracted"
    doc.graph_extracted_at = datetime.now(UTC)
    shacl_detail = (
        "shacl ok"
        if validation.conforms
        else f"shacl warn ({len(validation.violations)} violations)"
    )
    return (
        f"graph: {stats.entities} entities, {stats.relations} relations, "
        f"{stats.citations} citations, {stats.chunks} chunks, {shacl_detail}"
    )
