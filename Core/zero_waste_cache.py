"""
Core/zero_waste_cache.py — Two-Tier Semantic Cache for RAG Pipeline.

Tier 1 (Answer Cache): Exact + semantic match → return full answer (≥0.95 sim)
Tier 2 (Context Cache): Topic overlap → reuse retrieved chunks (≥0.70 sim)

Features:
  - SHA-256 fingerprint validation per cache entry
  - Collection version tracking for automatic invalidation
  - Adaptive TTL (popular entries live longer)
  - Temporal query bypass (date-sensitive queries skip cache)
  - Surgical URL-based invalidation
  - Context sufficiency checking (Scenario 7)

Ported from ZEN_RAG.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import threading
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Callable

logger = logging.getLogger(__name__)


# ─── Data Structures ───────────────────────────────────────────────────────


@dataclass
class CacheFingerprint:
    """SHA-256 fingerprint of source chunks for cache validation."""

    chunk_hashes: FrozenSet[str]
    source_urls: FrozenSet[str]
    collection_version: int = 0

    @classmethod
    def from_chunks(cls, chunks: List[Dict], collection_version: int = 0) -> "CacheFingerprint":
        hashes = set()
        urls = set()
        for c in chunks:
            text = c.get("text", "")
            hashes.add(hashlib.sha256(text.encode()).hexdigest()[:16])
            url = c.get("url") or c.get("source") or ""
            if url:
                urls.add(url)
        return cls(
            chunk_hashes=frozenset(hashes),
            source_urls=frozenset(urls),
            collection_version=collection_version,
        )


@dataclass
class Tier1Entry:
    """Answer-level cache entry."""

    query_norm: str
    query_embedding: Any  # numpy array or None
    results: List[Dict]
    fingerprint: CacheFingerprint
    validation_strategy: str = "standard"
    created_at: float = field(default_factory=time.time)
    hit_count: int = 0


@dataclass
class Tier2Entry:
    """Context-level cache entry."""

    query_norm: str
    query_embedding: Any  # numpy array
    topic_keywords: Set[str] = field(default_factory=set)
    context_chunks: List[Dict] = field(default_factory=list)
    fingerprint: CacheFingerprint = field(default_factory=lambda: CacheFingerprint(frozenset(), frozenset()))
    created_at: float = field(default_factory=time.time)
    hit_count: int = 0


class CacheValidationStrategy:
    """Strategy pattern for cache validation."""

    STANDARD = "standard"
    STRICT = "strict"
    TEMPORAL = "temporal"


# ─── Temporal Patterns ─────────────────────────────────────────────────────

_TEMPORAL_PATTERNS = re.compile(
    r"\b(today|yesterday|now|current|latest|recent|last\s+\w+|"
    r"this\s+(week|month|year)|"
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|"
    r"(january|february|march|april|may|june|july|august|"
    r"september|october|november|december)\s+\d{4})\b",
    re.IGNORECASE,
)


class ZeroWasteCache:
    """Two-tier semantic cache with fingerprint validation.

    Thread-safe via RLock. Uses sentence-transformers for semantic matching.

    Usage:
        cache = ZeroWasteCache()

        # Check cache before RAG pipeline
        cached = cache.get_answer(query)
        if cached:
            return cached  # Tier 1 hit

        context = cache.get_context(query)
        if context:
            # Tier 2 hit — skip retrieval, go straight to LLM
            answer = llm.generate(query, context)
        else:
            context = rag.retrieve(query)
            cache.set_context(query, context)
            answer = llm.generate(query, context)

        cache.set_answer(query, answer, context)
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        tier1_threshold: float = 0.95,
        tier2_threshold: float = 0.70,
        tier1_ttl: float = 3600,
        tier2_ttl: float = 7200,
        max_entries: int = 500,
    ):
        self.tier1_threshold = tier1_threshold
        self.tier2_threshold = tier2_threshold
        self.tier1_ttl = tier1_ttl
        self.tier2_ttl = tier2_ttl
        self.max_entries = max_entries

        self._lock = threading.RLock()
        self._exact_cache: Dict[str, Tier1Entry] = {}
        self._semantic_cache: List[Tier1Entry] = []
        self._context_cache: List[Tier2Entry] = []
        self._collection_version: int = 0

        self.stats: Dict[str, int] = {
            "tier1_exact_hits": 0,
            "tier1_semantic_hits": 0,
            "tier1_misses": 0,
            "tier2_hits": 0,
            "tier2_partial_hits": 0,
            "tier2_misses": 0,
            "fingerprint_invalidations": 0,
            "version_invalidations": 0,
            "temporal_bypasses": 0,
            "total_retrieval_savings": 0,
        }

        # Lazy-load embedding model
        self._model = None
        self._model_name = model_name

        try:
            import numpy
            self.np = numpy
        except ImportError:
            self.np = None
            logger.warning("[Cache] numpy not available — semantic matching disabled")

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
                logger.info(f"[Cache] Loaded embedding model: {self._model_name}")
            except Exception as e:
                logger.warning(f"[Cache] Could not load embedding model: {e}")
        return self._model

    # ─── Temporal / Strategy ───────────────────────────────────────────────

    @staticmethod
    def is_temporal_query(query: str) -> bool:
        """Check if a query contains temporal references that should bypass cache."""
        return bool(_TEMPORAL_PATTERNS.search(query))

    @staticmethod
    def classify_strategy(query: str) -> str:
        """Classify validation strategy for a query."""
        if ZeroWasteCache.is_temporal_query(query):
            return CacheValidationStrategy.TEMPORAL
        q_lower = query.lower()
        if any(w in q_lower for w in ("exact", "precise", "specific", "verify", "confirm")):
            return CacheValidationStrategy.STRICT
        return CacheValidationStrategy.STANDARD

    def _effective_ttl(self, base_ttl: float, hit_count: int) -> float:
        """Adaptive TTL: popular entries live up to 2x longer."""
        bonus = min(hit_count * 0.1, 1.0)
        return base_ttl * (1.0 + bonus)

    # ─── URL-based Invalidation ────────────────────────────────────────────

    def invalidate_urls(self, urls: List[str]):
        """Surgically remove cache entries that depend on specific URLs."""
        with self._lock:
            url_set = set(urls)
            removed = 0

            # Tier 1 exact
            keys_to_del = [
                k for k, v in self._exact_cache.items()
                if v.fingerprint.source_urls & url_set
            ]
            for k in keys_to_del:
                del self._exact_cache[k]
                removed += 1

            # Tier 1 semantic
            before = len(self._semantic_cache)
            self._semantic_cache = [
                e for e in self._semantic_cache
                if not (e.fingerprint.source_urls & url_set)
            ]
            removed += before - len(self._semantic_cache)

            # Tier 2 context
            before = len(self._context_cache)
            self._context_cache = [
                e for e in self._context_cache
                if not (e.fingerprint.source_urls & url_set)
            ]
            removed += before - len(self._context_cache)

            if removed:
                logger.info(f"[Cache] Invalidated {removed} entries for {len(urls)} URLs")

    # ─── Tier 1: Answer Cache ─────────────────────────────────────────────

    def get_answer(
        self,
        query: str,
        validate_fn: Optional[Callable] = None,
    ) -> Optional[List[Dict]]:
        """Check Tier 1 (answer-level cache). Returns cached results or None."""
        with self._lock:
            now = time.time()

            if self.is_temporal_query(query):
                self.stats["temporal_bypasses"] += 1
                return None

            q_norm = query.strip().lower()

            # ── Exact match ──
            entry = self._exact_cache.get(q_norm)
            if entry:
                effective = self._effective_ttl(self.tier1_ttl, entry.hit_count)
                if now - entry.created_at < effective:
                    if self._validate_entry(entry.fingerprint, validate_fn):
                        entry.hit_count += 1
                        self.stats["tier1_exact_hits"] += 1
                        self.stats["total_retrieval_savings"] += 1
                        logger.debug(f"[Cache] T1 Exact Hit: '{q_norm[:40]}'")
                        return self._tag_results(entry.results, "tier1_exact")
                    else:
                        del self._exact_cache[q_norm]
                        self.stats["fingerprint_invalidations"] += 1
                else:
                    del self._exact_cache[q_norm]

            # ── Semantic match ──
            if self.model and self.np:
                try:
                    q_vec = self.model.encode([query], normalize_embeddings=True)[0]
                    best_score = 0.0
                    best_idx = -1

                    for i, e in enumerate(self._semantic_cache):
                        if e.query_embedding is None:
                            continue
                        effective = self._effective_ttl(self.tier1_ttl, e.hit_count)
                        if now - e.created_at > effective:
                            continue
                        score = float(self.np.dot(q_vec, e.query_embedding))
                        if score > best_score:
                            best_score = score
                            best_idx = i

                    if best_score >= self.tier1_threshold and best_idx >= 0:
                        e = self._semantic_cache[best_idx]
                        if self._validate_entry(e.fingerprint, validate_fn):
                            e.hit_count += 1
                            self.stats["tier1_semantic_hits"] += 1
                            self.stats["total_retrieval_savings"] += 1
                            logger.debug(
                                f"[Cache] T1 Semantic Hit ({best_score:.3f}): "
                                f"'{q_norm[:40]}' ≈ '{e.query_norm[:40]}'"
                            )
                            return self._tag_results(e.results, "tier1_semantic")
                        else:
                            self._semantic_cache.pop(best_idx)
                            self.stats["fingerprint_invalidations"] += 1
                except Exception as ex:
                    logger.warning(f"[Cache] T1 semantic check error: {ex}")

            self.stats["tier1_misses"] += 1
            return None

    def set_answer(
        self,
        query: str,
        results: List[Dict],
        source_chunks: Optional[List[Dict]] = None,
    ):
        """Store a complete answer in Tier 1 cache."""
        with self._lock:
            q_norm = query.strip().lower()
            now = time.time()

            fp = CacheFingerprint.from_chunks(
                source_chunks or results,
                collection_version=self._collection_version,
            )
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
            self._exact_cache[q_norm] = entry
            if q_vec is not None:
                self._semantic_cache.append(entry)
            self._prune_tier1()

    # ─── Tier 2: Context Cache ─────────────────────────────────────────────

    def get_context(
        self,
        query: str,
        validate_fn: Optional[Callable] = None,
    ) -> Optional[List[Dict]]:
        """Check Tier 2 (context-level cache).

        Returns cached raw chunks if query topic is ≥70% similar AND
        the cached context is sufficient for the new query.
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

                    if not self._validate_entry(entry.fingerprint, validate_fn):
                        self._context_cache.pop(best_idx)
                        self.stats["fingerprint_invalidations"] += 1
                        self.stats["tier2_misses"] += 1
                        return None

                    if not self._is_context_sufficient(query, entry):
                        entry.hit_count += 1
                        self.stats["tier2_partial_hits"] += 1
                        return None

                    entry.hit_count += 1
                    self.stats["tier2_hits"] += 1
                    self.stats["total_retrieval_savings"] += 1
                    logger.debug(
                        f"[Cache] T2 Context Hit ({best_score:.3f}): "
                        f"reusing {len(entry.context_chunks)} chunks"
                    )
                    return [
                        {**c, "_cache_tier": "tier2_context", "_cache_score": best_score}
                        for c in entry.context_chunks
                    ]

            except Exception as e:
                logger.warning(f"[Cache] T2 context check error: {e}")

            self.stats["tier2_misses"] += 1
            return None

    def set_context(self, query: str, chunks: List[Dict]):
        """Store retrieved context in Tier 2 cache."""
        with self._lock:
            q_norm = query.strip().lower()
            fp = CacheFingerprint.from_chunks(chunks, collection_version=self._collection_version)

            try:
                q_vec = self.model.encode([query], normalize_embeddings=True)[0]
            except Exception:
                return

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
        validate_fn: Optional[Callable] = None,
    ) -> bool:
        """Validate a cache entry's fingerprint against collection version."""
        if fingerprint.collection_version < self._collection_version:
            if validate_fn:
                try:
                    return validate_fn(fingerprint)
                except Exception:
                    return False
            self.stats["version_invalidations"] += 1
            return False

        if validate_fn:
            try:
                return validate_fn(fingerprint)
            except Exception:
                return False

        return True

    def _is_context_sufficient(self, query: str, entry: Tier2Entry) -> bool:
        """Check if cached context chunks cover the new query's topics."""
        new_keywords = self._extract_query_keywords(query)
        if not new_keywords:
            return True

        cached_text = " ".join(c.get("text", "").lower() for c in entry.context_chunks)
        covered = sum(1 for kw in new_keywords if kw in cached_text)
        coverage_ratio = covered / len(new_keywords) if new_keywords else 1.0

        original_keywords = entry.topic_keywords
        keyword_overlap = len(new_keywords & original_keywords) / len(new_keywords) if new_keywords else 1.0

        return coverage_ratio >= 0.6 or keyword_overlap >= 0.7

    # ─── Keyword Extraction ────────────────────────────────────────────────

    _STOPWORDS = frozenset(
        {
            "the", "a", "an", "is", "are", "was", "were", "what", "which", "who",
            "when", "where", "how", "why", "do", "does", "did", "can", "could",
            "would", "should", "will", "shall", "may", "might", "must", "has",
            "have", "had", "been", "being", "this", "that", "these", "those",
            "it", "its", "they", "them", "their", "we", "our", "you", "your",
            "i", "my", "me", "he", "she", "his", "her", "of", "in", "on", "at",
            "to", "for", "with", "from", "by", "about", "into", "through",
            "during", "before", "after", "above", "below", "between", "and",
            "but", "or", "nor", "not", "no", "so", "if", "then", "than", "too",
            "very", "just", "also", "all", "any", "some", "each", "every",
            "both", "few", "more", "most", "other", "such", "only", "own",
            "same", "tell", "give", "show", "list", "find", "get", "describe",
            "explain", "summarize", "compare",
            # Romanian common
            "care", "este", "sunt", "din", "pentru", "la", "cu", "de", "pe",
            "si", "sau", "dar", "nu", "ce", "cum", "unde",
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
        all_text = " ".join(c.get("text", "") for c in chunks[:5])
        chunk_words = self._WORD_PATTERN.findall(all_text.lower())
        chunk_words = [w for w in chunk_words if w not in self._STOPWORDS]
        if chunk_words:
            freq = Counter(chunk_words)
            keywords.update(w for w, _ in freq.most_common(10))
        return keywords

    # ─── Collection Version ────────────────────────────────────────────────

    def bump_version(self):
        """Increment collection version after any write/delete to Qdrant."""
        with self._lock:
            self._collection_version += 1
            logger.debug(f"[Cache] Collection version → {self._collection_version}")

    @property
    def collection_version(self) -> int:
        return self._collection_version

    # ─── Housekeeping ──────────────────────────────────────────────────────

    def _prune_tier1(self):
        """Evict oldest entries if over capacity."""
        if len(self._exact_cache) > self.max_entries:
            oldest_key = min(
                self._exact_cache,
                key=lambda k: self._exact_cache[k].created_at,
            )
            del self._exact_cache[oldest_key]

        max_semantic = max(self.max_entries // 5, 50)
        if len(self._semantic_cache) > max_semantic:
            now = time.time()
            self._semantic_cache = [e for e in self._semantic_cache if now - e.created_at < self.tier1_ttl]
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
        """Clear all cache tiers."""
        with self._lock:
            self._exact_cache.clear()
            self._semantic_cache.clear()
            self._context_cache.clear()
            logger.debug("[Cache] All tiers cleared")

    def _tag_results(self, results: List[Dict], cache_tier: str) -> List[Dict]:
        """Tag results with cache metadata for UI/logging."""
        return [{**r, "_is_cached": True, "_cache_tier": cache_tier} for r in results]
