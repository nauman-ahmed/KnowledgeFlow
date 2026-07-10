from app.eval.metrics import context_hit, graph_hit, hybrid_hit, summarize_rates
from app.rag.graph_retriever import GraphPath


def test_context_hit_matches_expected_document() -> None:
    assert context_hit({"compound-interest.txt", "other.md"}, ["compound-interest.txt"]) is True
    assert context_hit({"other.md"}, ["compound-interest.txt"]) is False


def test_context_hit_with_no_expectations() -> None:
    assert context_hit(set(), []) is True


def test_graph_hit_matches_entity_in_path_description() -> None:
    paths = [
        GraphPath(
            path_id="p1",
            description="compound interest --RELATED_TO--> simple interest",
            score=1.0,
            document_filename="compound-interest.txt",
            concepts=["compound interest", "simple interest"],
        )
    ]
    assert graph_hit(
        paths,
        expected_entities=["simple interest"],
        expected_documents=["compound-interest.txt"],
    )


def test_graph_hit_requires_entity_when_only_entities_expected() -> None:
    paths = [
        GraphPath(
            path_id="p1",
            description="unrelated concept path",
            score=1.0,
            document_filename="other.txt",
            concepts=["other"],
        )
    ]
    assert graph_hit(paths, expected_entities=["compound interest"]) is False


def test_hybrid_hit_is_true_when_either_source_hits() -> None:
    assert hybrid_hit(context_ok=False, graph_ok=True) is True
    assert hybrid_hit(context_ok=True, graph_ok=False) is True
    assert hybrid_hit(context_ok=False, graph_ok=False) is False


def test_summarize_rates() -> None:
    assert summarize_rates([True, False, True]) == 0.667


def test_aggregate_report_includes_graph_metrics() -> None:
    from pathlib import Path

    from app.eval.run import _aggregate_report

    report = _aggregate_report(
        Path("eval/dataset.json"),
        "hybrid",
        [
            {
                "context_hit": True,
                "graph_hit": False,
                "hybrid_hit": True,
                "faithfulness": 0.9,
                "cypher_success": True,
            },
            {
                "context_hit": False,
                "graph_hit": True,
                "hybrid_hit": True,
                "faithfulness": 0.8,
                "cypher_success": False,
            },
        ],
    )
    assert report["mode"] == "hybrid"
    assert report["graph_hit_rate"] == 0.5
    assert report["hybrid_hit_rate"] == 1.0
    assert report["cypher_success_rate"] == 0.5
