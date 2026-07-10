import pytest

from app.graph.cypher_sandbox import CypherSandboxError, ensure_limit, validate_read_only_cypher


def test_validate_allows_read_match_query() -> None:
    cypher = """
    MATCH (c:Concept)<-[:MENTIONS]-(d:Document)
    WHERE toLower(c.name) CONTAINS 'investing'
    RETURN d.filename AS filename
    LIMIT 10
    """
    cleaned = validate_read_only_cypher(cypher)
    assert "MATCH" in cleaned
    assert "RETURN" in cleaned


@pytest.mark.parametrize(
    "cypher",
    [
        "CREATE (n:Concept {name: 'x'}) RETURN n",
        "MATCH (n) DELETE n",
        "MATCH (n) SET n.name = 'x' RETURN n",
        "CALL dbms.procedures() YIELD name RETURN name",
    ],
)
def test_validate_blocks_write_and_admin_queries(cypher: str) -> None:
    with pytest.raises(CypherSandboxError):
        validate_read_only_cypher(cypher)


def test_ensure_limit_appends_limit_when_missing() -> None:
    cypher = "MATCH (d:Document) RETURN d.filename"
    result = ensure_limit(cypher, max_limit=15)
    assert result.endswith("LIMIT 15")
