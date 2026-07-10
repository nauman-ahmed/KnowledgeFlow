from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from app.core.config import get_settings

KF = Namespace("http://knowledgeflow.io/ontology#")

# Entity types the LLM extractor may emit (Document/Chunk come from ingest metadata).
EXTRACTABLE_ENTITY_TYPES = (
    "Author",
    "Organization",
    "Concept",
    "Dataset",
    "Experiment",
    "Citation",
)

# Maps ontology class local names to Neo4j node labels.
NEO4J_LABEL_BY_CLASS: dict[str, str] = {
    "Document": "Document",
    "Chunk": "Chunk",
    "Author": "Author",
    "Organization": "Organization",
    "Concept": "Concept",
    "Dataset": "Dataset",
    "Experiment": "Experiment",
    "Citation": "Citation",
}

# Maps ontology object-property local names to Neo4j relationship types.
NEO4J_RELATION_BY_PROPERTY: dict[str, str] = {
    "authoredBy": "AUTHORED_BY",
    "affiliatedWith": "AFFILIATED_WITH",
    "mentions": "MENTIONS",
    "cites": "CITES",
    "relatedTo": "RELATED_TO",
    "hasChunk": "HAS_CHUNK",
    "partOf": "PART_OF",
    "describes": "DESCRIBES",
    "reportsExperiment": "REPORTS_EXPERIMENT",
}


@dataclass(frozen=True)
class OntologyClass:
    uri: str
    local_name: str
    label: str
    comment: str | None = None


@dataclass(frozen=True)
class OntologyProperty:
    uri: str
    local_name: str
    label: str
    property_type: str
    domain: str | None = None
    range: str | None = None


class OntologyLoader:
    """Load and query the KnowledgeFlow RDF/OWL ontology."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.graph = Graph()
        self.graph.parse(path, format="turtle")
        self.graph.bind("kf", KF)

    def list_classes(self) -> list[OntologyClass]:
        classes: list[OntologyClass] = []
        for subject in self.graph.subjects(RDF.type, OWL.Class):
            if not isinstance(subject, URIRef) or not str(subject).startswith(str(KF)):
                continue
            local_name = subject.split("#")[-1]
            classes.append(
                OntologyClass(
                    uri=str(subject),
                    local_name=local_name,
                    label=self._label(subject),
                    comment=self._comment(subject),
                )
            )
        return sorted(classes, key=lambda item: item.local_name)

    def list_object_properties(self) -> list[OntologyProperty]:
        return self._list_properties(OWL.ObjectProperty, "object")

    def list_datatype_properties(self) -> list[OntologyProperty]:
        return self._list_properties(OWL.DatatypeProperty, "datatype")

    def extractable_entity_types(self) -> list[str]:
        defined = {item.local_name for item in self.list_classes()}
        return [name for name in EXTRACTABLE_ENTITY_TYPES if name in defined]

    def extractable_relationships(self) -> list[str]:
        return [
            prop.local_name
            for prop in self.list_object_properties()
            if prop.local_name in NEO4J_RELATION_BY_PROPERTY
        ]

    def neo4j_label(self, class_local_name: str) -> str:
        return NEO4J_LABEL_BY_CLASS[class_local_name]

    def neo4j_relationship(self, property_local_name: str) -> str:
        return NEO4J_RELATION_BY_PROPERTY[property_local_name]

    def _list_properties(self, property_type: URIRef, kind: str) -> list[OntologyProperty]:
        properties: list[OntologyProperty] = []
        for subject in self.graph.subjects(RDF.type, property_type):
            if not isinstance(subject, URIRef) or not str(subject).startswith(str(KF)):
                continue
            local_name = subject.split("#")[-1]
            properties.append(
                OntologyProperty(
                    uri=str(subject),
                    local_name=local_name,
                    label=self._label(subject),
                    property_type=kind,
                    domain=self._class_local_name(subject, RDFS.domain),
                    range=self._class_local_name(subject, RDFS.range),
                )
            )
        return sorted(properties, key=lambda item: item.local_name)

    def _label(self, subject: URIRef) -> str:
        label = self.graph.value(subject, RDFS.label)
        if label is None:
            return subject.split("#")[-1]
        return str(label)

    def _comment(self, subject: URIRef) -> str | None:
        comment = self.graph.value(subject, RDFS.comment)
        return str(comment) if comment is not None else None

    def _class_local_name(self, subject: URIRef, predicate: URIRef) -> str | None:
        value = self.graph.value(subject, predicate)
        if value is None:
            return None
        if isinstance(value, URIRef) and str(value).startswith(str(KF)):
            return value.split("#")[-1]
        return None


_loader: OntologyLoader | None = None


def init_ontology() -> OntologyLoader:
    """Load and cache the ontology (idempotent)."""
    global _loader
    if _loader is None:
        settings = get_settings()
        _loader = OntologyLoader(settings.ontology_path)
    return _loader


def get_ontology() -> OntologyLoader:
    if _loader is None:
        return init_ontology()
    return _loader


def check_ontology() -> bool:
    try:
        loader = get_ontology()
        return len(loader.list_classes()) > 0
    except Exception:
        return False


def reset_ontology_for_tests() -> None:
    global _loader
    _loader = None
    get_settings.cache_clear()
