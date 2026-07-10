from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.rag.graph_retriever import GraphPath, graph_retrieval_enabled, retrieve_graph_context
from app.rag.retriever import RetrievedChunk, retrieve_chunks


@dataclass
class HybridRetrievalResult:
    chunks: list[RetrievedChunk]
    graph_paths: list[GraphPath]
    retrieval_mode: str


def _boost_chunks_with_graph(
    chunks: list[RetrievedChunk], graph_paths: list[GraphPath]
) -> list[RetrievedChunk]:
    if not chunks or not graph_paths:
        return chunks

    boost_by_filename: dict[str, float] = {}
    for path in graph_paths:
        if not path.document_filename:
            continue
        boost_by_filename[path.document_filename] = max(
            boost_by_filename.get(path.document_filename, 0.0),
            path.score,
        )

    boosted = [
        RetrievedChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            document_filename=chunk.document_filename,
            content=chunk.content,
            score=chunk.score + 0.15 * boost_by_filename.get(chunk.document_filename, 0.0),
        )
        for chunk in chunks
    ]
    return sorted(boosted, key=lambda item: item.score, reverse=True)


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]], *, k: int = 60
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def _rerank_chunks_with_rrf(
    vector_chunks: list[RetrievedChunk], graph_paths: list[GraphPath]
) -> list[RetrievedChunk]:
    if not vector_chunks:
        return vector_chunks

    vector_ranking = [chunk.chunk_id for chunk in vector_chunks]
    graph_ranking: list[str] = []
    seen: set[str] = set()
    for path in sorted(graph_paths, key=lambda item: item.score, reverse=True):
        if not path.document_filename:
            continue
        for chunk in vector_chunks:
            if chunk.document_filename != path.document_filename:
                continue
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            graph_ranking.append(chunk.chunk_id)

    if not graph_ranking:
        return _boost_chunks_with_graph(vector_chunks, graph_paths)

    fused_scores = dict(reciprocal_rank_fusion([vector_ranking, graph_ranking]))
    reranked = [
        RetrievedChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            document_filename=chunk.document_filename,
            content=chunk.content,
            score=fused_scores.get(chunk.chunk_id, chunk.score),
        )
        for chunk in vector_chunks
    ]
    return sorted(reranked, key=lambda item: item.score, reverse=True)


def retrieve_hybrid(db: Session, query: str, top_k: int | None = None) -> HybridRetrievalResult:
    settings = get_settings()
    k = top_k or settings.rag_top_k
    vector_chunks = retrieve_chunks(db, query, top_k=k)

    if not settings.hybrid_retrieval_enabled or not graph_retrieval_enabled():
        return HybridRetrievalResult(
            chunks=vector_chunks,
            graph_paths=[],
            retrieval_mode="vector",
        )

    graph_paths = retrieve_graph_context(query)
    if settings.hybrid_use_rrf:
        chunks = _rerank_chunks_with_rrf(vector_chunks, graph_paths)
    else:
        chunks = _boost_chunks_with_graph(vector_chunks, graph_paths)

    return HybridRetrievalResult(
        chunks=chunks[:k],
        graph_paths=graph_paths,
        retrieval_mode="hybrid",
    )
