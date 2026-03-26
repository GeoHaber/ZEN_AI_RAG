"""
Core/semantic_cache.py - Semantic caching for query results

Features:
- Cache query results based on semantic similarity
- TTL (time-to-live) for cache entries
- Cache statistics and monitoring
- Automatic cleanup of expired entries
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


class SemanticCache:
    """Cache query results based on semantic similarity"""

    def __init__(
        self,
        similarity_threshold: float = 0.95,
        ttl_hours: int = 24,
        max_size: int = 1000,
    ):
        """
        Initialize semantic cache

        Args:
            similarity_threshold: Minimum similarity to consider a cache hit (0-1)
            ttl_hours: Time-to-live for cache entries in hours
            max_size: Maximum number of entries to keep in cache
        """
        self.cache: List[Tuple[np.ndarray, str, Dict[str, Any], datetime]] = []
        self.threshold = similarity_threshold
        self.ttl = timedelta(hours=ttl_hours)
        self.max_size = max_size

        # Cleanup interval (check for expired entries every N lookups)
        self._cleanup_interval = 10

        # Statistics
        self.hits = 0
        self.misses = 0
        self.total_lookups = 0

        logger.info(
            f"Semantic cache initialized: threshold={similarity_threshold}, ttl={ttl_hours}h, max_size={max_size}"
        )

    def lookup(self, query: str, query_embedding: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Check if similar query exists in cache

        Args:
            query: Query text
            query_embedding: Query embedding vector

        Returns:
            Cached result if found, None otherwise
        """
        self.total_lookups += 1

        # Periodic cleanup instead of every-lookup (performance optimization)
        if self.total_lookups % self._cleanup_interval == 0:
            self._cleanup_expired()

        if not self.cache:
            self.misses += 1
            return None

        # Vectorized similarity search — batch compute instead of one-by-one
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
        best_match = None
        best_similarity = 0.0

        for cached_emb, cached_query, cached_result, timestamp in self.cache:
            # Fast dot product on pre-normalized vectors
            similarity = float(np.dot(query_norm, cached_emb / (np.linalg.norm(cached_emb) + 1e-10)))
            similarity = max(0.0, min(1.0, similarity))

            if similarity >= self.threshold and similarity > best_similarity:
                best_match = (cached_query, cached_result, similarity)
                best_similarity = similarity

        if best_match:
            cached_query, cached_result, similarity = best_match
            self.hits += 1
            logger.info(f"✅ Cache HIT: '{query}' → '{cached_query}' (similarity: {similarity:.3f})")

            # Add cache metadata
            result = cached_result.copy()
            result["_cache_hit"] = True
            result["_cached_query"] = cached_query
            result["_similarity"] = similarity

            return result

        self.misses += 1
        logger.debug(f"❌ Cache MISS: '{query}'")
        return None

    def store(self, query: str, query_embedding: np.ndarray, result: Dict[str, Any]):
        """
        Store query result in cache

        Args:
            query: Query text
            query_embedding: Query embedding vector
            result: Query result to cache
        """
        # Remove cache metadata before storing
        result_clean = {k: v for k, v in result.items() if not k.startswith("_cache")}

        # Deduplicate: don't re-add if a very similar query is already cached
        q_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
        for cached_emb, cached_query, _, _ in self.cache:
            sim = float(np.dot(q_norm, cached_emb / (np.linalg.norm(cached_emb) + 1e-10)))
            sim = max(0.0, min(1.0, sim))  # Clamp to [0, 1] for consistency with lookup
            if sim >= 0.99:  # Near-duplicate threshold
                logger.debug(f"Cache skip (duplicate): '{query}' ≈ '{cached_query}'")
                return

        # Add to cache
        self.cache.append((query_embedding, query, result_clean, datetime.now()))

        logger.debug(f"💾 Cached result for: '{query}'")

        # Enforce max size (remove oldest entries)
        if len(self.cache) > self.max_size:
            removed = len(self.cache) - self.max_size
            self.cache = self.cache[-self.max_size :]
            logger.debug(f"Cache size limit reached, removed {removed} oldest entries")

    def _cleanup_expired(self):
        """Remove expired cache entries"""
        now = datetime.now()
        original_size = len(self.cache)

        self.cache = [
            (emb, query, result, timestamp)
            for emb, query, result, timestamp in self.cache
            if now - timestamp < self.ttl
        ]

        removed = original_size - len(self.cache)
        if removed > 0:
            logger.debug(f"Removed {removed} expired cache entries")

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            # Ensure vectors are numpy arrays
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Clamp to [0, 1] range
            return max(0.0, min(1.0, float(similarity)))

        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dict with cache performance metrics
        """
        hit_rate = self.hits / self.total_lookups if self.total_lookups > 0 else 0.0
        miss_rate = self.misses / self.total_lookups if self.total_lookups > 0 else 0.0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_lookups": self.total_lookups,
            "hit_rate": hit_rate,
            "miss_rate": miss_rate,
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "threshold": self.threshold,
            "ttl_hours": self.ttl.total_seconds() / 3600,
        }

    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("Cache cleared")

    def reset_stats(self):
        """Reset cache statistics"""
        self.hits = 0
        self.misses = 0
        self.total_lookups = 0
        logger.info("Cache statistics reset")

    def get_cached_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get list of cached queries for debugging

        Args:
            limit: Maximum number of queries to return

        Returns:
            List of cached query info
        """
        queries = []

        for emb, query, result, timestamp in self.cache[-limit:]:
            queries.append(
                {
                    "query": query,
                    "timestamp": timestamp.isoformat(),
                    "age_hours": (datetime.now() - timestamp).total_seconds() / 3600,
                }
            )

        return queries


# Singleton instance
_semantic_cache = None


def get_semantic_cache(similarity_threshold: float = 0.95, ttl_hours: int = 24) -> SemanticCache:
    """Get or create semantic cache instance"""
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCache(similarity_threshold, ttl_hours)
    return _semantic_cache
