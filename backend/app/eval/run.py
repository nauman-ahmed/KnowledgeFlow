"""RAG / GraphRAG evaluation CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session_factory, init_db
from app.core.llm import get_openai_client
from app.eval.metrics import context_hit, graph_hit, hybrid_hit, summarize_rates
from app.graph.cypher_executor import query_graph_cypher
from app.guardrails.output import generate_structured_answer
from app.rag.graph_retriever import graph_retrieval_enabled, retrieve_graph_context
from app.rag.hybrid_retriever import retrieve_hybrid
from app.rag.prompts import (
    SYSTEM_PROMPT,
    chunks_to_citations,
    format_context,
    format_cypher_context,
    format_graph_context,
    format_hybrid_context,
)
from app.rag.retriever import retrieve_chunks
from app.schemas.chat import SourceCitation

EvalMode = Literal["vector", "hybrid", "graph"]


def _load_dataset(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("cases", []))


def _score_faithfulness(
    client,
    question: str,
    reference: str,
    answer: str,
    context: str,
) -> dict:
    prompt = (
        "You are an evaluation judge for a RAG system.\n"
        "Score the answer on faithfulness (grounded in context) from 0.0 to 1.0.\n"
        'Return ONLY JSON: {"faithfulness": float, "reason": "short explanation"}\n\n'
        f"Question: {question}\n\n"
        f"Reference answer: {reference}\n\n"
        f"Retrieved context:\n{context[:3000]}\n\n"
        f"Generated answer:\n{answer}"
    )
    settings = get_settings()
    response = client.chat.completions.create(
        model=settings.llm_chat_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    return json.loads(raw)


def _build_context(
    *,
    mode: EvalMode,
    chunks,
    graph_paths,
    cypher_query: str = "",
    cypher_records: list[dict] | None = None,
    cypher_error: str | None = None,
) -> str:
    if mode == "vector":
        return format_context(chunks)
    if mode == "graph":
        sections = [format_graph_context(graph_paths)]
        if cypher_query:
            sections.append(
                format_cypher_context(
                    cypher_query,
                    cypher_records or [],
                    error=cypher_error,
                )
            )
        return "\n\n---\n\n".join(sections)
    return format_hybrid_context(chunks, graph_paths)


def _run_ragas_eval(cases: list[dict], results: list[dict]) -> dict | None:
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, faithfulness
    except ImportError:
        return None

    rows = {
        "question": [c["question"] for c in cases],
        "answer": [r["answer"] for r in results],
        "contexts": [r["contexts"] for r in results],
        "ground_truth": [c["reference_answer"] for c in cases],
    }
    dataset = Dataset.from_dict(rows)
    scores = evaluate(dataset, metrics=[faithfulness, answer_relevancy])
    return dict(scores)


def evaluate_case(db: Session, case: dict, mode: EvalMode) -> dict:
    question = case["question"]
    expected_documents = case.get("expected_documents", [])
    expected_graph_entities = case.get("expected_graph_entities", [])

    chunks = []
    graph_paths = []
    retrieval_mode = mode
    cypher_query = ""
    cypher_records: list[dict] = []
    cypher_error = None
    cypher_success: bool | None = None

    if mode in {"vector", "hybrid"}:
        if mode == "vector":
            chunks = retrieve_chunks(db, question)
        else:
            hybrid = retrieve_hybrid(db, question)
            chunks = hybrid.chunks
            graph_paths = hybrid.graph_paths
            retrieval_mode = hybrid.retrieval_mode

    if mode in {"graph", "hybrid"} and not graph_paths and graph_retrieval_enabled():
        graph_paths = retrieve_graph_context(question)

    if mode == "graph" or case.get("graph_query"):
        graph_query = case.get("graph_query") or question
        if graph_retrieval_enabled():
            cypher_result = query_graph_cypher(graph_query)
            cypher_query = cypher_result.get("cypher_query", "")
            cypher_records = cypher_result.get("records", [])
            cypher_error = cypher_result.get("error")
            cypher_success = bool(cypher_result.get("success"))

    context = _build_context(
        mode=mode,
        chunks=chunks,
        graph_paths=graph_paths,
        cypher_query=cypher_query,
        cypher_records=cypher_records,
        cypher_error=cypher_error,
    )
    citations = chunks_to_citations(chunks)
    fallback_sources = [SourceCitation(**c) for c in citations]

    answer_messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n## Retrieved context\n\n{context}"},
        {"role": "user", "content": question},
    ]
    client = get_openai_client()
    structured = generate_structured_answer(
        client,
        answer_messages,
        fallback_sources=fallback_sources,
    )

    retrieved_filenames = {chunk.document_filename for chunk in chunks}
    context_ok = context_hit(retrieved_filenames, expected_documents)
    graph_ok = graph_hit(
        graph_paths,
        expected_entities=expected_graph_entities,
        expected_documents=expected_documents,
    )

    faith = _score_faithfulness(
        client,
        question,
        case.get("reference_answer", ""),
        structured.summary,
        context,
    )

    return {
        "id": case["id"],
        "question": question,
        "mode": mode,
        "answer": structured.summary,
        "contexts": [chunk.content for chunk in chunks],
        "context_hit": context_ok,
        "graph_hit": graph_ok,
        "hybrid_hit": hybrid_hit(context_ok, graph_ok),
        "retrieved_documents": sorted(retrieved_filenames),
        "expected_documents": expected_documents,
        "expected_graph_entities": expected_graph_entities,
        "graph_paths": [path.description for path in graph_paths],
        "retrieval_mode": retrieval_mode,
        "cypher_query": cypher_query,
        "cypher_success": cypher_success,
        "graph_results_count": len(cypher_records),
        "faithfulness": float(faith.get("faithfulness", 0)),
        "faithfulness_reason": faith.get("reason", ""),
        "confidence": structured.confidence,
    }


def _aggregate_report(path: Path, mode: EvalMode, results: list[dict]) -> dict:
    report = {
        "dataset": str(path),
        "mode": mode,
        "total_cases": len(results),
        "context_hit_rate": summarize_rates([r["context_hit"] for r in results]),
        "avg_faithfulness": round(
            sum(r["faithfulness"] for r in results) / len(results), 3
        )
        if results
        else 0.0,
        "results": results,
    }

    if mode in {"hybrid", "graph"}:
        report["graph_hit_rate"] = summarize_rates([r["graph_hit"] for r in results])
    if mode == "hybrid":
        report["hybrid_hit_rate"] = summarize_rates([r["hybrid_hit"] for r in results])

    cypher_cases = [r for r in results if r.get("cypher_success") is not None]
    if cypher_cases:
        report["cypher_success_rate"] = summarize_rates(
            [bool(r["cypher_success"]) for r in cypher_cases]
        )
        report["cypher_cases"] = len(cypher_cases)

    return report


def run_eval(dataset_path: Path | None = None, mode: EvalMode = "vector") -> dict:
    settings = get_settings()
    path = dataset_path or settings.eval_dataset_path
    cases = _load_dataset(path)
    init_db()

    results: list[dict] = []
    SessionLocal = get_session_factory()
    with SessionLocal() as db:
        for case in cases:
            print(f"Evaluating [{mode}]: {case['id']}…", file=sys.stderr)
            results.append(evaluate_case(db, case, mode))

    report = _aggregate_report(path, mode, results)
    ragas_scores = _run_ragas_eval(cases, results)
    if ragas_scores:
        report["ragas"] = ragas_scores
    return report


def _metrics_below_threshold(report: dict, threshold: float) -> list[str]:
    failures: list[str] = []
    if report["context_hit_rate"] < threshold:
        failures.append(f"context_hit_rate={report['context_hit_rate']}")
    if report["avg_faithfulness"] < threshold:
        failures.append(f"avg_faithfulness={report['avg_faithfulness']}")
    if report.get("graph_hit_rate", 1.0) < threshold:
        failures.append(f"graph_hit_rate={report['graph_hit_rate']}")
    if report.get("hybrid_hit_rate", 1.0) < threshold:
        failures.append(f"hybrid_hit_rate={report['hybrid_hit_rate']}")
    if report.get("cypher_success_rate", 1.0) < threshold:
        failures.append(f"cypher_success_rate={report['cypher_success_rate']}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Run KnowledgeFlow RAG evaluation")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to eval/dataset.json (default: from settings)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write JSON report to file (default: stdout)",
    )
    parser.add_argument(
        "--mode",
        choices=["vector", "hybrid", "graph"],
        default="vector",
        help="Evaluation retrieval mode (default: vector)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Minimum acceptable metric score (default: 0.7)",
    )
    args = parser.parse_args()

    report = run_eval(args.dataset, mode=args.mode)
    output = json.dumps(report, indent=2)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)

    failures = _metrics_below_threshold(report, args.threshold)
    if failures:
        print(
            f"\nWarning: metrics below {args.threshold} threshold: {', '.join(failures)}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
