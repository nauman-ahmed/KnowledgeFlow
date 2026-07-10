from typing import Any


def _concepts_from_cypher_records(records: list[dict[str, Any]]) -> set[str]:
    concepts: set[str] = set()
    list_keys = {
        "related_concepts",
        "directly_linked",
        "co_mentioned_in_documents",
        "frequently_co_occurring",
    }
    for record in records:
        for key, value in record.items():
            if key in list_keys and isinstance(value, list):
                concepts.update(item for item in value if isinstance(item, str) and item)
            elif isinstance(value, str) and value and key.endswith("concept"):
                concepts.add(value)
            elif isinstance(value, str) and value and key in {"concept", "principle", "name"}:
                concepts.add(value)
    return concepts


def build_graph_context(final_state: dict[str, Any]) -> dict[str, Any] | None:
    graph_paths = final_state.get("graph_paths") or []
    concepts: set[str] = set()
    for path in graph_paths:
        for concept in path.get("concepts") or []:
            if concept:
                concepts.add(concept)

    cypher_query = final_state.get("cypher_query") or None
    cypher_error = final_state.get("cypher_error")
    graph_results = final_state.get("graph_query_results") or []
    concepts.update(_concepts_from_cypher_records(graph_results))
    retrieval_mode = final_state.get("retrieval_mode")

    if not graph_paths and not cypher_query and not concepts and not graph_results:
        return None

    return {
        "retrieval_mode": retrieval_mode,
        "related_concepts": sorted(concepts),
        "graph_paths": [
            path.get("description", "")
            for path in graph_paths
            if path.get("description")
        ],
        "cypher_query": cypher_query,
        "cypher_error": cypher_error,
        "graph_results_count": len(graph_results),
    }
