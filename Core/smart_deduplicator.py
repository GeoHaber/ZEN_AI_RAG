"""
Core/smart_deduplicator.py — 5-Tier Smart Deduplication for RAG Pipeline.

Tier 1: Exact hash dedup (SHA-256)
Tier 2: Boilerplate removal (headers, footers, nav)
Tier 3: Structural dedup (normalized text comparison)
Tier 4: Semantic dedup (embedding cosine similarity)
Tier 5: Shingle fingerprinting (near-duplicate detection)

Ported from ZEN_RAG.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationStats:
    """Statistics from a dedup pass."""

    total_input: int = 0
    exact_dupes_removed: int = 0
    boilerplate_removed: int = 0
    structural_dupes_removed: int = 0
    semantic_dupes_removed: int = 0
    shingle_dupes_removed: int = 0
    total_output: int = 0
    conflicts_detected: int = 0

    @property
    def total_removed(self) -> int:
        return (
            self.exact_dupes_removed
            + self.boilerplate_removed
            + self.structural_dupes_removed
            + self.semantic_dupes_removed
            + self.shingle_dupes_removed
        )


@dataclass
class ConflictCandidate:
    """Two chunks that say different things about the same topic."""

    chunk_a: Dict[str, Any]
    chunk_b: Dict[str, Any]
    similarity: float
    conflict_type: str = "potential_contradiction"


@dataclass
class DeduplicationResult:
    """Full result of deduplication pass."""

    unique_chunks: List[Dict[str, Any]]
    stats: DeduplicationStats
    conflicts: List[ConflictCandidate] = field(default_factory=list)


# ─── Boilerplate Patterns ──────────────────────────────────────────────────

_BOILERPLATE_PATTERNS = [
    re.compile(r"^(cookie|privacy)\s*(policy|notice|settings)", re.IGNORECASE),
    re.compile(r"^(terms\s+(of\s+)?(use|service)|disclaimer)", re.IGNORECASE),
    re.compile(r"^(copyright|©|all\s+rights?\s+reserved)", re.IGNORECASE),
    re.compile(r"^(subscribe|sign\s+up|newsletter|follow\s+us)", re.IGNORECASE),
    re.compile(r"^(skip\s+to\s+(content|main|navigation))", re.IGNORECASE),
    re.compile(r"^(home|about|contact|faq|help|sitemap)\s*[|>»]", re.IGNORECASE),
    re.compile(r"^(loading|please\s+wait|javascript\s+(is\s+)?required)", re.IGNORECASE),
    re.compile(r"^(share|tweet|pin\s+it|email\s+this)", re.IGNORECASE),
    re.compile(r"^(accept|reject|manage)\s*(all\s+)?(cookies?)", re.IGNORECASE),
    re.compile(r"^(advertisement|sponsored|promoted)", re.IGNORECASE),
    re.compile(r"^(previous|next)\s*(article|post|page)", re.IGNORECASE),
    re.compile(r"^(read\s+more|continue\s+reading|see\s+also)", re.IGNORECASE),
]


class SmartDeduplicator:
    """5-tier deduplication engine for RAG chunks.

    Thread-safe. Uses sentence-transformers for semantic dedup.

    Usage:
        dedup = SmartDeduplicator()
        result = dedup.deduplicate(chunks)
        clean_chunks = result.unique_chunks
    """

    def __init__(
        self,
        semantic_threshold: float = 0.92,
        shingle_threshold: float = 0.80,
        min_chunk_length: int = 30,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        self.semantic_threshold = semantic_threshold
        self.shingle_threshold = shingle_threshold
        self.min_chunk_length = min_chunk_length
        self._model = None
        self._model_name = model_name

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
            except Exception as e:
                logger.warning(f"[Dedup] Could not load model: {e}")
        return self._model

    def deduplicate(
        self,
        chunks: List[Dict[str, Any]],
        detect_conflicts: bool = True,
    ) -> DeduplicationResult:
        """Run all 5 dedup tiers sequentially."""
        stats = DeduplicationStats(total_input=len(chunks))
        conflicts: List[ConflictCandidate] = []

        if not chunks:
            stats.total_output = 0
            return DeduplicationResult([], stats)

        # Tier 1: Exact hash
        current, removed = self._tier1_exact_hash(chunks)
        stats.exact_dupes_removed = removed

        # Tier 2: Boilerplate
        current, removed = self._tier2_boilerplate(current)
        stats.boilerplate_removed = removed

        # Tier 3: Structural
        current, removed = self._tier3_structural(current)
        stats.structural_dupes_removed = removed

        # Tier 4: Semantic
        current, removed, tier4_conflicts = self._tier4_semantic(current, detect_conflicts)
        stats.semantic_dupes_removed = removed
        conflicts.extend(tier4_conflicts)

        # Tier 5: Shingle
        current, removed = self._tier5_shingle(current)
        stats.shingle_dupes_removed = removed

        stats.total_output = len(current)
        stats.conflicts_detected = len(conflicts)

        logger.info(
            f"[Dedup] {stats.total_input}→{stats.total_output} chunks "
            f"(removed {stats.total_removed}: "
            f"hash={stats.exact_dupes_removed}, boiler={stats.boilerplate_removed}, "
            f"struct={stats.structural_dupes_removed}, sem={stats.semantic_dupes_removed}, "
            f"shingle={stats.shingle_dupes_removed})"
        )

        return DeduplicationResult(current, stats, conflicts)

    # ─── Tier 1: Exact Hash ────────────────────────────────────────────────

    def _tier1_exact_hash(self, chunks: List[Dict]) -> Tuple[List[Dict], int]:
        """Remove exact duplicate texts using SHA-256."""
        seen: Set[str] = set()
        unique = []
        for c in chunks:
            text = c.get("text", "").strip()
            h = hashlib.sha256(text.encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                unique.append(c)
        return unique, len(chunks) - len(unique)

    # ─── Tier 2: Boilerplate ───────────────────────────────────────────────

    def _tier2_boilerplate(self, chunks: List[Dict]) -> Tuple[List[Dict], int]:
        """Remove boilerplate chunks (nav, cookies, footers)."""
        clean = []
        for c in chunks:
            text = c.get("text", "").strip()
            if len(text) < self.min_chunk_length:
                continue
            if any(p.search(text) for p in _BOILERPLATE_PATTERNS):
                continue
            clean.append(c)
        return clean, len(chunks) - len(clean)

    # ─── Tier 3: Structural ────────────────────────────────────────────────

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for structural comparison."""
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s]", "", text)
        return text

    def _tier3_structural(self, chunks: List[Dict]) -> Tuple[List[Dict], int]:
        """Remove structurally identical chunks (after normalization)."""
        seen: Set[str] = set()
        unique = []
        for c in chunks:
            norm = self._normalize_text(c.get("text", ""))
            if norm not in seen:
                seen.add(norm)
                unique.append(c)
        return unique, len(chunks) - len(unique)

    # ─── Tier 4: Semantic ──────────────────────────────────────────────────

    def _tier4_semantic(
        self,
        chunks: List[Dict],
        detect_conflicts: bool = True,
    ) -> Tuple[List[Dict], int, List[ConflictCandidate]]:
        """Remove semantically redundant chunks using embeddings."""
        conflicts: List[ConflictCandidate] = []

        if not self.model or len(chunks) < 2:
            return chunks, 0, conflicts

        try:
            import numpy as np

            texts = [c.get("text", "") for c in chunks]
            embeddings = self.model.encode(texts, normalize_embeddings=True)

            keep = [True] * len(chunks)
            for i in range(len(chunks)):
                if not keep[i]:
                    continue
                for j in range(i + 1, len(chunks)):
                    if not keep[j]:
                        continue
                    sim = float(np.dot(embeddings[i], embeddings[j]))
                    if sim >= self.semantic_threshold:
                        # Keep the longer chunk
                        if len(texts[i]) >= len(texts[j]):
                            keep[j] = False
                        else:
                            keep[i] = False
                            break
                    elif detect_conflicts and 0.70 <= sim < self.semantic_threshold:
                        # High similarity but not duplicate — possible conflict
                        if self._texts_conflict(texts[i], texts[j]):
                            conflicts.append(ConflictCandidate(
                                chunk_a=chunks[i],
                                chunk_b=chunks[j],
                                similarity=sim,
                            ))

            unique = [c for c, k in zip(chunks, keep) if k]
            return unique, len(chunks) - len(unique), conflicts

        except Exception as e:
            logger.warning(f"[Dedup] Tier 4 semantic dedup error: {e}")
            return chunks, 0, conflicts

    @staticmethod
    def _texts_conflict(text_a: str, text_b: str) -> bool:
        """Heuristic: do two similar texts actually conflict?"""
        a_lower = text_a.lower()
        b_lower = text_b.lower()

        # Check for negation patterns
        negation_patterns = [
            (r"\bnot\b", r"\bis\b"),
            (r"\bnever\b", r"\balways\b"),
            (r"\bno\b", r"\byes\b"),
            (r"\bdecreased?\b", r"\bincreased?\b"),
            (r"\blower\b", r"\bhigher\b"),
        ]
        for pat_a, pat_b in negation_patterns:
            if (re.search(pat_a, a_lower) and re.search(pat_b, b_lower)) or \
               (re.search(pat_b, a_lower) and re.search(pat_a, b_lower)):
                return True

        # Check Jaccard word overlap — very similar words but different content
        words_a = set(re.findall(r"\w+", a_lower))
        words_b = set(re.findall(r"\w+", b_lower))
        if words_a and words_b:
            jaccard = len(words_a & words_b) / len(words_a | words_b)
            if jaccard > 0.5:
                # High word overlap → check for number discrepancies
                nums_a = set(re.findall(r"\b\d+\.?\d*\b", text_a))
                nums_b = set(re.findall(r"\b\d+\.?\d*\b", text_b))
                if nums_a and nums_b and nums_a != nums_b:
                    return True

        return False

    # ─── Tier 5: Shingle Fingerprinting ────────────────────────────────────

    def _tier5_shingle(self, chunks: List[Dict]) -> Tuple[List[Dict], int]:
        """Remove near-duplicates via character n-gram (shingle) fingerprinting."""
        if len(chunks) < 2:
            return chunks, 0

        # Build fingerprints
        fingerprints = []
        for c in chunks:
            text = c.get("text", "")
            fp = self._shingle_hash(text)
            fingerprints.append(fp)

        keep = [True] * len(chunks)
        for i in range(len(chunks)):
            if not keep[i]:
                continue
            for j in range(i + 1, len(chunks)):
                if not keep[j]:
                    continue
                sim = self._jaccard_similarity(fingerprints[i], fingerprints[j])
                if sim >= self.shingle_threshold:
                    # Keep the longer chunk
                    if len(chunks[i].get("text", "")) >= len(chunks[j].get("text", "")):
                        keep[j] = False
                    else:
                        keep[i] = False
                        break

        unique = [c for c, k in zip(chunks, keep) if k]
        return unique, len(chunks) - len(unique)

    @staticmethod
    def _shingle_hash(text: str, n: int = 5) -> Set[int]:
        """Create a set of character n-gram hashes."""
        text = re.sub(r"\s+", " ", text.lower().strip())
        if len(text) < n:
            return {hash(text)}
        return {hash(text[i:i + n]) for i in range(len(text) - n + 1)}

    @staticmethod
    def _jaccard_similarity(set_a: Set, set_b: Set) -> float:
        """Jaccard similarity between two sets."""
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)
