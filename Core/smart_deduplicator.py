"""
Core/smart_deduplicator.py — 4-Tier Smart Deduplication Engine

Eliminates duplicates at multiple levels during RAG ingestion:
  Tier 1: Exact hash duplicates (SHA256) — O(1)
  Tier 2: Boilerplate detection (nav, footer, cookie, copyright) — regex
  Tier 3: Structural/navigation content — link-density + pattern matching
  Tier 4: Semantic near-duplicates (cosine similarity) — embedding comparison
  Tier 5: Cross-page repeated blocks (MinHash fingerprint) — fuzzy structural

Also detects conflicting information between near-duplicates and queues them
for Human-in-the-Loop resolution instead of silently discarding.

Usage:
    dedup = SmartDeduplicator(model=sentence_transformer_model)
    for chunk_text, chunk_embedding in chunks:
        skip, reason, conflict = dedup.should_skip_chunk(chunk_text, chunk_embedding)
        if conflict:
            conflict_queue.append(conflict)
        elif not skip:
            add_to_index(chunk_text, chunk_embedding)
"""

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    np = None


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class DeduplicationResult:
    """Result of dedup check for one chunk."""

    should_skip: bool
    reason: str  # "kept", "exact_duplicate", "boilerplate", "structural", "semantic_duplicate", "repetitive"
    conflict: Optional["ConflictCandidate"] = None


@dataclass
class ConflictCandidate:
    """Two chunks that are semantically similar but textually different —
    flagged for Human-in-the-Loop review."""

    new_text: str
    existing_text: str
    similarity: float
    new_source: Optional[str] = None
    existing_source: Optional[str] = None
    new_title: Optional[str] = None
    existing_title: Optional[str] = None
    detected_at: float = field(default_factory=time.time)


@dataclass
class DeduplicationStats:
    """Running statistics for a dedup session."""

    total_processed: int = 0
    kept: int = 0
    exact_duplicates: int = 0
    boilerplate: int = 0
    structural: int = 0
    semantic_duplicates: int = 0
    repetitive: int = 0
    conflicts_detected: int = 0
    processing_time_s: float = 0.0

    def to_dict(self) -> Dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @property
    def skip_rate(self) -> float:
        if self.total_processed == 0:
            return 0.0
        return 1.0 - (self.kept / self.total_processed)


# ─────────────────────────────────────────────────────────────────────────────
# SmartDeduplicator
# ─────────────────────────────────────────────────────────────────────────────


class SmartDeduplicator:
    """
    Production-grade 4-tier deduplication engine for RAG ingestion.

    Designed for website crawling where 40-60% of content is navigation noise,
    repeated boilerplate, or semantically duplicate paragraphs.
    """

    # ── Boilerplate patterns (footer, cookie, copyright, social, etc.) ────
    BOILERPLATE_PATTERNS = [
        r"©\s*\d{4}",
        r"all\s+rights\s+reserved",
        r"copyright\s+\d{4}",
        r"privacy\s+policy",
        r"terms\s+of\s+(service|use)",
        r"terms\s+and\s+conditions",
        r"cookie\s+(policy|consent|notice|settings)",
        r"follow\s+us\s+on",
        r"subscribe\s+to\s+(our|the)",
        r"sign\s+up\s+for\s+(our|the|a)",
        r"newsletter",
        r"powered\s+by\s+\w+",
        r"built\s+with\s+\w+",
        r"<<?\s*back\s+to",
        r"last\s+(updated|modified|changed)\s*:?",
        r"posted\s+on\s+\w+",
        r"\bdisclaimer\b",
        r"\blegal\s+notice\b",
        r"share\s+(this|on)",
        r"(facebook|twitter|linkedin|instagram|youtube)\s*(share|follow)?",
        r"accept\s+(all\s+)?cookies?",
        r"we\s+use\s+cookies",
        r"manage\s+(cookie|consent)",
        r"read\s+more\s*\.{0,3}$",
        r"click\s+here\s+to",
        r"loading\s*\.{2,}",
        r"please\s+wait",
        r"skip\s+to\s+(main\s+)?content",
        r"toggle\s+navigation",
        r"primary\s+menu",
        r"search\s+(this\s+)?site",
    ]

    # ── Navigation/structural patterns ────────────────────────────────────
    NAV_PATTERNS = [
        r"^\s*(home|about(\s+us)?|contact(\s+us)?|products|services|blog|faq|sitemap|login|register)\s*$",
        r"(main\s+)?menu",
        r"breadcrumb",
        r"sidebar",
        r"^\s*navigation\s*$",
        r"(previous|next)\s+(page|post|article)",
        r"page\s+\d+\s+of\s+\d+",
        r"^\s*\d+\s*$",  # Lone page numbers
    ]

    # Compile for speed
    _bp_compiled = [re.compile(p, re.IGNORECASE) for p in BOILERPLATE_PATTERNS]
    _nav_compiled = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in NAV_PATTERNS]

    def __init__(
        self,
        model=None,
        semantic_threshold: float = 0.90,
        conflict_threshold: float = 0.75,
        max_semantic_cache: int = 500,
    ):
        """
        Args:
            model: SentenceTransformer model for semantic comparison (optional).
            semantic_threshold: Cosine similarity above which chunks are near-duplicates.
            conflict_threshold: Similarity band [conflict_threshold, semantic_threshold)
                where chunks are similar but different enough to be potential conflicts.
            max_semantic_cache: Max cached embeddings for comparison (LRU-ish).
        """
        self.model = model
        self.semantic_threshold = semantic_threshold
        self.conflict_threshold = conflict_threshold
        self.max_semantic_cache = max_semantic_cache

        # ── Caches ────────────────────────────────────────────────────────
        self._hash_cache: Set[str] = set()
        # Each entry: (embedding_ndarray, text, source_url, title)
        self._semantic_cache: List[Tuple] = []
        # MinHash-style shingle fingerprints for cross-page block detection
        self._shingle_hashes: Set[str] = set()

        # ── Stats ─────────────────────────────────────────────────────────
        self.stats = DeduplicationStats()

    # =====================================================================
    # PUBLIC API
    # =====================================================================

    def should_skip_chunk(
        self,
        text: str,
        embedding=None,
        source_url: Optional[str] = None,
        title: Optional[str] = None,
    ) -> DeduplicationResult:
        """
        Decide whether a chunk should be added to the index or skipped.

        Returns:
            DeduplicationResult with skip decision, reason, and optional conflict.
        """
        t0 = time.time()
        self.stats.total_processed += 1

        # Tier 1 — Exact hash duplicate
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if text_hash in self._hash_cache:
            self.stats.exact_duplicates += 1
            self.stats.processing_time_s += time.time() - t0
            return DeduplicationResult(True, "exact_duplicate")

        # Tier 2 — Boilerplate
        if self._is_boilerplate(text):
            self.stats.boilerplate += 1
            self.stats.processing_time_s += time.time() - t0
            return DeduplicationResult(True, "boilerplate")

        # Tier 3 — Structural / navigation
        if self._is_structural(text):
            self.stats.structural += 1
            self.stats.processing_time_s += time.time() - t0
            return DeduplicationResult(True, "structural")

        # Tier 3b — Excessive word repetition
        if self._is_repetitive(text):
            self.stats.repetitive += 1
            self.stats.processing_time_s += time.time() - t0
            return DeduplicationResult(True, "repetitive")

        # Tier 4 — Semantic near-duplicate / conflict detection
        conflict = None
        if embedding is not None and np is not None:
            dup_or_conflict = self._check_semantic(text, embedding, source_url, title)
            if dup_or_conflict is True:
                self.stats.semantic_duplicates += 1
                self.stats.processing_time_s += time.time() - t0
                return DeduplicationResult(True, "semantic_duplicate")
            elif isinstance(dup_or_conflict, ConflictCandidate):
                conflict = dup_or_conflict
                self.stats.conflicts_detected += 1
                # Don't skip — keep the chunk, but flag the conflict

        # Tier 5 — Cross-page repeated shingle blocks
        if self._is_repeated_block(text):
            self.stats.boilerplate += 1
            self.stats.processing_time_s += time.time() - t0
            return DeduplicationResult(True, "boilerplate")

        # ── Not duplicate; cache it ───────────────────────────────────────
        self._hash_cache.add(text_hash)
        if embedding is not None and np is not None:
            self._semantic_cache.append((embedding, text, source_url, title))
            if len(self._semantic_cache) > self.max_semantic_cache:
                self._semantic_cache = self._semantic_cache[-self.max_semantic_cache :]

        self.stats.kept += 1
        self.stats.processing_time_s += time.time() - t0
        return DeduplicationResult(False, "kept", conflict=conflict)

    def clear(self):
        """Reset all caches and stats."""
        self._hash_cache.clear()
        self._semantic_cache.clear()
        self._shingle_hashes.clear()
        self.stats = DeduplicationStats()

    def get_stats(self) -> Dict:
        return self.stats.to_dict()

    # =====================================================================
    # TIER 2: BOILERPLATE DETECTION
    # =====================================================================

    def _is_boilerplate(self, text: str) -> bool:
        """Check if chunk is likely boilerplate (footer, cookie, copyright)."""
        text_stripped = text.strip()
        text_lower = text_stripped.lower()

        # Very short chunks that match boilerplate → definitely skip
        if len(text_stripped) < 200:
            for pat in self._bp_compiled:
                if pat.search(text_lower):
                    return True

        # Longer chunks: only skip if >60% of lines are boilerplate
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) >= 3:
            bp_count = sum(1 for line in lines if any(pat.search(line.lower()) for pat in self._bp_compiled))
            if bp_count / len(lines) > 0.6:
                return True

        return False

    # =====================================================================
    # TIER 3: STRUCTURAL / NAVIGATION
    # =====================================================================

    def _is_structural(self, text: str) -> bool:
        """Check if chunk is navigation, menu, breadcrumb, etc."""
        text_lower = text.lower()

        # Direct pattern match
        for pat in self._nav_compiled:
            if pat.search(text_lower):
                return True

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return False

        # Link-heavy content (>50% lines look like links)
        link_lines = sum(1 for line in lines if re.search(r"\[.+?\]\(.+?\)|https?://|www\.", line))
        if len(lines) >= 3 and link_lines / len(lines) > 0.5:
            return True

        # Very short lines that look like menu items
        short_lines = sum(1 for line in lines if len(line) < 30)
        if len(lines) >= 5 and short_lines / len(lines) > 0.7:
            # Check if they look like a menu (mostly capitalized words)
            cap_lines = sum(1 for line in lines if line[0].isupper() and len(line.split()) <= 4)
            if cap_lines / len(lines) > 0.6:
                return True

        return False

    def _is_repetitive(self, text: str) -> bool:
        """Chunk has excessive word repetition → likely auto-generated filler."""
        words = text.lower().split()
        if len(words) < 10:
            return False
        unique_ratio = len(set(words)) / len(words)
        return unique_ratio < 0.30

    # =====================================================================
    # TIER 4: SEMANTIC NEAR-DUPLICATE / CONFLICT
    # =====================================================================

    def _check_semantic(self, text: str, embedding, source_url: Optional[str], title: Optional[str]):
        """
        Compare against cached embeddings.

        Returns:
            True    — semantic duplicate (skip)
            ConflictCandidate — similar but different (keep, flag conflict)
            None    — no match
        """
        if not self._semantic_cache:
            return None

        emb = np.asarray(embedding)

        # Compare to recent cache entries (cap at last 200 for speed)
        search_window = self._semantic_cache[-200:]

        best_sim = 0.0
        best_entry = None

        for cached_emb, cached_text, cached_url, cached_title in search_window:
            sim = float(np.dot(emb, np.asarray(cached_emb)))
            if sim > best_sim:
                best_sim = sim
                best_entry = (cached_text, cached_url, cached_title)

        if best_sim >= self.semantic_threshold:
            return True  # Near-duplicate → skip

        if best_sim >= self.conflict_threshold and best_entry is not None:
            # In the "conflict zone" — similar topic, different content
            existing_text, existing_url, existing_title = best_entry
            # Only flag as conflict if the texts are meaningfully different
            if self._texts_conflict(text, existing_text):
                return ConflictCandidate(
                    new_text=text,
                    existing_text=existing_text,
                    similarity=best_sim,
                    new_source=source_url,
                    existing_source=existing_url,
                    new_title=title,
                    existing_title=existing_title,
                )

        return None

    def _texts_conflict(self, text_a: str, text_b: str) -> bool:
        """
        Check if two semantically similar texts actually contain conflicting
        information (not just paraphrases of the same facts).
        """
        a_lower = text_a.lower()
        b_lower = text_b.lower()

        # If one is a substring of the other, it's a paraphrase, not a conflict
        if a_lower in b_lower or b_lower in a_lower:
            return False

        # Extract key assertions (numbers, dates, proper nouns)
        a_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", text_a))
        b_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", text_b))

        # If both mention numbers and they differ → potential conflict
        if a_nums and b_nums and a_nums != b_nums:
            # Check if the different numbers are in similar contexts
            a_nums & b_nums
            diff_a = a_nums - b_nums
            diff_b = b_nums - a_nums
            if diff_a and diff_b:
                return True

        # Check for contradictory language patterns
        negation_pairs = [
            (r"\bis\b", r"\bis\s+not\b"),
            (r"\bwas\b", r"\bwas\s+not\b"),
            (r"\bcan\b", r"\bcannot\b|\bcan\s*'?\s*t\b"),
            (r"\bwill\b", r"\bwill\s+not\b|\bwon\s*'?\s*t\b"),
            (r"\btrue\b", r"\bfalse\b"),
            (r"\bcorrect\b", r"\bincorrect\b"),
            (r"\byes\b", r"\bno\b"),
        ]

        for pos_pat, neg_pat in negation_pairs:
            a_has_pos = bool(re.search(pos_pat, a_lower))
            b_has_neg = bool(re.search(neg_pat, b_lower))
            a_has_neg = bool(re.search(neg_pat, a_lower))
            b_has_pos = bool(re.search(pos_pat, b_lower))
            if (a_has_pos and b_has_neg) or (a_has_neg and b_has_pos):
                return True

        # Check Jaccard distance of significant words (content words)
        stopwords = {
            "the",
            "a",
            "an",
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
            "must",
            "shall",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "and",
            "or",
            "but",
            "if",
            "then",
            "than",
            "that",
            "this",
            "it",
            "its",
            "not",
            "no",
            "so",
            "very",
            "also",
            "just",
        }
        a_words = set(a_lower.split()) - stopwords
        b_words = set(b_lower.split()) - stopwords

        if not a_words or not b_words:
            return False

        jaccard = len(a_words & b_words) / len(a_words | b_words)
        # High topic overlap but low exact word overlap → possible conflict
        if 0.2 < jaccard < 0.6:
            return True

        return False

    # =====================================================================
    # TIER 5: CROSS-PAGE REPEATED BLOCKS (SHINGLE FINGERPRINT)
    # =====================================================================

    def _shingle_hash(self, text: str, shingle_size: int = 3) -> str:
        """Create a fingerprint from word-level shingles."""
        words = text.lower().split()
        if len(words) < shingle_size:
            return hashlib.md5(text.lower().encode()).hexdigest()

        shingles = []
        for i in range(len(words) - shingle_size + 1):
            shingle = " ".join(words[i : i + shingle_size])
            shingles.append(shingle)

        # Sort shingles and hash the combined fingerprint
        combined = "|".join(sorted(shingles[:20]))  # First 20 for efficiency
        return hashlib.md5(combined.encode()).hexdigest()

    def _is_repeated_block(self, text: str) -> bool:
        """
        Detect cross-page repeated blocks using shingle fingerprints.
        E.g., "Related Articles" sections that appear on every blog post.
        """
        if len(text.strip()) < 80:
            return False

        fp = self._shingle_hash(text)
        if fp in self._shingle_hashes:
            return True

        self._shingle_hashes.add(fp)
        return False
