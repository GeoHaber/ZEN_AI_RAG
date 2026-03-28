"""
Core/zero_waste_cache.py — Zero-Waste Two-Tier Validation-Aware Cache

Inspired by: "Zero-Waste Agentic RAG: Designing Caching Architectures to
Minimize Latency and LLM Costs at Scale" (Partha Sarkar, TDS 2026)

Architecture:
  ┌────────────────────────────────────────────────────────┐
  │                   User Query                           │
  │                      │                                 │
  │          ┌───── Temporal Check ─────┐                  │
  │          │ "latest"/"current"?      │                  │
  │          │ YES → BYPASS all cache   │                  │
  │          └──────────┬───────────────┘                  │
  │                     │ NO                               │
  │          ┌──── Tier 1: Answer Cache ────┐              │
  │          │ cosine ≥ 0.95 against query  │              │
  │          │ + Validate fingerprint       │              │
  │          │ HIT → return cached answer   │              │
  │          └──────────┬───────────────────┘              │
  │                     │ MISS                             │
  │          ┌──── Tier 2: Context Cache ───┐              │
  │          │ cosine ≥ 0.70 against topic  │              │
  │          │ + Sufficiency check          │              │
  │          │ HIT → return cached CHUNKS   │              │
  │          │   (skip Qdrant, re-run LLM)  │              │
  │          └──────────┬───────────────────┘              │
  │                     │ MISS                             │
  │          ┌──── Full Retrieval ──────────┐              │
  │          │ Qdrant + BM25 + Rerank       │              │
  │          │ Store in both tiers          │              │
  │          └──────────────────────────────┘              │
  └────────────────────────────────────────────────────────┘

Staleness Prevention:
  - Fingerprint validation: SHA-256 of source chunk texts
  - Collection version tracking: bump on every write/delete
  - TTL expiry: configurable per tier
  - Temporal bypass: freshness-oriented queries skip cache

Usage:
    cache = ZeroWasteCache(model, max_entries=1000)

    # Check Tier 1 (answer-level)
    result = cache.get_answer(query)
    if result:
        return result  # instant, zero LLM cost

    # Check Tier 2 (context-level)
    context = cache.get_context(query)
    if context:
        answer = llm.generate(query, context)  # fresh LLM, cached context
        cache.set_answer(query, answer, context)
        return answer

    # Full retrieval
    context = qdrant.search(query)
    answer = llm.generate(query, context)
    cache.set_answer(query, answer, context)
    cache.set_context(query, context)
    return answer
"""

import hashlib
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ─── Configuration ─────────────────────────────────────────────────────────


class CacheValidationStrategy(str, Enum):
    """How to validate a cache entry before serving."""

    FINGERPRINT = "fingerprint"  # SHA-256 hash comparison
    TEMPORAL = "temporal"  # Always bypass (freshness query)
    VERSION = "version"  # Collection version check
    STATIC = "static"  # TTL-only, no extra validation


# Temporal/freshness keywords that force cache bypass
TEMPORAL_KEYWORDS = frozenset(
    {
        "latest",
        "newest",
        "most recent",
        "current",
        "today",
        "right now",
        "updated",
        "fresh",
        "new",
        "real-time",
        "just added",
        "last",
        "cele mai recente",
        "actualizat",
        "ultimele",
        "nou",
        "azi",  # Romanian equivalents
    }
)

# Pre-compiled pattern for fast temporal detection
_TEMPORAL_PATTERN = re.compile(
    r"\b(?:latest|newest|most\s+recent|current(?:ly)?|today|right\s+now|"
    r"updated|fresh|real[\s-]?time|just\s+added|"
    r"cele\s+mai\s+recente|actualizat|ultimele|nou[aă]?|azi)\b",
    re.IGNORECASE,
)


# ─── Data Structures ──────────────────────────────────────────────────────


@dataclass
class CacheFingerprint:
    """SHA-256 fingerprint of source chunks for staleness detection.

    Stores source URLs and Qdrant point IDs so validate_fn can do
    *surgical* Qdrant queries instead of full-collection scans
    (Article Scenario 4-6).
    """

    chunk_hashes: Tuple[str, ...]  # Ordered hashes of chunk texts
    combined_hash: str  # Single hash of all chunks combined
    collection_version: int  # Qdrant collection version when cached
    source_urls: Tuple[str, ...] = ()  # URLs of source documents (for surgical invalidation)
    source_point_ids: Tuple[str, ...] = ()  # Qdrant point IDs (for targeted re-fetch)
    created_at: float = field(default_factory=time.time)

    @classmethod
    def from_chunks(cls, chunks: List[Dict], collection_version: int = 0) -> "CacheFingerprint":
        """Create fingerprint from a list of chunk dicts.

        Extracts source URLs and point IDs when available so that
        the validate_fn callback can surgically query Qdrant for
        only the affected documents.
        """
        texts = [c.get("text", "") for c in chunks]
        individual = tuple(hashlib.sha256(t.encode("utf-8")).hexdigest()[:16] for t in texts)
        combined = hashlib.sha256("|".join(texts).encode("utf-8")).hexdigest()[:24]
        # Extract unique source URLs (deduplicated, order-preserving)
        seen_urls: set = set()
        urls: list = []
        for c in chunks:
            u = c.get("url") or ""
            if u and u not in seen_urls:
                seen_urls.add(u)
                urls.append(u)
        # Extract point IDs if stored by Qdrant
        point_ids = tuple(str(c["qdrant_id"]) for c in chunks if c.get("qdrant_id"))
        return cls(
            chunk_hashes=individual,
            combined_hash=combined,
            collection_version=collection_version,
            source_urls=tuple(urls),
            source_point_ids=point_ids,
        )


@dataclass
class Tier1Entry:
    """Answer-level cache entry (Tier 1)."""

    query_norm: str  # Normalized original query
    query_embedding: Any  # numpy array
    results: List[Dict]  # Final search results (the "answer")
    fingerprint: CacheFingerprint  # Source validation
    validation_strategy: CacheValidationStrategy
    created_at: float = field(default_factory=time.time)
    hit_count: int = 0  # Popularity tracking


@dataclass
class Tier2Entry:
    """Context-level cache entry (Tier 2)."""

    query_norm: str  # Original query for this context
    query_embedding: Any  # numpy array
    topic_keywords: Set[str]  # Key nouns/entities for sufficiency
    context_chunks: List[Dict]  # Raw retrieved chunks
    fingerprint: CacheFingerprint  # Source validation
    created_at: float = field(default_factory=time.time)
    hit_count: int = 0


# ─── Main Cache ────────────────────────────────────────────────────────────


class ZeroWasteCache:
    """
    Two-tier validation-aware cache for RAG pipelines.

    Tier 1 (Answer Cache):  cosine ≥ 0.95  → return cached final results
    Tier 2 (Context Cache): cosine ≥ 0.70  → return cached chunks (skip Qdrant)

    Validation: fingerprinting, temporal bypass, collection versioning, TTL.
    """

    def __init__(
        self,
        model,
        max_entries: int = 1000,
        tier1_ttl: int = 3600,
        tier2_ttl: int = 7200,
        tier1_threshold: float = 0.95,
        tier2_threshold: float = 0.70,
    ):
        """
        Args:
            model: SentenceTransformer instance for embedding queries
            max_entries: Max entries per tier
            tier1_ttl: Seconds before Tier 1 entries expire (default: 1 hour)
            tier2_ttl: Seconds before Tier 2 entries expire (default: 2 hours)
            tier1_threshold: Cosine similarity threshold for answer-level cache
            tier2_threshold: Cosine similarity threshold for context-level cache
        """
        self.model = model
        self.max_entries = max_entries
        self.tier1_ttl = tier1_ttl
        self.tier2_ttl = tier2_ttl
        self.tier1_threshold = tier1_threshold
        self.tier2_threshold = tier2_threshold

        # ── Tier 1: Answer Cache ──
        self._exact_cache: Dict[str, Tier1Entry] = {}  # exact string → entry
        self._semantic_cache: List[Tier1Entry] = []  # list for cosine scan

        # ── Tier 2: Context Cache ──
        self._context_cache: List[Tier2Entry] = []  # list for topic scan

        # ── Collection version (bumped on every write/delete) ──
        self._collection_version: int = 0

        # ── Statistics ──
        self.stats = {
            "tier1_exact_hits": 0,
            "tier1_semantic_hits": 0,
            "tier1_misses": 0,
            "tier2_hits": 0,
            "tier2_partial_hits": 0,  # Hit but insufficient context
            "tier2_misses": 0,
            "temporal_bypasses": 0,
            "fingerprint_invalidations": 0,
            "version_invalidations": 0,
            "surgical_invalidations": 0,  # Entries evicted by invalidate_urls()
            "aggregate_queries": 0,  # Queries classified as VERSION strategy
            "total_queries": 0,
            "total_llm_savings": 0,  # Queries that avoided LLM entirely
            "total_retrieval_savings": 0,  # Queries that avoided Qdrant
        }

        self._lock = threading.Lock()

        # Lazy-loaded numpy
        self._np = None

    # ─── Adaptive TTL (Gap 6) ──────────────────────────────────────────────
    # High-hit entries get TTL boost: base + (hits * 120s), max 3x base.
    # This prevents evicting "hot" entries while keeping cold ones trimmed.

    def _effective_ttl(self, base_ttl: float, hit_count: int) -> float:
        """Return adaptive TTL: popular entries get up to 3× the base TTL."""
        boost = min(hit_count * 120, base_ttl * 2)  # max 3× base
        return base_ttl + boost

    # ─── Aggregate / Strategy Classification (Gap 3) ───────────────────────
    # Queries like "how many", "total", "average" operate on *all* chunks
    # in a collection, so a single-chunk fingerprint check is insufficient.
    # We tag them with VERSION strategy → invalidate whenever collection changes.

    _AGGREGATE_PATTERN = re.compile(
        r"\b(?:how\s+many|total|count|average|mean|sum|all|every|overview|"
        r"c[aâ]te|total[aă]?|media|sumar[aă]?|toate|fiecare)\b",
        re.IGNORECASE,
    )

    def classify_strategy(self, query: str) -> CacheValidationStrategy:
        """Classify the optimal validation strategy for a query.

        - TEMPORAL: freshness queries (bypass all cache)
        - VERSION: aggregate queries (invalidate on any collection change)
        - FINGERPRINT: specific queries (use chunk-level SHA-256)
        """
        if self.is_temporal_query(query):
            return CacheValidationStrategy.TEMPORAL
        if self._AGGREGATE_PATTERN.search(query):
            return CacheValidationStrategy.VERSION
        return CacheValidationStrategy.FINGERPRINT

    # ─── Surgical URL Invalidation (Gap 4) ─────────────────────────────────
    # Instead of clear() (nuclear), invalidate only entries whose source_urls
    # overlap with the deleted URL(s).  O(N) sweep over both tiers.

    def invalidate_urls(self, urls: Set[str]) -> int:
        """Surgically evict cache entries whose source docs overlap *urls*.

        Returns the number of evicted entries.
        """
        if not urls:
            return 0
        evicted = 0
        with self._lock:
            # --- Tier 1: exact cache ---
            stale_keys = [k for k, entry in self._exact_cache.items() if set(entry.fingerprint.source_urls) & urls]
            for k in stale_keys:
                del self._exact_cache[k]
            evicted += len(stale_keys)

            # --- Tier 1: semantic cache ---
            before = len(self._semantic_cache)
            self._semantic_cache = [e for e in self._semantic_cache if not (set(e.fingerprint.source_urls) & urls)]
            evicted += before - len(self._semantic_cache)

            # --- Tier 2: context cache ---
            before = len(self._context_cache)
            self._context_cache = [e for e in self._context_cache if not (set(e.fingerprint.source_urls) & urls)]
            evicted += before - len(self._context_cache)

            if evicted:
                logger.debug(f"[Cache] Surgical invalidation: {evicted} entries evicted for URLs {list(urls)[:3]}...")
        return evicted

    @property
    def np(self):
        if self._np is None:
            import numpy as np

            self._np = np
        return self._np

    # ─── Temporal Bypass ───────────────────────────────────────────────────

    def is_temporal_query(self, query: str) -> bool:
        """
        Detect if query asks for fresh/latest/current data.
        These queries ALWAYS bypass cache to prevent stale answers.

        Scenario 3 from the article: Agentic Cache Bypass
        """
        return bool(_TEMPORAL_PATTERN.search(query))

    # ─── Tier 1: Answer Cache ─────────────────────────────────────────────

    def get_answer(
        self,
        query: str,
        validate_fn: Optional[callable] = None,
    ) -> Optional[List[Dict]]:
        """
        Check Tier 1 (answer-level cache).

        Returns cached search results if query is ≥95% similar AND source
        fingerprints are still valid. Returns None on miss.

        Args:
            query: User query string
            validate_fn: Optional callable(fingerprint) -> bool to validate
                         source data hasn't changed. If None, skips validation.

        Returns:
            List of result dicts (same format as search() output) or None
        """
        with self._lock:
            self.stats["total_queries"] += 1
            now = time.time()

            # ── Temporal bypass ──
            if self.is_temporal_query(query):
                self.stats["temporal_bypasses"] += 1
                logger.debug(f"[Cache] Temporal bypass: '{query[:50]}...'")
                return None

            q_norm = query.strip().lower()

            # ── Exact match (fastest, O(1)) ──
            if q_norm in self._exact_cache:
                entry = self._exact_cache[q_norm]
                effective = self._effective_ttl(self.tier1_ttl, entry.hit_count)
                if now - entry.created_at > effective:
                    del self._exact_cache[q_norm]
                elif self._validate_entry(entry.fingerprint, validate_fn):
                    entry.hit_count += 1
                    self.stats["tier1_exact_hits"] += 1
                    self.stats["total_llm_savings"] += 1
                    logger.debug(f"[Cache] T1 Exact Hit: '{q_norm[:40]}...'")
                    return self._tag_results(entry.results, "tier1_exact")
                else:
                    # Fingerprint invalid → evict
                    del self._exact_cache[q_norm]
                    self.stats["fingerprint_invalidations"] += 1

            # ── Semantic match (cosine scan, O(N)) ──
            if self._semantic_cache:
                try:
                    q_vec = self.model.encode([query], normalize_embeddings=True)[0]

                    best_score = 0.0
                    best_idx = -1

                    for i, entry in enumerate(self._semantic_cache):
                        effective = self._effective_ttl(self.tier1_ttl, entry.hit_count)
                        if now - entry.created_at > effective:
                            continue
                        score = float(self.np.dot(q_vec, entry.query_embedding))
                        if score > best_score:
                            best_score = score
                            best_idx = i

                    if best_score >= self.tier1_threshold and best_idx >= 0:
                        entry = self._semantic_cache[best_idx]
                        if self._validate_entry(entry.fingerprint, validate_fn):
                            entry.hit_count += 1
                            self.stats["tier1_semantic_hits"] += 1
                            self.stats["total_llm_savings"] += 1
                            logger.debug(
                                f"[Cache] T1 Semantic Hit ({best_score:.3f}): "
                                f"'{query[:40]}' ≈ '{entry.query_norm[:40]}'"
                            )
                            return self._tag_results(entry.results, "tier1_semantic")
                        else:
                            self._semantic_cache.pop(best_idx)
                            self.stats["fingerprint_invalidations"] += 1

                except Exception as e:
                    logger.warning(f"[Cache] T1 semantic check error: {e}")

            self.stats["tier1_misses"] += 1
            return None

    def set_answer(
        self,
        query: str,
        results: List[Dict],
        source_chunks: Optional[List[Dict]] = None,
    ):
        """
        Store answer in Tier 1 cache.

        Args:
            query: Original user query
            results: Final search results to cache
            source_chunks: The chunks used to build this answer (for fingerprinting)
        """
        with self._lock:
            q_norm = query.strip().lower()
            now = time.time()

            # Build fingerprint from source chunks
            fp = CacheFingerprint.from_chunks(
                source_chunks or results,
                collection_version=self._collection_version,
            )

            # Determine validation strategy (uses classify_strategy)
            strategy = self.classify_strategy(query)

            try:
                q_vec = self.model.encode([query], normalize_embeddings=True)[0]
            except Exception:
                q_vec = None

            entry = Tier1Entry(
                query_norm=q_norm,
                query_embedding=q_vec,
                results=results,
                fingerprint=fp,
                validation_strategy=strategy,
                created_at=now,
            )

            # Store in exact cache
            self._exact_cache[q_norm] = entry

            # Store in semantic cache (if embedding succeeded)
            if q_vec is not None:
                self._semantic_cache.append(entry)

            # ── Prune ──
            self._prune_tier1()

    # ─── Tier 2: Context Cache ─────────────────────────────────────────────

    def get_context(
        self,
        query: str,
        validate_fn: Optional[callable] = None,
    ) -> Optional[List[Dict]]:
        """
        Check Tier 2 (context-level cache).

        Returns cached raw chunks if query topic is ≥70% similar AND
        the cached context is SUFFICIENT for the new query.
        Returns None on miss.

        This is the KEY innovation from the article: even when the specific
        question is different, the underlying documents are often the same.
        Skip Qdrant, feed cached chunks directly to LLM.

        Scenario 2 + Scenario 7 from the article.
        """
        with self._lock:
            now = time.time()

            if self.is_temporal_query(query):
                return None

            if not self._context_cache:
                self.stats["tier2_misses"] += 1
                return None

            try:
                q_vec = self.model.encode([query], normalize_embeddings=True)[0]

                best_score = 0.0
                best_idx = -1

                for i, entry in enumerate(self._context_cache):
                    effective = self._effective_ttl(self.tier2_ttl, entry.hit_count)
                    if now - entry.created_at > effective:
                        continue
                    score = float(self.np.dot(q_vec, entry.query_embedding))
                    if score > best_score:
                        best_score = score
                        best_idx = i

                if best_score >= self.tier2_threshold and best_idx >= 0:
                    entry = self._context_cache[best_idx]

                    # ── Validate fingerprint ──
                    if not self._validate_entry(entry.fingerprint, validate_fn):
                        self._context_cache.pop(best_idx)
                        self.stats["fingerprint_invalidations"] += 1
                        self.stats["tier2_misses"] += 1
                        return None

                    # ── Context Sufficiency Check (Scenario 7) ──
                    if not self._is_context_sufficient(query, entry):
                        entry.hit_count += 1
                        self.stats["tier2_partial_hits"] += 1
                        logger.debug(
                            f"[Cache] T2 Partial Hit ({best_score:.3f}): insufficient context for '{query[:40]}'"
                        )
                        return None  # Force fresh retrieval

                    entry.hit_count += 1
                    self.stats["tier2_hits"] += 1
                    self.stats["total_retrieval_savings"] += 1
                    logger.debug(
                        f"[Cache] T2 Context Hit ({best_score:.3f}): "
                        f"reusing {len(entry.context_chunks)} chunks "
                        f"from '{entry.query_norm[:40]}'"
                    )

                    # Tag chunks so UI knows this was a cache hit
                    return [
                        {
                            **c,
                            "_cache_tier": "tier2_context",
                            "_cache_score": best_score,
                        }
                        for c in entry.context_chunks
                    ]

            except Exception as e:
                logger.warning(f"[Cache] T2 context check error: {e}")

            self.stats["tier2_misses"] += 1
            return None

    def set_context(self, query: str, chunks: List[Dict]):
        """
        Store retrieved context in Tier 2 cache.

        Args:
            query: Original user query
            chunks: Raw retrieved chunks from Qdrant/BM25 (before reranking)
        """
        with self._lock:
            q_norm = query.strip().lower()

            fp = CacheFingerprint.from_chunks(chunks, collection_version=self._collection_version)

            try:
                q_vec = self.model.encode([query], normalize_embeddings=True)[0]
            except Exception:
                return  # Can't cache without embedding

            # Extract topic keywords for sufficiency checking
            keywords = self._extract_topic_keywords(query, chunks)

            entry = Tier2Entry(
                query_norm=q_norm,
                query_embedding=q_vec,
                topic_keywords=keywords,
                context_chunks=chunks,
                fingerprint=fp,
            )
            self._context_cache.append(entry)
            self._prune_tier2()

    # ─── Validation ────────────────────────────────────────────────────────

    def _validate_entry(
        self,
        fingerprint: CacheFingerprint,
        validate_fn: Optional[callable] = None,
    ) -> bool:
        """
        Validate a cache entry's fingerprint.

        Scenarios 4-6 from the article:
        - Collection version check (fast, O(1))
        - SHA-256 fingerprint comparison (via validate_fn callback)
        """
        # ── Version check (cheapest) ──
        if fingerprint.collection_version < self._collection_version:
            # Collection has been modified since this entry was cached.
            # Could still be valid (the specific chunks might not have changed),
            # but if we have a validate_fn, use it. Otherwise, invalidate.
            if validate_fn:
                try:
                    return validate_fn(fingerprint)
                except Exception:
                    return False
            # Conservative: invalidate when version has changed
            self.stats["version_invalidations"] += 1
            return False

        # ── External fingerprint validation ──
        if validate_fn:
            try:
                return validate_fn(fingerprint)
            except Exception:
                return False

        # No version change, no external validation → trust TTL
        return True

    def _is_context_sufficient(self, query: str, entry: Tier2Entry) -> bool:
        """
        Context Sufficiency Check (Scenario 7).

        Verify that the cached context chunks contain enough information
        to answer the NEW query. If the new query asks about topics not
        covered by the cached context, return False → force fresh retrieval.

        Strategy: Extract key nouns/entities from the new query and check
        if they appear in the cached chunks' text.
        """
        # Extract key terms from the new query
        new_keywords = self._extract_query_keywords(query)

        if not new_keywords:
            return True  # Can't determine → optimistic

        # Check how many new keywords are covered by cached context
        cached_text = " ".join(c.get("text", "").lower() for c in entry.context_chunks)

        covered = sum(1 for kw in new_keywords if kw in cached_text)
        coverage_ratio = covered / len(new_keywords) if new_keywords else 1.0

        # Also check against the original query's keywords
        original_keywords = entry.topic_keywords
        keyword_overlap = len(new_keywords & original_keywords) / len(new_keywords) if new_keywords else 1.0

        # Require ≥60% keyword coverage in either the text or query overlap
        is_sufficient = coverage_ratio >= 0.6 or keyword_overlap >= 0.7

        if not is_sufficient:
            logger.debug(
                f"[Cache] Sufficiency FAIL: {covered}/{len(new_keywords)} terms covered "
                f"(ratio={coverage_ratio:.2f}), keyword overlap={keyword_overlap:.2f}"
            )

        return is_sufficient

    # ─── Keyword Extraction ────────────────────────────────────────────────

    _STOPWORDS = frozenset(
        {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "what",
            "which",
            "who",
            "when",
            "where",
            "how",
            "why",
            "do",
            "does",
            "did",
            "can",
            "could",
            "would",
            "should",
            "will",
            "shall",
            "may",
            "might",
            "must",
            "has",
            "have",
            "had",
            "been",
            "being",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "they",
            "them",
            "their",
            "we",
            "our",
            "you",
            "your",
            "i",
            "my",
            "me",
            "he",
            "she",
            "his",
            "her",
            "of",
            "in",
            "on",
            "at",
            "to",
            "for",
            "with",
            "from",
            "by",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "and",
            "but",
            "or",
            "nor",
            "not",
            "no",
            "so",
            "if",
            "then",
            "than",
            "too",
            "very",
            "just",
            "also",
            "all",
            "any",
            "some",
            "each",
            "every",
            "both",
            "few",
            "more",
            "most",
            "other",
            "such",
            "only",
            "own",
            "same",
            "tell",
            "give",
            "show",
            "list",
            "find",
            "get",
            "describe",
            "explain",
            "summarize",
            "compare",
            # Romanian common
            "care",
            "este",
            "sunt",
            "din",
            "pentru",
            "la",
            "cu",
            "de",
            "pe",
            "si",
            "sau",
            "dar",
            "nu",
            "ce",
            "cum",
            "unde",
        }
    )

    _WORD_PATTERN = re.compile(r"[a-zA-ZăîâșțĂÎÂȘȚ]{3,}", re.UNICODE)

    def _extract_query_keywords(self, query: str) -> Set[str]:
        """Extract meaningful keywords from a query."""
        words = set(self._WORD_PATTERN.findall(query.lower()))
        return words - self._STOPWORDS

    def _extract_topic_keywords(self, query: str, chunks: List[Dict]) -> Set[str]:
        """Extract topic keywords from query + chunk texts."""
        keywords = self._extract_query_keywords(query)

        # Also extract prominent terms from chunk texts (top by frequency)
        all_text = " ".join(c.get("text", "") for c in chunks[:5])
        chunk_words = self._WORD_PATTERN.findall(all_text.lower())
        chunk_words = [w for w in chunk_words if w not in self._STOPWORDS]

        # Add top-10 most frequent chunk words
        if chunk_words:
            from collections import Counter

            freq = Counter(chunk_words)
            keywords.update(w for w, _ in freq.most_common(10))

        return keywords

    # ─── Collection Version ────────────────────────────────────────────────

    def bump_version(self):
        """
        Increment collection version after any write/delete to Qdrant.
        Called by build_index(), add_chunks(), delete_document_by_url().
        """
        with self._lock:
            self._collection_version += 1
            logger.debug(f"[Cache] Collection version → {self._collection_version}")

    @property
    def collection_version(self) -> int:
        return self._collection_version

    # ─── Housekeeping ──────────────────────────────────────────────────────

    def _prune_tier1(self):
        """Evict oldest entries if over capacity."""
        # Prune exact cache
        if len(self._exact_cache) > self.max_entries:
            oldest_key = min(
                self._exact_cache,
                key=lambda k: self._exact_cache[k].created_at,
            )
            del self._exact_cache[oldest_key]

        # Prune semantic cache (keep max_entries // 5)
        max_semantic = max(self.max_entries // 5, 50)
        if len(self._semantic_cache) > max_semantic:
            # Remove expired first
            now = time.time()
            self._semantic_cache = [e for e in self._semantic_cache if now - e.created_at < self.tier1_ttl]
            # Still too many? Remove least-hit
            if len(self._semantic_cache) > max_semantic:
                self._semantic_cache.sort(key=lambda e: e.hit_count)
                self._semantic_cache = self._semantic_cache[-max_semantic:]

    def _prune_tier2(self):
        """Evict oldest Tier 2 entries if over capacity."""
        max_context = max(self.max_entries // 3, 100)
        if len(self._context_cache) > max_context:
            now = time.time()
            self._context_cache = [e for e in self._context_cache if now - e.created_at < self.tier2_ttl]
            if len(self._context_cache) > max_context:
                self._context_cache.sort(key=lambda e: e.hit_count)
                self._context_cache = self._context_cache[-max_context:]

    def clear(self):
        """Clear all cache tiers. Called on full index rebuild."""
        with self._lock:
            self._exact_cache.clear()
            self._semantic_cache.clear()
            self._context_cache.clear()
            logger.debug("[Cache] All tiers cleared")

    def _tag_results(self, results: List[Dict], cache_tier: str) -> List[Dict]:
        """Tag results with cache metadata for UI/logging."""
        return [{**r, "_is_cached": True, "_cache_tier": cache_tier} for r in results]

    # ─── Statistics & Diagnostics ──────────────────────────────────────────

    def get_stats(self) -> Dict:
        """Return cache performance statistics."""
        total = self.stats["total_queries"] or 1
        t1_hits = self.stats["tier1_exact_hits"] + self.stats["tier1_semantic_hits"]
        t2_hits = self.stats["tier2_hits"]

        return {
            **self.stats,
            "tier1_entries": len(self._exact_cache),
            "tier1_semantic_entries": len(self._semantic_cache),
            "tier2_entries": len(self._context_cache),
            "collection_version": self._collection_version,
            "tier1_hit_rate": t1_hits / total,
            "tier2_hit_rate": t2_hits / total,
            "overall_hit_rate": (t1_hits + t2_hits) / total,
            "cost_reduction_pct": (self.stats["total_llm_savings"] / total) * 100,
            "retrieval_reduction_pct": (
                (self.stats["total_llm_savings"] + self.stats["total_retrieval_savings"]) / total
            )
            * 100,
        }

    def get_summary(self) -> str:
        """Human-readable cache performance summary."""
        s = self.get_stats()
        return (
            f"Zero-Waste Cache │ "
            f"T1 hits: {s['tier1_exact_hits']}+{s['tier1_semantic_hits']} │ "
            f"T2 hits: {s['tier2_hits']} │ "
            f"Bypassed: {s['temporal_bypasses']} │ "
            f"Invalidated: {s['fingerprint_invalidations']}+{s['version_invalidations']} │ "
            f"LLM savings: {s['cost_reduction_pct']:.1f}% │ "
            f"Retrieval savings: {s['retrieval_reduction_pct']:.1f}%"
        )


# ─── Backward Compatibility Adapter ───────────────────────────────────────


class ZeroWasteCacheAdapter:
    """
    Drop-in replacement for the old SemanticCache interface.

    The old code calls:
        cache.get(query) → results or None
        cache.set(query, results)
        cache.clear()

    This adapter maps those to ZeroWasteCache methods while enabling
    the new Tier 2 functionality and forwarding validate_fn / source_chunks.
    """

    def __init__(self, zero_waste: ZeroWasteCache):
        self._zw = zero_waste

    def get(
        self,
        query: str,
        validate_fn: Optional[callable] = None,
    ) -> Optional[List[Dict]]:
        """Tier 1 answer lookup with optional fingerprint validation."""
        return self._zw.get_answer(query, validate_fn=validate_fn)

    def set(
        self,
        query: str,
        results: List[Dict],
        source_chunks: Optional[List[Dict]] = None,
    ):
        """Store in Tier 1, forwarding source_chunks for proper fingerprinting."""
        self._zw.set_answer(query, results, source_chunks=source_chunks)

    def clear(self):
        """Old-style clear → clear all tiers."""
        self._zw.clear()

    # ── Expose new methods for upgraded search() ──

    def get_context(
        self,
        query: str,
        validate_fn: Optional[callable] = None,
    ) -> Optional[List[Dict]]:
        return self._zw.get_context(query, validate_fn=validate_fn)

    def set_context(self, query: str, chunks: List[Dict]):
        self._zw.set_context(query, chunks)

    def bump_version(self):
        self._zw.bump_version()

    def invalidate_urls(self, urls: Set[str]) -> int:
        """Surgically invalidate cache entries whose source URLs overlap *urls*.

        Returns the number of entries removed. This is much cheaper than
        clear() because only affected entries are evicted.
        """
        return self._zw.invalidate_urls(urls)

    def get_stats(self) -> Dict:
        return self._zw.get_stats()

    def get_summary(self) -> str:
        return self._zw.get_summary()

    @property
    def is_zero_waste(self) -> bool:
        return True
