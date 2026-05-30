"""RAG evaluation CLI — retrieval hit rate + faithfulness scoring."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session_factory, init_db
from app.core.llm import get_openai_client
from app.guardrails.output import generate_structured_answer
from app.rag.prompts import SYSTEM_PROMPT, chunks_to_citations, format_context
from app.rag.retriever import retrieve_chunks
from app.schemas.chat import SourceCitation


def _load_dataset(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("cases", []))


def _context_hit(retrieved_filenames: set[str], expected: list[str]) -> bool:
    return any(doc in retrieved_filenames for doc in expected)


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
        "Return ONLY JSON: {\"faithfulness\": float, \"reason\": \"short explanation\"}\n\n"
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


def evaluate_case(db: Session, case: dict) -> dict:
    question = case["question"]
    chunks = retrieve_chunks(db, question)
    context = format_context(chunks)
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

    retrieved_filenames = {c.document_filename for c in chunks}
    context_hit = _context_hit(retrieved_filenames, case.get("expected_documents", []))

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
        "answer": structured.summary,
        "contexts": [c.content for c in chunks],
        "context_hit": context_hit,
        "retrieved_documents": sorted(retrieved_filenames),
        "expected_documents": case.get("expected_documents", []),
        "faithfulness": float(faith.get("faithfulness", 0)),
        "faithfulness_reason": faith.get("reason", ""),
        "confidence": structured.confidence,
    }


def run_eval(dataset_path: Path | None = None) -> dict:
    settings = get_settings()
    path = dataset_path or settings.eval_dataset_path
    cases = _load_dataset(path)
    init_db()

    results: list[dict] = []
    SessionLocal = get_session_factory()
    with SessionLocal() as db:
        for case in cases:
            print(f"Evaluating: {case['id']}…", file=sys.stderr)
            results.append(evaluate_case(db, case))

    context_hits = sum(1 for r in results if r["context_hit"])
    avg_faith = sum(r["faithfulness"] for r in results) / len(results) if results else 0.0

    report = {
        "dataset": str(path),
        "total_cases": len(results),
        "context_hit_rate": round(context_hits / len(results), 3) if results else 0.0,
        "avg_faithfulness": round(avg_faith, 3),
        "results": results,
    }

    ragas_scores = _run_ragas_eval(cases, results)
    if ragas_scores:
        report["ragas"] = ragas_scores

    return report


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
    args = parser.parse_args()

    report = run_eval(args.dataset)
    output = json.dumps(report, indent=2)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)

    threshold = 0.7
    if report["context_hit_rate"] < threshold or report["avg_faithfulness"] < threshold:
        print(
            f"\nWarning: metrics below {threshold} threshold "
            f"(hit={report['context_hit_rate']}, faith={report['avg_faithfulness']})",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
