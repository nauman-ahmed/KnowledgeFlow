import re

BLOCKED_PATTERN = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|FOREACH|LOAD\s+CSV|"
    r"CALL\s+\{?\s*dbms|CALL\s+\{?\s*apoc\.|CALL\s+\{?\s*gds\.)\b",
    re.IGNORECASE,
)

ALLOWED_START = re.compile(r"^(MATCH|OPTIONAL\s+MATCH|WITH)\b", re.IGNORECASE)


class CypherSandboxError(ValueError):
    pass


def _strip_comments(cypher: str) -> str:
    lines = []
    for line in cypher.splitlines():
        stripped = line.split("//", 1)[0].strip()
        if stripped:
            lines.append(stripped)
    return " ".join(lines)


def validate_read_only_cypher(cypher: str) -> str:
    cleaned = _strip_comments(cypher).strip().rstrip(";")
    if not cleaned:
        raise CypherSandboxError("Empty Cypher query")

    if BLOCKED_PATTERN.search(cleaned):
        raise CypherSandboxError("Write or admin operations are not allowed")

    if not ALLOWED_START.match(cleaned):
        raise CypherSandboxError("Query must start with MATCH, OPTIONAL MATCH, or WITH")

    if re.search(r"\bRETURN\b", cleaned, re.IGNORECASE) is None:
        raise CypherSandboxError("Query must include RETURN")

    return cleaned


def ensure_limit(cypher: str, max_limit: int = 25) -> str:
    cleaned = validate_read_only_cypher(cypher)
    if re.search(r"\bLIMIT\s+\d+\b", cleaned, re.IGNORECASE):
        return cleaned
    return f"{cleaned} LIMIT {max_limit}"
