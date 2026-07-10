from typing import Any

from app.core.config import get_settings
from app.graph.cypher_sandbox import CypherSandboxError, ensure_limit
from app.graph.neo4j_client import get_neo4j_driver


def execute_read_cypher(cypher: str) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.neo4j_enabled:
        raise RuntimeError("Neo4j is disabled")

    driver = get_neo4j_driver()
    if driver is None:
        raise RuntimeError("Neo4j driver unavailable")

    safe_cypher = ensure_limit(cypher, max_limit=settings.cypher_query_limit)
    with driver.session() as session:
        result = session.run(safe_cypher)
        return [dict(record) for record in result]


def query_graph_cypher(nl_query: str) -> dict[str, Any]:
    from app.graph.cypher_generator import generate_cypher_query

    cypher = generate_cypher_query(nl_query)
    try:
        records = execute_read_cypher(cypher)
    except CypherSandboxError as exc:
        return {
            "cypher_query": cypher,
            "records": [],
            "error": str(exc),
            "success": False,
        }
    except Exception as exc:
        return {
            "cypher_query": cypher,
            "records": [],
            "error": str(exc),
            "success": False,
        }

    return {
        "cypher_query": cypher,
        "records": records,
        "error": None,
        "success": True,
    }
