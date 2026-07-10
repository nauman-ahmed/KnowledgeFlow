from dataclasses import dataclass, field
from typing import Any

from neo4j import Driver

from app.graph.resolver import entity_key, entity_key_field
from app.ontology.loader import NEO4J_LABEL_BY_CLASS, NEO4J_RELATION_BY_PROPERTY, OntologyLoader
from app.ontology.schemas import ExtractedEntity, ExtractedRelation, ExtractionResult


@dataclass
class ChunkExtraction:
    chunk_id: str
    chunk_index: int
    chunk_text: str
    result: ExtractionResult


@dataclass
class GraphWriteStats:
    entities: int = 0
    relations: int = 0
    citations: int = 0
    chunks: int = 0


@dataclass
class _ResolvedEntity:
    entity_type: str
    name: str
    key: str
    key_field: str
    label: str
    extra: dict[str, Any] = field(default_factory=dict)


class GraphWriter:
    """Write document, chunk, entity, and relationship nodes to Neo4j."""

    def __init__(self, driver: Driver, loader: OntologyLoader) -> None:
        self._driver = driver
        self._loader = loader

    def clear_document_graph(self, document_id: str) -> None:
        query = """
        MATCH (d:Document {id: $document_id})-[:HAS_CHUNK]->(c:Chunk)
        DETACH DELETE c
        """
        self._run(query, document_id=document_id)
        query = """
        MATCH (d:Document {id: $document_id})
        OPTIONAL MATCH (d)-[r:MENTIONS|CITES|AUTHORED_BY|DESCRIBES|REPORTS_EXPERIMENT]->()
        DELETE r
        """
        self._run(query, document_id=document_id)

    def write_document(
        self,
        *,
        document_id: str,
        title: str,
        filename: str,
        chunk_extractions: list[ChunkExtraction],
    ) -> GraphWriteStats:
        stats = GraphWriteStats()
        self.clear_document_graph(document_id)
        self._upsert_document(document_id, title, filename)

        resolved_entities: dict[tuple[str, str], _ResolvedEntity] = {}
        for chunk_extraction in chunk_extractions:
            stats.chunks += 1
            self._upsert_chunk(
                chunk_id=chunk_extraction.chunk_id,
                document_id=document_id,
                chunk_index=chunk_extraction.chunk_index,
                text=chunk_extraction.chunk_text,
            )
            for entity in chunk_extraction.result.entities:
                resolved = self._resolve_entity(entity)
                resolved_entities[(resolved.entity_type, resolved.name.lower())] = resolved
            for citation in chunk_extraction.result.citations:
                resolved = self._resolve_citation(citation.text)
                resolved_entities[(resolved.entity_type, resolved.name.lower())] = resolved
                stats.citations += 1
            for relation in chunk_extraction.result.relations:
                for entity_type, entity_name in (
                    (relation.source_type, relation.source_name),
                    (relation.target_type, relation.target_name),
                ):
                    if entity_type == "Document":
                        continue
                    endpoint = self._relation_endpoint(entity_type, entity_name, document_id)
                    if endpoint is not None:
                        resolved_entities[(endpoint.entity_type, endpoint.name.lower())] = endpoint

        for resolved in resolved_entities.values():
            self._upsert_entity(resolved)
            stats.entities += 1

        document_relations = self._document_relations(document_id, resolved_entities.values())
        chunk_relations = [
            relation
            for chunk_extraction in chunk_extractions
            for relation in chunk_extraction.result.relations
        ]
        for relation in document_relations + chunk_relations:
            if self._upsert_relation(relation, document_id=document_id):
                stats.relations += 1

        return stats

    def _resolve_entity(self, entity: ExtractedEntity) -> _ResolvedEntity:
        key = entity_key(entity.type, entity.name, entity.uri)
        label = self._loader.neo4j_label(entity.type)
        return _ResolvedEntity(
            entity_type=entity.type,
            name=entity.name,
            key=key,
            key_field=entity_key_field(entity.type),
            label=label,
        )

    def _resolve_citation(self, text: str) -> _ResolvedEntity:
        key = entity_key("Citation", text)
        return _ResolvedEntity(
            entity_type="Citation",
            name=text,
            key=key,
            key_field=entity_key_field("Citation"),
            label=self._loader.neo4j_label("Citation"),
            extra={"text": text},
        )

    def _document_relations(
        self, document_id: str, entities: list[_ResolvedEntity]
    ) -> list[ExtractedRelation]:
        relations: list[ExtractedRelation] = []
        for entity in entities:
            if entity.entity_type == "Concept":
                relations.append(
                    ExtractedRelation(
                        predicate="mentions",
                        source_type="Document",
                        source_name=document_id,
                        target_type="Concept",
                        target_name=entity.name,
                    )
                )
            elif entity.entity_type == "Citation":
                relations.append(
                    ExtractedRelation(
                        predicate="cites",
                        source_type="Document",
                        source_name=document_id,
                        target_type="Citation",
                        target_name=entity.name,
                    )
                )
            elif entity.entity_type == "Author":
                relations.append(
                    ExtractedRelation(
                        predicate="authoredBy",
                        source_type="Document",
                        source_name=document_id,
                        target_type="Author",
                        target_name=entity.name,
                    )
                )
            elif entity.entity_type == "Dataset":
                relations.append(
                    ExtractedRelation(
                        predicate="describes",
                        source_type="Document",
                        source_name=document_id,
                        target_type="Dataset",
                        target_name=entity.name,
                    )
                )
            elif entity.entity_type == "Experiment":
                relations.append(
                    ExtractedRelation(
                        predicate="reportsExperiment",
                        source_type="Document",
                        source_name=document_id,
                        target_type="Experiment",
                        target_name=entity.name,
                    )
                )
        return relations

    def _upsert_document(self, document_id: str, title: str, filename: str) -> None:
        query = """
        MERGE (d:Document {id: $id})
        SET d.title = $title,
            d.filename = $filename,
            d.updated_at = datetime()
        """
        self._run(query, id=document_id, title=title, filename=filename)

    def _upsert_chunk(
        self, *, chunk_id: str, document_id: str, chunk_index: int, text: str
    ) -> None:
        query = """
        MATCH (d:Document {id: $document_id})
        MERGE (c:Chunk {id: $chunk_id})
        SET c.chunk_index = $chunk_index,
            c.text = $text,
            c.updated_at = datetime()
        MERGE (d)-[:HAS_CHUNK]->(c)
        MERGE (c)-[:PART_OF]->(d)
        """
        self._run(
            query,
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_index=chunk_index,
            text=text[:4000],
        )

    def _upsert_entity(self, entity: _ResolvedEntity) -> None:
        if entity.entity_type == "Citation":
            query = f"""
            MERGE (n:{entity.label} {{{entity.key_field}: $key}})
            SET n.text = $text,
                n.name = $name,
                n.updated_at = datetime()
            """
            self._run(
                query,
                key=entity.key,
                text=entity.extra.get("text", entity.name),
                name=entity.name,
            )
            return

        query = f"""
        MERGE (n:{entity.label} {{{entity.key_field}: $key}})
        SET n.name = $name,
            n.updated_at = datetime()
        """
        self._run(query, key=entity.key, name=entity.name)

    def _upsert_relation(self, relation: ExtractedRelation, *, document_id: str) -> bool:
        if relation.predicate not in NEO4J_RELATION_BY_PROPERTY:
            return False

        source = self._relation_endpoint(relation.source_type, relation.source_name, document_id)
        target = self._relation_endpoint(relation.target_type, relation.target_name, document_id)
        if source is None or target is None:
            return False

        rel_type = self._loader.neo4j_relationship(relation.predicate)
        query = f"""
        MATCH (s:{source.label} {{{source.key_field}: $source_key}})
        MATCH (t:{target.label} {{{target.key_field}: $target_key}})
        MERGE (s)-[r:{rel_type}]->(t)
        SET r.updated_at = datetime()
        """
        self._run(query, source_key=source.key, target_key=target.key)
        return True

    def _relation_endpoint(
        self, entity_type: str, name: str, document_id: str
    ) -> _ResolvedEntity | None:
        if entity_type not in NEO4J_LABEL_BY_CLASS:
            return None
        if entity_type == "Document":
            return _ResolvedEntity(
                entity_type="Document",
                name=document_id,
                key=document_id,
                key_field="id",
                label="Document",
            )
        return _ResolvedEntity(
            entity_type=entity_type,
            name=name,
            key=entity_key(entity_type, name),
            key_field=entity_key_field(entity_type),
            label=self._loader.neo4j_label(entity_type),
        )

    def _run(self, query: str, **params: Any) -> None:
        with self._driver.session() as session:
            session.run(query, **params)
