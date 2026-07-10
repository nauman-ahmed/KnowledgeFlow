from app.ontology.loader import OntologyLoader


def build_extraction_system_prompt(loader: OntologyLoader) -> str:
    """System prompt describing allowed entity types and relationships from the ontology."""
    entity_lines = []
    for cls in loader.list_classes():
        if cls.local_name not in loader.extractable_entity_types():
            continue
        detail = f"- {cls.local_name}: {cls.label}"
        if cls.comment:
            detail += f" — {cls.comment}"
        entity_lines.append(detail)

    relation_lines = []
    for prop in loader.list_object_properties():
        if prop.local_name not in loader.extractable_relationships():
            continue
        domain = prop.domain or "Entity"
        range_ = prop.range or "Entity"
        relation_lines.append(
            f"- {prop.local_name} ({domain} → {range_}): {prop.label}"
        )

    return (
        "You extract structured knowledge from document text for a knowledge graph.\n"
        "Use ONLY the entity types and relationship predicates listed below.\n"
        "Return valid JSON matching the requested schema.\n\n"
        "Allowed entity types:\n"
        f"{chr(10).join(entity_lines)}\n\n"
        "Allowed relationship predicates:\n"
        f"{chr(10).join(relation_lines)}"
    )


def build_extraction_user_prompt(
    *,
    document_title: str,
    document_filename: str,
    chunk_text: str,
) -> str:
    return (
        f"Document title: {document_title}\n"
        f"Document filename: {document_filename}\n\n"
        "Extract entities, relationships, and citations from this text chunk:\n\n"
        f"{chunk_text}"
    )
