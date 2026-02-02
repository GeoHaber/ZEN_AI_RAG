#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
semantic_cache.py - Tier 0: Instant Semantic Cache

Production-grade semantic caching for sub-millisecond responses.
Based on FrugalGPT research: 21% hit rate, 95% cost/latency reduction.

Features:
- Exact hash matching (SHA256)
- Semantic similarity matching (FAISS)
- TTL-based invalidation
- Hit count tracking
- Thread-safe operations
- Redis-ready architecture (currently in-memory)
"""
import time
import hashlib
import logging
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
import json

logger = logging.getLogger(__name__)

# Core dependencies
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    logger.warning("[SemanticCache] sentence-transformers or faiss-cpu not installed")


# =============================================================================
# Configuration
# =============================================================================
@dataclass
class CacheConfig:
    """Semantic cache configuration."""

    # Similarity thresholds
    EXACT_MATCH_THRESHOLD: float = 1.0        # SHA256 exact match
    SEMANTIC_MATCH_THRESHOLD: float = 0.98    # Very high similarity

    # TTL (time to live) in seconds
    TTL_LLM_ANSWER: int = 24 * 3600          # 24 hours for LLM answers
    TTL_RAG_ANSWER: int = 7 * 24 * 3600      # 7 days for RAG answers
    TTL_CONSENSUS_ANSWER: int = 14 * 24 * 3600  # 14 days for consensus

    # Cache size limits
    MAX_CACHE_SIZE: int = 10000               # Max entries before eviction
    MAX_MEMORY_MB: int = 500                  # Max memory usage

    # Performance
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # Fast, 384-dim embeddings

    # Monitoring
    LOG_HITS: bool = True                     # Log cache hits for analysis
    SAVE_INTERVAL: int = 300                  # Save to disk every 5 min


# =============================================================================
# Data Classes
# =============================================================================
@dataclass
class CacheEntry:
    """Single cache entry."""
    query_hash: str                  # SHA256 of normalized query
    query_text: str                  # Original query (for debugging)
    query_embedding: np.ndarray      # 384-dim vector
    answer: str                      # Cached response
    timestamp: datetime              # Creation time
    ttl: int                         # Time to live (seconds)
    source: str                      # "mini_rag" | "llm" | "consensus"
    confidence: float                # Original confidence score
    hit_count: int = 0               # Times served
    last_hit: Optional[datetime] = None  # Last access time

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > self.ttl

    def to_dict(self) -> Dict:
        """Serialize to dict (for JSON storage)."""
        return {
            "query_hash": self.query_hash,
            "query_text": self.query_text,
            "query_embedding": self.query_embedding.tolist(),
            "answer": self.answer,
            "timestamp": self.timestamp.isoformat(),
            "ttl": self.ttl,
            "source": self.source,
            "confidence": self.confidence,
            "hit_count": self.hit_count,
            "last_hit": self.last_hit.isoformat() if self.last_hit else None
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'CacheEntry':
        """Deserialize from dict."""
        return cls(
            query_hash=data["query_hash"],
            query_text=data["query_text"],
            query_embedding=np.array(data["query_embedding"], dtype=np.float32),
            answer=data["answer"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            ttl=data["ttl"],
            source=data["source"],
            confidence=data["confidence"],
            hit_count=data["hit_count"],
            last_hit=datetime.fromisoformat(data["last_hit"]) if data["last_hit"] else None
        )


@dataclass
class CacheStats:
    """Cache statistics."""
    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    exact_matches: int = 0
    semantic_matches: int = 0
    expired_entries: int = 0
    evicted_entries: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        if self.total_queries == 0:
            return 0.0
        return (self.cache_hits / self.total_queries) * 100

    def to_dict(self) -> Dict:
        """Export as dict."""
        return {
            "total_queries": self.total_queries,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": f"{self.hit_rate:.2f}%",
            "exact_matches": self.exact_matches,
            "semantic_matches": self.semantic_matches,
            "expired_entries": self.expired_entries,
            "evicted_entries": self.evicted_entries
        }


# =============================================================================
# Semantic Cache Implementation
# =============================================================================
class SemanticCache:
    """
    Production-grade semantic cache with FAISS and in-memory storage.

    Architecture:
    - Layer 1: SHA256 hash lookup (exact matches, <1μs)
    - Layer 2: FAISS vector search (semantic matches, <10ms)
    - Layer 3: TTL-based expiration
    - Layer 4: LRU eviction when full
    """

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        cache_dir: Optional[Path] = None
    ):
        if not DEPS_AVAILABLE:
            raise ImportError("Install: pip install sentence-transformers faiss-cpu")

        self.config = config or CacheConfig()
        self.cache_dir = cache_dir or Path("cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load embedding model
        logger.info(f"[SemanticCache] Loading model: {self.config.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(self.config.EMBEDDING_MODEL)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        # Storage
        self.entries: OrderedDict[str, CacheEntry] = OrderedDict()  # LRU
        self.hash_to_key: Dict[str, str] = {}  # Fast hash lookup

        # FAISS index
        self.index: Optional[faiss.IndexFlatIP] = None  # Inner product = cosine sim
        self.index_to_hash: List[str] = []  # Map FAISS idx -> query hash

        # Statistics
        self.stats = CacheStats()

        # Thread safety
        self._lock = threading.RLock()

        # Auto-save timer
        self._last_save = time.time()

        # Load from disk
        self._load_from_disk()

    # =========================================================================
    # Core Operations
    # =========================================================================

    def get(self, query: str) -> Optional[Tuple[str, str, float]]:
        """
        Get cached answer for query.

        Returns:
            (answer, source, confidence) if cache hit
            None if cache miss
        """
        with self._lock:
            self.stats.total_queries += 1

            # Normalize query
            query_normalized = self._normalize_query(query)
            query_hash = self._hash_query(query_normalized)

            # Layer 1: Exact hash match
            if query_hash in self.hash_to_key:
                entry = self.entries[self.hash_to_key[query_hash]]

                # Check expiration
                if entry.is_expired():
                    self._remove_entry(query_hash)
                    self.stats.expired_entries += 1
                    self.stats.cache_misses += 1
                    return None

                # Cache hit!
                self._record_hit(entry)
                self.stats.cache_hits += 1
                self.stats.exact_matches += 1

                if self.config.LOG_HITS:
                    logger.debug(f"[Cache] EXACT HIT: {query[:50]}... (hits: {entry.hit_count})")

                return entry.answer, entry.source, entry.confidence

            # Layer 2: Semantic similarity search
            semantic_result = self._semantic_search(query_normalized)

            if semantic_result:
                answer, source, confidence, similarity = semantic_result

                self.stats.cache_hits += 1
                self.stats.semantic_matches += 1

                if self.config.LOG_HITS:
                    logger.debug(f"[Cache] SEMANTIC HIT: {query[:50]}... (sim: {similarity:.3f})")

                return answer, source, confidence

            # Cache miss
            self.stats.cache_misses += 1
            return None

    def put(
        self,
        query: str,
        answer: str,
        source: str,
        confidence: float = 1.0,
        ttl: Optional[int] = None
    ):
        """
        Add entry to cache.

        Args:
            query: User query
            answer: Response to cache
            source: "mini_rag" | "llm" | "consensus"
            confidence: Confidence score (0-1)
            ttl: Custom TTL in seconds (optional)
        """
        with self._lock:
            # Normalize query
            query_normalized = self._normalize_query(query)
            query_hash = self._hash_query(query_normalized)

            # Determine TTL
            if ttl is None:
                if source == "mini_rag":
                    ttl = self.config.TTL_RAG_ANSWER
                elif source == "consensus":
                    ttl = self.config.TTL_CONSENSUS_ANSWER
                else:
                    ttl = self.config.TTL_LLM_ANSWER

            # Embed query
            query_embedding = self.model.encode(query_normalized, convert_to_numpy=True)

            # Create entry
            entry = CacheEntry(
                query_hash=query_hash,
                query_text=query,
                query_embedding=query_embedding,
                answer=answer,
                timestamp=datetime.now(),
                ttl=ttl,
                source=source,
                confidence=confidence
            )

            # Check if already exists
            if query_hash in self.hash_to_key:
                # Update existing entry
                old_key = self.hash_to_key[query_hash]
                self.entries[old_key] = entry
                self.entries.move_to_end(old_key)
            else:
                # Add new entry
                # Check size limit
                if len(self.entries) >= self.config.MAX_CACHE_SIZE:
                    self._evict_lru()

                # Add to storage
                self.entries[query_hash] = entry
                self.hash_to_key[query_hash] = query_hash

                # Add to FAISS index
                self._add_to_index(query_hash, query_embedding)

            # Auto-save check
            if time.time() - self._last_save > self.config.SAVE_INTERVAL:
                self._save_to_disk()

    def invalidate(self, query: str):
        """Invalidate cached entry for query."""
        with self._lock:
            query_normalized = self._normalize_query(query)
            query_hash = self._hash_query(query_normalized)

            if query_hash in self.hash_to_key:
                self._remove_entry(query_hash)
                logger.info(f"[Cache] Invalidated: {query[:50]}...")

    def clear(self):
        """Clear entire cache."""
        with self._lock:
            self.entries.clear()
            self.hash_to_key.clear()
            self.index = None
            self.index_to_hash = []
            self.stats = CacheStats()
            logger.info("[Cache] Cleared all entries")

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        with self._lock:
            return {
                **self.stats.to_dict(),
                "total_entries": len(self.entries),
                "index_size": len(self.index_to_hash),
                "memory_mb": self._estimate_memory_mb()
            }

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent hashing."""
        # Lowercase, strip whitespace, remove extra spaces
        normalized = ' '.join(query.lower().strip().split())
        return normalized

    def _hash_query(self, query: str) -> str:
        """Generate SHA256 hash of query."""
        return hashlib.sha256(query.encode('utf-8')).hexdigest()

    def _semantic_search(
        self,
        query: str
    ) -> Optional[Tuple[str, str, float, float]]:
        """
        Search for semantically similar cached queries.

        Returns:
            (answer, source, confidence, similarity) if found
            None if no similar query above threshold
        """
        if self.index is None or len(self.index_to_hash) == 0:
            return None

        # Embed query
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        query_embedding = query_embedding.reshape(1, -1)

        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)

        # Search (k=3 for robustness)
        k = min(3, len(self.index_to_hash))
        distances, indices = self.index.search(query_embedding, k)

        # Check best match
        if distances[0][0] >= self.config.SEMANTIC_MATCH_THRESHOLD:
            best_idx = indices[0][0]
            similarity = float(distances[0][0])

            # Get cached entry
            query_hash = self.index_to_hash[best_idx]
            entry = self.entries[self.hash_to_key[query_hash]]

            # Check expiration
            if entry.is_expired():
                self._remove_entry(query_hash)
                return None

            # Record hit
            self._record_hit(entry)

            return entry.answer, entry.source, entry.confidence, similarity

        return None

    def _record_hit(self, entry: CacheEntry):
        """Record cache hit."""
        entry.hit_count += 1
        entry.last_hit = datetime.now()

        # Move to end (LRU)
        self.entries.move_to_end(entry.query_hash)

    def _add_to_index(self, query_hash: str, embedding: np.ndarray):
        """Add embedding to FAISS index."""
        # Initialize index if needed
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.embedding_dim)

        # Normalize for cosine similarity
        embedding = embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(embedding)

        # Add to index
        self.index.add(embedding)
        self.index_to_hash.append(query_hash)

    def _remove_entry(self, query_hash: str):
        """Remove entry from cache and index."""
        if query_hash not in self.hash_to_key:
            return

        key = self.hash_to_key[query_hash]

        # Remove from dict
        del self.entries[key]
        del self.hash_to_key[query_hash]

        # Note: FAISS doesn't support removal, so we rebuild index periodically
        # For now, just mark as removed (will be cleaned on next save/load)

    def _evict_lru(self):
        """Evict least recently used entry."""
        # Get oldest entry (LRU)
        oldest_hash = next(iter(self.entries))
        self._remove_entry(oldest_hash)
        self.stats.evicted_entries += 1
        logger.debug(f"[Cache] Evicted LRU entry: {oldest_hash[:8]}...")

    def _rebuild_index(self):
        """Rebuild FAISS index from scratch."""
        logger.info("[Cache] Rebuilding FAISS index...")

        self.index = None
        self.index_to_hash = []

        # Re-add all valid entries
        for query_hash, entry in self.entries.items():
            if not entry.is_expired():
                self._add_to_index(query_hash, entry.query_embedding)

        logger.info(f"[Cache] Index rebuilt: {len(self.index_to_hash)} entries")

    def _estimate_memory_mb(self) -> float:
        """Estimate memory usage in MB."""
        # Rough estimate
        entry_size = 1000  # ~1KB per entry (text + embedding)
        total_bytes = len(self.entries) * entry_size
        return total_bytes / (1024 * 1024)

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_to_disk(self):
        """Save cache to disk."""
        try:
            cache_file = self.cache_dir / "semantic_cache.json"

            # Serialize entries
            data = {
                "entries": [entry.to_dict() for entry in self.entries.values()],
                "stats": self.stats.to_dict(),
                "timestamp": datetime.now().isoformat()
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            self._last_save = time.time()
            logger.debug(f"[Cache] Saved {len(self.entries)} entries to disk")

        except Exception as e:
            logger.error(f"[Cache] Failed to save: {e}")

    def _load_from_disk(self):
        """Load cache from disk."""
        try:
            cache_file = self.cache_dir / "semantic_cache.json"

            if not cache_file.exists():
                logger.info("[Cache] No existing cache found, starting fresh")
                return

            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load entries
            for entry_data in data.get("entries", []):
                entry = CacheEntry.from_dict(entry_data)

                # Skip expired entries
                if entry.is_expired():
                    continue

                self.entries[entry.query_hash] = entry
                self.hash_to_key[entry.query_hash] = entry.query_hash

            # Rebuild FAISS index
            if len(self.entries) > 0:
                self._rebuild_index()

            logger.info(f"[Cache] Loaded {len(self.entries)} entries from disk")

        except Exception as e:
            logger.error(f"[Cache] Failed to load: {e}")

    def __del__(self):
        """Save on cleanup."""
        try:
            self._save_to_disk()
        except:
            pass


# =============================================================================
# Utility Functions
# =============================================================================
def create_default_cache(cache_dir: Optional[Path] = None) -> SemanticCache:
    """Create cache with default configuration."""
    return SemanticCache(cache_dir=cache_dir)


if __name__ == "__main__":
    # Test the cache
    logging.basicConfig(level=logging.DEBUG)

    cache = create_default_cache(Path("test_cache"))

    # Add some entries
    cache.put("What is 2+2?", "2+2 equals 4.", source="mini_rag", confidence=0.99)
    cache.put("How do I start the LLM?", "Run python start_llm.py", source="mini_rag", confidence=0.99)
    cache.put("What is Python?", "Python is a programming language.", source="llm", confidence=0.85)

    # Test exact match
    result = cache.get("What is 2+2?")
    print(f"Exact match: {result}")

    # Test semantic match
    result = cache.get("what's 2 plus 2?")
    print(f"Semantic match: {result}")

    # Test miss
    result = cache.get("What is the meaning of life?")
    print(f"Cache miss: {result}")

    # Stats
    print(f"\nStats: {json.dumps(cache.get_stats(), indent=2)}")
