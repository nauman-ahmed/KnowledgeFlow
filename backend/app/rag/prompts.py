from app.rag.graph_retriever import GraphPath
from app.rag.retriever import RetrievedChunk

SYSTEM_PROMPT = (
    "You are KnowledgeFlow, a helpful assistant that answers questions "
    "using the curated knowledge library provided below.\n\n"
    "Rules:\n"
    "- Answer based on the provided context. If the context does not contain "
    "enough information, say so clearly.\n"
    "- Be concise and accurate. Use markdown when helpful.\n"
    "- Do not invent facts not supported by the context."
)


def format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No relevant documents were found in the knowledge library."

    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(
            f"[Source {i}: {chunk.document_filename}]\n{chunk.content.strip()}"
        )
    return "\n\n---\n\n".join(parts)


def format_graph_context(graph_paths: list[GraphPath]) -> str:
    if not graph_paths:
        return "No graph paths were found for this query."

    lines = ["Graph-grounded context:"]
    for idx, path in enumerate(graph_paths, start=1):
        suffix = f" (source: {path.document_filename})" if path.document_filename else ""
        lines.append(f"[Graph {idx}] {path.description}{suffix}")
    return "\n".join(lines)


def format_cypher_context(
    cypher_query: str, records: list[dict], *, error: str | None = None
) -> str:
    lines = ["Cypher query results:", f"Query: {cypher_query}"]
    if error:
        lines.append(f"Error: {error}")
        return "\n".join(lines)
    if not records:
        lines.append("No rows returned.")
        return "\n".join(lines)
    for idx, record in enumerate(records, start=1):
        parts = [f"{key}={value}" for key, value in record.items()]
        lines.append(f"[Row {idx}] " + ", ".join(parts))
    return "\n".join(lines)


def format_hybrid_context(chunks: list[RetrievedChunk], graph_paths: list[GraphPath]) -> str:
    sections = [format_context(chunks)]
    if graph_paths:
        sections.append(format_graph_context(graph_paths))
    return "\n\n---\n\n".join(sections)


def build_system_message(chunks: list[RetrievedChunk]) -> str:
    context = format_context(chunks)
    return f"{SYSTEM_PROMPT}\n\n## Retrieved context\n\n{context}"


def build_hybrid_system_message(
    chunks: list[RetrievedChunk], graph_paths: list[GraphPath]
) -> str:
    context = format_hybrid_context(chunks, graph_paths)
    return f"{SYSTEM_PROMPT}\n\n## Retrieved context\n\n{context}"


def chunks_to_citations(chunks: list[RetrievedChunk], excerpt_len: int = 300) -> list[dict]:
    citations: list[dict] = []
    seen: set[str] = set()
    for chunk in chunks:
        key = chunk.document_filename
        if key in seen:
            continue
        seen.add(key)
        excerpt = chunk.content.strip()
        if len(excerpt) > excerpt_len:
            excerpt = excerpt[: excerpt_len - 3].rstrip() + "..."
        citations.append({"document": chunk.document_filename, "excerpt": excerpt})
    return citations
