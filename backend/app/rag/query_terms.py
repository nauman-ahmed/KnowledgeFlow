import re

QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "about",
    "can",
    "does",
    "explain",
    "for",
    "how",
    "in",
    "is",
    "me",
    "of",
    "or",
    "tell",
    "the",
    "to",
    "what",
    "with",
    "you",
    "your",
}


def extract_query_terms(query: str, *, max_terms: int = 8) -> list[str]:
    tokens = re.findall(r"\w+", query.lower())
    terms = [token for token in tokens if token not in QUERY_STOPWORDS and len(token) > 2]
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        deduped.append(term)
    return deduped[:max_terms]
