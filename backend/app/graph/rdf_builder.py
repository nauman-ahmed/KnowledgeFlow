from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from app.graph.resolver import entity_key
from app.graph.writer import ChunkExtraction
from app.ontology.loader import KF, OntologyLoader

DATA = Namespace("http://knowledgeflow.io/data/")


def _entity_uri(entity_type: str, name: str, uri: str | None = None) -> URIRef:
    return URIRef(entity_key(entity_type, name, uri))


def _predicate_uri(loader: OntologyLoader, predicate: str) -> URIRef:
    return URIRef(f"{KF}{predicate}")


def build_extraction_rdf(
    *,
    document_id: str,
    title: str,
    filename: str,
    chunk_extractions: list[ChunkExtraction],
    loader: OntologyLoader,
) -> Graph:
    graph = Graph()
    graph.bind("kf", KF)
    graph.bind("data", DATA)

    doc_uri = DATA[f"document/{document_id}"]
    graph.add((doc_uri, RDF.type, KF.Document))
    graph.add((doc_uri, KF.title, Literal(title, datatype=XSD.string)))
    graph.add((doc_uri, KF.filename, Literal(filename, datatype=XSD.string)))

    for chunk_extraction in chunk_extractions:
        chunk_uri = DATA[f"chunk/{chunk_extraction.chunk_id}"]
        graph.add((chunk_uri, RDF.type, KF.Chunk))
        graph.add((chunk_uri, KF.text, Literal(chunk_extraction.chunk_text, datatype=XSD.string)))
        graph.add((chunk_uri, KF.partOf, doc_uri))
        graph.add((doc_uri, KF.hasChunk, chunk_uri))

        for entity in chunk_extraction.result.entities:
            entity_uri = _entity_uri(entity.type, entity.name, entity.uri)
            graph.add((entity_uri, RDF.type, URIRef(f"{KF}{entity.type}")))
            graph.add((entity_uri, KF.name, Literal(entity.name, datatype=XSD.string)))
            if entity.type == "Concept":
                graph.add((doc_uri, KF.mentions, entity_uri))
            elif entity.type == "Author":
                graph.add((doc_uri, KF.authoredBy, entity_uri))
            elif entity.type == "Dataset":
                graph.add((doc_uri, KF.describes, entity_uri))
            elif entity.type == "Experiment":
                graph.add((doc_uri, KF.reportsExperiment, entity_uri))

        for citation in chunk_extraction.result.citations:
            citation_uri = _entity_uri("Citation", citation.text)
            graph.add((citation_uri, RDF.type, KF.Citation))
            graph.add((citation_uri, KF.text, Literal(citation.text, datatype=XSD.string)))
            graph.add((doc_uri, KF.cites, citation_uri))

        for relation in chunk_extraction.result.relations:
            predicate = _predicate_uri(loader, relation.predicate)
            if relation.source_type == "Document":
                source_uri = doc_uri
            else:
                source_uri = _entity_uri(relation.source_type, relation.source_name)
            target_uri = _entity_uri(relation.target_type, relation.target_name)
            graph.add((source_uri, predicate, target_uri))

    return graph
