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


def build_system_message(chunks: list[RetrievedChunk]) -> str:
    context = format_context(chunks)
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
