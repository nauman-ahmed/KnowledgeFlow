from pathlib import Path

from neo4j import Driver, GraphDatabase

from app.core.config import get_settings

_driver: Driver | None = None
_SCHEMA_PATH = Path(__file__).parent / "schema.cypher"


def get_neo4j_driver() -> Driver | None:
    """Return a singleton Neo4j driver, or None when graph storage is disabled."""
    global _driver
    settings = get_settings()
    if not settings.neo4j_enabled:
        return None
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def check_neo4j() -> bool | None:
    """Return True if connected, False on error, None when Neo4j is disabled."""
    driver = get_neo4j_driver()
    if driver is None:
        return None
    try:
        driver.verify_connectivity()
        return True
    except Exception:
        return False


def _load_schema_statements() -> list[str]:
    raw = _SCHEMA_PATH.read_text(encoding="utf-8")
    statements: list[str] = []
    buffer: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        buffer.append(stripped)
        if stripped.endswith(";"):
            statement = " ".join(buffer).rstrip(";").strip()
            if statement:
                statements.append(statement)
            buffer = []
    if buffer:
        statement = " ".join(buffer).rstrip(";").strip()
        if statement:
            statements.append(statement)
    return statements


def init_graph_schema() -> None:
    """Apply idempotent constraints and indexes from schema.cypher."""
    driver = get_neo4j_driver()
    if driver is None:
        return
    statements = _load_schema_statements()
    with driver.session() as session:
        for statement in statements:
            session.run(statement)


def reset_neo4j_driver_for_tests() -> None:
    """Clear cached driver — test helper only."""
    close_neo4j_driver()
    get_settings.cache_clear()
