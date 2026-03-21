"""
Core/constants.py - Shared constants and utilities used across RAG engine modules.

Centralizes stop words, sentence splitting, and token estimation to eliminate
duplication across contextual_compressor, reranker, evaluation, and confidence_scorer.

Ported from ZEN_RAG.
"""

import re
from typing import List

# Shared stop words set — used by reranker, compressor, evaluator, confidence scorer
STOP_WORDS: frozenset = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "of",
        "to",
        "in",
        "for",
        "on",
        "at",
        "by",
        "with",
        "from",
        "as",
        "this",
        "that",
        "these",
        "those",
        "it",
        "what",
        "when",
        "where",
        "who",
        "why",
        "how",
        "which",
        "and",
        "or",
        "but",
        "not",
        "no",
    }
)

# Pre-compiled sentence split pattern (lookbehind to preserve punctuation)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Pre-compiled word extraction pattern
_WORD_RE = re.compile(r"\b\w+\b")


def split_sentences(text: str) -> List[str]:
    """Split text into sentences, preserving ending punctuation."""
    sentences = _SENTENCE_SPLIT_RE.split(text)
    return [s.strip() for s in sentences if s.strip()]


def extract_key_words(text: str, min_length: int = 2) -> List[str]:
    """Extract key words from text, excluding stop words and short words."""
    words = _WORD_RE.findall(text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > min_length]


def estimate_tokens(text: str) -> int:
    """Rough token count estimate (~4 chars per token)."""
    return max(1, len(text) // 4)
