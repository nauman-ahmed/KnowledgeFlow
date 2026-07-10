import argparse
import sys

from app.ingest.pipeline import run_ingest


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest documents from content/ into pgvector")
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="Skip files whose content hash already exists with status=ready",
    )
    parser.add_argument(
        "--skip-graph",
        action="store_true",
        help="Ingest vectors only; skip Neo4j graph extraction",
    )
    parser.add_argument(
        "--graph-only",
        action="store_true",
        help="Run graph extraction on already-ingested documents (requires Neo4j + LLM key)",
    )
    args = parser.parse_args()

    results = run_ingest(
        changed_only=args.changed_only,
        skip_graph=args.skip_graph,
        graph_only=args.graph_only,
    )
    ingested = skipped = failed = 0
    for item in results:
        if item.action == "ingested":
            ingested += 1
            print(f"✓ {item.path}: {item.detail}")
        elif item.action == "skipped":
            skipped += 1
            print(f"○ {item.path}: {item.detail or 'unchanged'}")
        else:
            failed += 1
            print(f"✗ {item.path}: {item.detail}", file=sys.stderr)

    print(f"\nDone: {ingested} ingested, {skipped} skipped, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
