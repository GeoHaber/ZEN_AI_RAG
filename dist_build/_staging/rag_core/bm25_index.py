"""
rag_core.bm25_index — BM25 Keyword Search Index
==================================================

Wraps rank_bm25 with code-aware tokenisation and graceful fallback.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-zA-Z_]\w*")


def tokenize(text: str, *, code_aware: bool = True) -> List[str]:
    """Tokenise text for BM25.

    When *code_aware* is True, splits camelCase and snake_case into sub-tokens
    so ``parseJsonConfig`` produces ``[parse, json, config, parsejsonconfig]``.
    """
    tokens: List[str] = []
    # Extract words from the ORIGINAL case, then lowercase parts
    for word in _TOKEN_RE.findall(text):
        lower_word = word.lower()
        if code_aware:
            # Split camelCase / PascalCase on case boundaries
            parts = [p.lower() for p in re.findall(r"[a-z]+|[A-Z][a-z]*|[A-Z]+(?=[A-Z]|$)", word)]
            tokens.extend(parts)
        tokens.append(lower_word)
    return [t for t in tokens if len(t) > 1]


class BM25Index:
    """
    BM25 keyword search with graceful fallback.

    Uses ``rank_bm25.BM25Okapi`` when available, otherwise falls back
    to simple token overlap scoring.
    """

    def __init__(self, code_aware: bool = True):
        self.code_aware = code_aware
        self._bm25 = None
        self._corpus_tokens: List[List[str]] = []
        self._has_rank_bm25 = False

    @property
    def indexed(self) -> bool:
        return len(self._corpus_tokens) > 0

    @property
    def doc_count(self) -> int:
        return len(self._corpus_tokens)

    def build(self, documents: List[str]) -> int:
        """Build the BM25 index from a list of document texts.

        Returns the number of documents indexed.
        """
        self._corpus_tokens = [tokenize(doc, code_aware=self.code_aware) for doc in documents]

        # Guard: empty corpus or all-empty tokens → nothing to index
        corpus_has_tokens = any(len(t) > 0 for t in self._corpus_tokens)
        if not self._corpus_tokens or not corpus_has_tokens:
            self._bm25 = None
            self._has_rank_bm25 = False
            return len(self._corpus_tokens)

        try:
            from rank_bm25 import BM25Okapi

            self._bm25 = BM25Okapi(self._corpus_tokens)
            self._has_rank_bm25 = True
        except ImportError:
            logger.info("rank_bm25 not installed — using token overlap fallback")
            self._bm25 = None
            self._has_rank_bm25 = False

        return len(self._corpus_tokens)

    def search(self, query: str, k: int = 50) -> Dict[int, float]:
        """Search the index and return {doc_index: score} dict.

        Scores are raw BM25 scores (not normalised to 0-1).
        """
        if not self._corpus_tokens:
            return {}

        q_tokens = tokenize(query, code_aware=self.code_aware)

        if self._has_rank_bm25 and self._bm25 is not None:
            raw = self._bm25.get_scores(q_tokens)
            scored = [(i, float(s)) for i, s in enumerate(raw) if s > 0]
            scored.sort(key=lambda x: x[1], reverse=True)
            return {i: s for i, s in scored[:k]}

        # Fallback: simple token overlap
        q_set = set(q_tokens)
        scores: Dict[int, float] = {}
        for i, doc_tokens in enumerate(self._corpus_tokens):
            overlap = len(q_set & set(doc_tokens))
            if overlap > 0:
                scores[i] = overlap / max(len(q_set), 1)

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_scores[:k])
