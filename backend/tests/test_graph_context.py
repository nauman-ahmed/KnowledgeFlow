from app.services.graph_context import build_graph_context


def test_build_graph_context_from_final_state() -> None:
    context = build_graph_context(
        {
            "retrieval_mode": "hybrid",
            "graph_paths": [
                {
                    "description": "compound interest --RELATED_TO--> simple interest",
                    "concepts": ["compound interest", "simple interest"],
                }
            ],
            "cypher_query": "MATCH (c:Concept) RETURN c.name LIMIT 5",
            "graph_query_results": [{"name": "compound interest"}],
        }
    )
    assert context is not None
    assert context["retrieval_mode"] == "hybrid"
    assert "compound interest" in context["related_concepts"]
    assert context["graph_results_count"] == 1


def test_build_graph_context_extracts_concepts_from_cypher_lists() -> None:
    context = build_graph_context(
        {
            "retrieval_mode": "graph",
            "graph_paths": [],
            "cypher_query": "MATCH (c:Concept) RETURN c",
            "graph_query_results": [
                {
                    "concept": "compound interest",
                    "directly_linked": ["Simple interest"],
                    "co_mentioned_in_documents": ["Rule of 72", "diversification"],
                }
            ],
        }
    )
    assert context is not None
    assert "compound interest" in context["related_concepts"]
    assert "Simple interest" in context["related_concepts"]
    assert "Rule of 72" in context["related_concepts"]
    assert "diversification" in context["related_concepts"]


def test_build_graph_context_returns_none_without_graph_data() -> None:
    assert build_graph_context({"retrieval_mode": "vector"}) is None
