"""
STAT router — classify query as STAT (numbers/SQL), DOC (text), or HYBRID.

Used to decide whether to run the STAT path (schema + examples from Qdrant → SQL → execute)
or the normal RAG path (retrieve chunks → LLM answer). See docs/GOLDEN_INTERACTION_FLOW.md.
"""

from typing import Literal

# Keywords that suggest the user wants numbers/aggregates per entity or time
STAT_KEYWORDS_RO = (
    "rata",
    "ocupare",
    "secție",
    "secți",
    "sectie",
    "paturi",
    "procent",
    "număr",
    "total",
    "pe secție",
    "per sectie",
    "pe fiecare",
    "în data de",
    "data de",
    "la data",
    "aggregat",
    "statistic",
    "kpi",
    "indicator",
    "top 5",
    "top 10",
    "media",
    "diferență",
    "diferenta",
    "câte",
    "cate",
    "câți",
    "cati",
    "grad de ocupare",
    "paturi reale",
    "paturi libere",
    "structură",
    "structura",
)
STAT_KEYWORDS_EN = (
    "rate",
    "occupancy",
    "per section",
    "per department",
    "by section",
    "on date",
    "as of",
    "aggregate",
    "statistic",
    "kpi",
    "metric",
    "top 5",
    "top 10",
    "average",
    "difference",
    "how many",
    "count",
)


def route(query: str) -> Literal["STAT", "DOC", "HYBRID"]:
    """
    Classify query into STAT (numbers/SQL), DOC (text-only), or HYBRID.

    Returns:
        "STAT"  — use STAT path (schema + examples → SQL → execute).
        "DOC"   — use normal RAG (chunks → LLM).
        "HYBRID" — use STAT path, optionally augmented with DOC context (treated as STAT for now).
    """
    if not query or not query.strip():
        return "DOC"
    q = query.strip().lower()
    # Normalize Romanian diacritics for matching
    q_norm = q.replace("ă", "a").replace("â", "a").replace("î", "i").replace("ș", "s").replace("ț", "t")
    for kw in STAT_KEYWORDS_RO:
        kw_norm = kw.replace("ă", "a").replace("â", "a").replace("î", "i").replace("ș", "s").replace("ț", "t")
        if kw_norm in q_norm or kw in q:
            return "STAT"
    for kw in STAT_KEYWORDS_EN:
        if kw in q:
            return "STAT"
    return "DOC"


def is_stat_query(query: str) -> bool:
    """True if the query should use the STAT path."""
    return route(query) in ("STAT", "HYBRID")
