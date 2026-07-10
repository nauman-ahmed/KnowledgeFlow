GRAPH_SCHEMA_CONTEXT = """
Neo4j node labels and key properties:
- Document {id, title, filename}
- Chunk {id, text, chunk_index}
- Concept {uri, name}
- Author {id, name}
- Organization {id, name}
- Dataset {id, name}
- Experiment {id, name}
- Citation {id, text, name}

Relationship types:
- (Document)-[:HAS_CHUNK]->(Chunk)
- (Chunk)-[:PART_OF]->(Document)
- (Document)-[:MENTIONS]->(Concept)
- (Document)-[:AUTHORED_BY]->(Author)
- (Document)-[:CITES]->(Citation)
- (Document)-[:DESCRIBES]->(Dataset)
- (Document)-[:REPORTS_EXPERIMENT]->(Experiment)
- (Concept)-[:RELATED_TO]->(Concept)
- (Author)-[:AFFILIATED_WITH]->(Organization)

Read-only Cypher rules:
- Use MATCH / OPTIONAL MATCH / WITH / RETURN only
- Always include LIMIT (max 25)
- Use toLower() for case-insensitive name matching
"""

CYPHER_FEW_SHOT_EXAMPLES = """
User: What concepts relate to compound interest?
Cypher:
MATCH (c:Concept)
WHERE toLower(c.name) CONTAINS 'compound interest'
OPTIONAL MATCH (c)-[:RELATED_TO]-(related:Concept)
OPTIONAL MATCH (doc:Document)-[:MENTIONS]->(c)
OPTIONAL MATCH (doc)-[:MENTIONS]->(cooccur:Concept)
WHERE cooccur IS NULL OR cooccur <> c
RETURN c.name AS concept,
       collect(DISTINCT related.name) AS directly_linked,
       collect(DISTINCT cooccur.name) AS co_mentioned_in_documents
LIMIT 10

User: Which documents mention investing?
Cypher:
MATCH (c:Concept)<-[:MENTIONS]-(d:Document)
WHERE toLower(c.name) CONTAINS 'investing'
RETURN d.title AS title, d.filename AS filename
LIMIT 10

User: Who authored documents about study habits?
Cypher:
MATCH (c:Concept)<-[:MENTIONS]-(d:Document)-[:AUTHORED_BY]->(a:Author)
WHERE toLower(c.name) CONTAINS 'study'
RETURN DISTINCT a.name AS author, d.filename AS filename
LIMIT 10
"""
