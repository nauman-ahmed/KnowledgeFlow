from unittest.mock import MagicMock, patch

from app.rag.graph_retriever import GraphPath
from app.rag.hybrid_retriever import (
    reciprocal_rank_fusion,
    retrieve_hybrid,
)
from app.rag.prompts import format_graph_context, format_hybrid_context
from app.rag.query_terms import extract_query_terms
from app.rag.retriever import RetrievedChunk


def test_extract_query_terms_filters_stopwords() -> None:
    terms = extract_query_terms("What is compound interest in investing?")
    assert "compound" in terms
    assert "interest" in terms
    assert "what" not in terms


def test_reciprocal_rank_fusion_combines_rankings() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "a"]])
    assert fused[0][0] in {"a", "b"}
    assert len(fused) == 3


def test_format_graph_context_renders_paths() -> None:
    text = format_graph_context(
        [
            GraphPath(
                path_id="p1",
                description="compound interest --RELATED_TO--> simple interest",
                score=1.0,
                document_filename="intro-to-investing.md",
                concepts=["compound interest", "simple interest"],
            )
        ]
    )
    assert "Graph-grounded context" in text
    assert "intro-to-investing.md" in text


def test_format_hybrid_context_includes_vector_and_graph_sections() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            document_title="Intro",
            document_filename="intro.md",
            content="Compound interest grows over time.",
            score=0.9,
        )
    ]
    paths = [
        GraphPath(
            path_id="p1",
            description="compound interest <-MENTIONS- Intro (intro.md)",
            score=1.0,
            document_filename="intro.md",
        )
    ]
    text = format_hybrid_context(chunks, paths)
    assert "[Source 1: intro.md]" in text
    assert "[Graph 1]" in text


@patch("app.rag.hybrid_retriever.retrieve_graph_context")
@patch("app.rag.hybrid_retriever.retrieve_chunks")
@patch("app.rag.hybrid_retriever.graph_retrieval_enabled")
@patch("app.rag.hybrid_retriever.get_settings")
def test_retrieve_hybrid_combines_vector_and_graph(
    mock_settings,
    mock_graph_enabled,
    mock_retrieve_chunks,
    mock_graph_context,
) -> None:
    mock_settings.return_value.rag_top_k = 5
    mock_settings.return_value.hybrid_retrieval_enabled = True
    mock_settings.return_value.hybrid_use_rrf = True
    mock_graph_enabled.return_value = True
    mock_retrieve_chunks.return_value = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            document_title="Intro",
            document_filename="intro.md",
            content="Compound interest grows.",
            score=0.8,
        )
    ]
    mock_graph_context.return_value = [
        GraphPath(
            path_id="p1",
            description="compound interest <-MENTIONS- Intro (intro.md)",
            score=1.0,
            document_filename="intro.md",
        )
    ]

    result = retrieve_hybrid(MagicMock(), "compound interest")
    assert result.retrieval_mode == "hybrid"
    assert len(result.chunks) == 1
    assert len(result.graph_paths) == 1


@patch("app.rag.hybrid_retriever.graph_retrieval_enabled")
@patch("app.rag.hybrid_retriever.retrieve_chunks")
@patch("app.rag.hybrid_retriever.get_settings")
def test_retrieve_hybrid_falls_back_to_vector(
    mock_settings,
    mock_retrieve_chunks,
    mock_graph_enabled,
) -> None:
    mock_settings.return_value.rag_top_k = 5
    mock_settings.return_value.hybrid_retrieval_enabled = True
    mock_graph_enabled.return_value = False
    mock_retrieve_chunks.return_value = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            document_title="Intro",
            document_filename="intro.md",
            content="text",
            score=0.5,
        )
    ]

    result = retrieve_hybrid(MagicMock(), "compound interest")
    assert result.retrieval_mode == "vector"
    assert result.graph_paths == []
