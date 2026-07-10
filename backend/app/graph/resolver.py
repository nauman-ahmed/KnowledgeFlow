import re

BASE_URI = "http://knowledgeflow.io/entity"

# Neo4j unique-key field per entity type (matches schema.cypher constraints).
ENTITY_KEY_FIELD: dict[str, str] = {
    "Concept": "uri",
    "Author": "id",
    "Organization": "id",
    "Dataset": "id",
    "Experiment": "id",
    "Citation": "id",
    "Document": "id",
    "Chunk": "id",
}


def slugify(text: str) -> str:
    normalized = text.lower().strip()
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    normalized = re.sub(r"[\s_-]+", "-", normalized)
    return normalized.strip("-") or "unknown"


def entity_key(entity_type: str, name: str, uri: str | None = None) -> str:
    if entity_type == "Concept":
        if uri:
            return uri
        return f"{BASE_URI}/concept/{slugify(name)}"
    prefix = entity_type.lower()
    return f"{prefix}:{slugify(name)}"


def entity_key_field(entity_type: str) -> str:
    return ENTITY_KEY_FIELD[entity_type]
