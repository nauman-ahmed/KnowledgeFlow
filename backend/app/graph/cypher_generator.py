import re

from openai import OpenAI

from app.core.config import get_settings
from app.core.llm import get_openai_client
from app.graph.cypher_schema import CYPHER_FEW_SHOT_EXAMPLES, GRAPH_SCHEMA_CONTEXT


def _parse_cypher_response(raw: str) -> str:
    text = raw.strip()
    fence = re.search(r"```(?:cypher)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    if "Cypher:" in text:
        return text.split("Cypher:", 1)[1].strip()
    return text.strip()


def generate_cypher_query(
    nl_query: str,
    *,
    client: OpenAI | None = None,
) -> str:
    settings = get_settings()
    llm = client or get_openai_client()
    prompt = (
        "Convert the user question into a read-only Neo4j Cypher query.\n"
        f"{GRAPH_SCHEMA_CONTEXT}\n\n"
        f"Examples:\n{CYPHER_FEW_SHOT_EXAMPLES}\n\n"
        f"User question: {nl_query}\n"
        "Return ONLY the Cypher query."
    )
    response = llm.chat.completions.create(
        model=settings.llm_chat_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
    )
    raw = response.choices[0].message.content or ""
    return _parse_cypher_response(raw)
