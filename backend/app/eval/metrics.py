from __future__ import annotations

from app.rag.graph_retriever import GraphPath


def context_hit(retrieved_filenames: set[str], expected: list[str]) -> bool:
    if not expected:
        return True
    return any(doc in retrieved_filenames for doc in expected)


def _normalized_terms(values: list[str]) -> list[str]:
    return [value.strip().lower() for value in values if value.strip()]


def graph_hit(
    graph_paths: list[GraphPath],
    *,
    expected_entities: list[str] | None = None,
    expected_documents: list[str] | None = None,
) -> bool:
    entities = _normalized_terms(expected_entities or [])
    documents = expected_documents or []
    if not entities and not documents:
        return True

    path_text = " ".join(path.description.lower() for path in graph_paths)
    path_concepts = {concept.lower() for path in graph_paths for concept in path.concepts}
    path_documents = {path.document_filename for path in graph_paths if path.document_filename}

    entity_hit = any(
        entity in path_text or any(entity in concept for concept in path_concepts)
        for entity in entities
    )
    document_hit = context_hit(path_documents, documents)
    if entities and documents:
        return entity_hit or document_hit
    if entities:
        return entity_hit
    return document_hit


def hybrid_hit(context_ok: bool, graph_ok: bool) -> bool:
    return context_ok or graph_ok


def summarize_rates(values: list[bool]) -> float:
    if not values:
        return 0.0
    return round(sum(1 for value in values if value) / len(values), 3)
