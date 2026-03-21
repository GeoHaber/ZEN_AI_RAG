"""
Core/metrics_tracker.py — Thread-Safe Singleton Metrics Tracker.

Tracks:
  - Cache hit rates (tier1 exact, tier1 semantic, tier2)
  - Query latency percentiles (p50, p90, p99)
  - Hallucination rates
  - Indexing throughput
  - RAG pipeline performance

Ported from ZEN_RAG.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class QueryEvent:
    """A single query event for metrics tracking."""

    query: str = ""
    latency_ms: float = 0.0
    cache_hit: bool = False
    cache_tier: str = ""
    chunks_retrieved: int = 0
    chunks_after_dedup: int = 0
    hallucination_probability: float = 0.0
    quality_score: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class IndexEvent:
    """A single indexing event for metrics tracking."""

    url: str = ""
    chunks_created: int = 0
    processing_time_ms: float = 0.0
    doc_type: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class MetricsSummary:
    """Aggregated metrics summary."""

    total_queries: int = 0
    cache_hit_rate: float = 0.0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p90_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    avg_hallucination_rate: float = 0.0
    avg_quality_score: float = 0.0
    total_documents_indexed: int = 0
    avg_indexing_time_ms: float = 0.0
    total_chunks_created: int = 0


class MetricsTracker:
    """Thread-safe singleton metrics tracker for RAG pipeline.

    Usage:
        tracker = get_metrics_tracker()
        tracker.record_query(QueryEvent(latency_ms=150, cache_hit=True))
        summary = tracker.get_summary()
    """

    _instance: Optional["MetricsTracker"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MetricsTracker":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, max_history: int = 1000):
        if self._initialized:
            return
        self._query_events: Deque[QueryEvent] = deque(maxlen=max_history)
        self._index_events: Deque[IndexEvent] = deque(maxlen=max_history)
        self._data_lock = threading.RLock()
        self._initialized = True

    def record_query(self, event: QueryEvent):
        """Record a query event."""
        with self._data_lock:
            self._query_events.append(event)

    def record_index(self, event: IndexEvent):
        """Record an indexing event."""
        with self._data_lock:
            self._index_events.append(event)

    def get_summary(self, window_seconds: Optional[float] = None) -> MetricsSummary:
        """Get aggregated metrics summary."""
        with self._data_lock:
            now = time.time()

            # Filter by time window
            if window_seconds:
                queries = [e for e in self._query_events if now - e.timestamp < window_seconds]
                indexes = [e for e in self._index_events if now - e.timestamp < window_seconds]
            else:
                queries = list(self._query_events)
                indexes = list(self._index_events)

            if not queries:
                return MetricsSummary(
                    total_documents_indexed=len(indexes),
                    total_chunks_created=sum(e.chunks_created for e in indexes),
                )

            latencies = sorted(e.latency_ms for e in queries)
            cache_hits = sum(1 for e in queries if e.cache_hit)

            n = len(latencies)
            summary = MetricsSummary(
                total_queries=n,
                cache_hit_rate=cache_hits / n if n else 0,
                avg_latency_ms=sum(latencies) / n,
                p50_latency_ms=latencies[n // 2] if n else 0,
                p90_latency_ms=latencies[int(n * 0.9)] if n else 0,
                p99_latency_ms=latencies[int(n * 0.99)] if n else 0,
                avg_hallucination_rate=sum(e.hallucination_probability for e in queries) / n,
                avg_quality_score=sum(e.quality_score for e in queries) / n,
                total_documents_indexed=len(indexes),
                avg_indexing_time_ms=sum(e.processing_time_ms for e in indexes) / len(indexes) if indexes else 0,
                total_chunks_created=sum(e.chunks_created for e in indexes),
            )

            return summary

    def get_recent_queries(self, n: int = 10) -> List[QueryEvent]:
        """Get the N most recent query events."""
        with self._data_lock:
            return list(self._query_events)[-n:]

    def clear(self):
        """Clear all metrics."""
        with self._data_lock:
            self._query_events.clear()
            self._index_events.clear()


# ─── Module-level accessor ─────────────────────────────────────────────────

_tracker: Optional[MetricsTracker] = None


def get_metrics_tracker() -> MetricsTracker:
    """Get the singleton MetricsTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = MetricsTracker()
    return _tracker
