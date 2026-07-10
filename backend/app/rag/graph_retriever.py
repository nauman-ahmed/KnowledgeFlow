from dataclasses import dataclass, field

from app.core.config import get_settings
from app.graph.neo4j_client import get_neo4j_driver
from app.rag.query_terms import extract_query_terms


@dataclass
class GraphPath:
    path_id: str
    description: str
    score: float
    document_filename: str | None = None
    concepts: list[str] = field(default_factory=list)


def graph_retrieval_enabled() -> bool:
    return get_settings().neo4j_enabled and get_neo4j_driver() is not None


def retrieve_graph_context(query: str) -> list[GraphPath]:
    if not graph_retrieval_enabled():
        return []

    settings = get_settings()
    terms = extract_query_terms(query)
    if not terms:
        return []

    driver = get_neo4j_driver()
    assert driver is not None

    paths: list[GraphPath] = []
    with driver.session() as session:
        paths.extend(_match_concept_documents(session, terms))
        paths.extend(_match_related_concepts(session, terms, settings.graph_retrieval_hops))
        paths.extend(_match_cooccurring_concepts(session, terms))
        paths.extend(_match_author_paths(session, terms))

    return _dedupe_paths(paths, settings.graph_retrieval_limit)


def _match_concept_documents(session, terms: list[str]) -> list[GraphPath]:
    query = """
    MATCH (c:Concept)<-[:MENTIONS]-(d:Document)
    WHERE any(term IN $terms WHERE toLower(c.name) CONTAINS term)
    RETURN c.name AS concept, d.filename AS filename, d.title AS title
    ORDER BY size(c.name) ASC
    LIMIT 20
    """
    rows = session.run(query, terms=terms)
    paths: list[GraphPath] = []
    for idx, record in enumerate(rows):
        concept = record["concept"]
        filename = record["filename"]
        title = record["title"]
        paths.append(
            GraphPath(
                path_id=f"doc-mention-{idx}-{concept}-{filename}",
                description=(
                    f"{concept} <-MENTIONS- {title or filename} ({filename})"
                ),
                score=1.0,
                document_filename=filename,
                concepts=[concept],
            )
        )
    return paths


def _match_related_concepts(session, terms: list[str], hops: int) -> list[GraphPath]:
    max_hops = max(1, min(hops, 2))
    query = f"""
    MATCH (start:Concept)
    WHERE any(term IN $terms WHERE toLower(start.name) CONTAINS term)
    MATCH path = (start)-[:RELATED_TO*1..{max_hops}]-(related:Concept)
    WITH path, start, related
    OPTIONAL MATCH (d:Document)-[:MENTIONS]->(start)
    RETURN start.name AS start_concept,
           related.name AS related_concept,
           [rel IN relationships(path) | type(rel)] AS rel_types,
           collect(DISTINCT d.filename)[0] AS filename
    LIMIT 20
    """
    rows = session.run(query, terms=terms)
    paths: list[GraphPath] = []
    for idx, record in enumerate(rows):
        start = record["start_concept"]
        related = record["related_concept"]
        filename = record["filename"]
        hop_count = len(record["rel_types"] or [])
        score = 1.0 / hop_count
        paths.append(
            GraphPath(
                path_id=f"related-{idx}-{start}-{related}",
                description=f"{start} --RELATED_TO--> {related}",
                score=score,
                document_filename=filename,
                concepts=[start, related],
            )
        )
    return paths


def _match_cooccurring_concepts(session, terms: list[str]) -> list[GraphPath]:
    query = """
    MATCH (start:Concept)
    WHERE any(term IN $terms WHERE toLower(start.name) CONTAINS term)
    MATCH (doc:Document)-[:MENTIONS]->(start)
    MATCH (doc)-[:MENTIONS]->(cooccur:Concept)
    WHERE cooccur <> start
    RETURN start.name AS start_concept,
           cooccur.name AS cooccur_concept,
           doc.filename AS filename,
           doc.title AS title
    LIMIT 20
    """
    rows = session.run(query, terms=terms)
    paths: list[GraphPath] = []
    for idx, record in enumerate(rows):
        start = record["start_concept"]
        cooccur = record["cooccur_concept"]
        filename = record["filename"]
        title = record["title"]
        paths.append(
            GraphPath(
                path_id=f"cooccur-{idx}-{start}-{cooccur}-{filename}",
                description=(
                    f"{start} co-mentioned with {cooccur} in {title or filename} ({filename})"
                ),
                score=0.9,
                document_filename=filename,
                concepts=[start, cooccur],
            )
        )
    return paths


def _match_author_paths(session, terms: list[str]) -> list[GraphPath]:
    query = """
    MATCH (c:Concept)<-[:MENTIONS]-(d:Document)-[:AUTHORED_BY]->(a:Author)
    WHERE any(term IN $terms WHERE toLower(c.name) CONTAINS term)
    RETURN c.name AS concept, d.filename AS filename, a.name AS author
    LIMIT 10
    """
    rows = session.run(query, terms=terms)
    paths: list[GraphPath] = []
    for idx, record in enumerate(rows):
        concept = record["concept"]
        filename = record["filename"]
        author = record["author"]
        paths.append(
            GraphPath(
                path_id=f"author-{idx}-{author}-{filename}",
                description=f"{author} --AUTHORED_BY-- {filename} (mentions {concept})",
                score=0.8,
                document_filename=filename,
                concepts=[concept],
            )
        )
    return paths


def _dedupe_paths(paths: list[GraphPath], limit: int) -> list[GraphPath]:
    deduped: list[GraphPath] = []
    seen: set[str] = set()
    for path in sorted(paths, key=lambda item: item.score, reverse=True):
        if path.description in seen:
            continue
        seen.add(path.description)
        deduped.append(path)
        if len(deduped) >= limit:
            break
    return deduped
