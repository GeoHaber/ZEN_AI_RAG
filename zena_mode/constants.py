# -*- coding: utf-8 -*-
"""
zena_mode/constants.py — Shared constants and utilities
========================================================

Centralises stop words, sentence splitting, and token estimation
used across query_processor, contextual_compressor, and evaluation.
"""
from __future__ import annotations

import re
from typing import List

# Shared stop words set
STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "of", "to", "in", "for", "on", "at",
    "by", "with", "from", "as", "this", "that", "these", "those", "it",
    "what", "when", "where", "who", "why", "how", "which",
    "and", "or", "but", "not", "no",
})

# Pre-compiled patterns
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"\b\w+\b")


def split_sentences(text: str) -> List[str]:
    """Split text into sentences, preserving ending punctuation."""
    sentences = _SENTENCE_SPLIT_RE.split(text)
    return [s.strip() for s in sentences if s.strip()]


def extract_key_words(text: str, min_length: int = 2) -> set[str]:
    """Extract key words from text, excluding stop words and short words.

    Returns a *set* so callers can use set-intersection (``&``) directly.
    """
    words = _WORD_RE.findall(text.lower())
    return {w for w in words if w not in STOP_WORDS and len(w) > min_length}


def estimate_tokens(text: str) -> int:
    """Rough token count estimate (~4 chars per token)."""
    return max(1, len(text) // 4)
