"""
Core/metrics_tracker.py — Real-time performance metrics tracker for ZEN_RAG.

Quick Win #2: Tracks key operational metrics and exposes them for the Streamlit dashboard.

Tracked metrics:
  - Cache hit rate (Tier 1 and Tier 2 separately)
  - Retrieval latency (mean, p50, p95)
  - Hallucination detection rate
  - Indexing throughput (chunks/sec)
  - Query volume over time

Thread-safe. Stores recent history in a ring buffer (no external DB needed).
"""

import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Deque, Dict, List, Optional, Tuple


# =============================================================================
# Data Types
# =============================================================================


@dataclass
class QueryEvent:
    timestamp: float
    query: str
    latency_s: float
    cache_tier: Optional[int]  # 1 = Tier1 hit, 2 = Tier2 hit, None = full retrieval
    n_results: int
    hallucination_detected: bool = False


@dataclass
class IndexEvent:
    timestamp: float
    chunks_added: int
    duration_s: float
    source: str = ""


@dataclass
class MetricsSummary:
    """Snapshot of current system health."""

    n_queries_total: int = 0
    n_queries_1h: int = 0
    cache_hit_rate_t1: float = 0.0
    cache_hit_rate_t2: float = 0.0
    cache_hit_rate_total: float = 0.0
    avg_latency_s: float = 0.0
    p50_latency_s: float = 0.0
    p95_latency_s: float = 0.0
    hallucination_rate: float = 0.0
    total_chunks_indexed: int = 0
    avg_indexing_throughput: float = 0.0  # chunks/sec
    uptime_s: float = 0.0
    last_query_at: Optional[str] = None


# =============================================================================
# MetricsTracker
# =============================================================================


class MetricsTracker:
    """
    Singleton-compatible, thread-safe metrics tracker for ZEN_RAG.

    Usage:
        tracker = MetricsTracker.get_instance()
        tracker.record_query("my query", latency_s=0.45, cache_tier=1)
        summary = tracker.get_summary()
    """

    _instance: Optional["MetricsTracker"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, history_size: int = 1000):
        self._query_history: Deque[QueryEvent] = deque(maxlen=history_size)
        self._index_history: Deque[IndexEvent] = deque(maxlen=200)
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._total_chunks_indexed = 0

    @classmethod
    def get_instance(cls) -> "MetricsTracker":
        """Get or create the global singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # =========================================================================
    # Recording methods
    # =========================================================================

    def record_query(
        self,
        query: str,
        latency_s: float,
        cache_tier: Optional[int] = None,
        n_results: int = 0,
        hallucination_detected: bool = False,
    ):
        """Record a completed search query."""
        event = QueryEvent(
            timestamp=time.time(),
            query=query[:100],
            latency_s=latency_s,
            cache_tier=cache_tier,
            n_results=n_results,
            hallucination_detected=hallucination_detected,
        )
        with self._lock:
            self._query_history.append(event)

    def record_indexing(self, chunks_added: int, duration_s: float, source: str = ""):
        """Record a completed indexing operation."""
        with self._lock:
            self._index_history.append(
                IndexEvent(
                    timestamp=time.time(),
                    chunks_added=chunks_added,
                    duration_s=max(duration_s, 0.001),
                    source=source,
                )
            )
            self._total_chunks_indexed += chunks_added

    # =========================================================================
    # Retrieval methods
    # =========================================================================

    def get_summary(self) -> MetricsSummary:
        """Compute and return current metrics summary."""
        with self._lock:
            events = list(self._query_history)
            idx_events = list(self._index_history)

        now = time.time()
        cutoff_1h = now - 3600

        # Filter last hour
        events_1h = [e for e in events if e.timestamp >= cutoff_1h]
        n_total = len(events)
        n_1h = len(events_1h)

        # Cache hit rates
        if n_total > 0:
            t1_hits = sum(1 for e in events if e.cache_tier == 1)
            t2_hits = sum(1 for e in events if e.cache_tier == 2)
            total_hits = t1_hits + t2_hits
            t1_rate = t1_hits / n_total
            t2_rate = t2_hits / n_total
            total_rate = total_hits / n_total
        else:
            t1_rate = t2_rate = total_rate = 0.0

        # Latency percentiles
        latencies = sorted(e.latency_s for e in events)
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        p50 = latencies[int(len(latencies) * 0.5)] if latencies else 0.0
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

        # Hallucination rate
        hal_rate = sum(1 for e in events if e.hallucination_detected) / n_total if n_total > 0 else 0.0

        # Indexing throughput (avg chunks/sec)
        if idx_events:
            total_throughput = sum(e.chunks_added / e.duration_s for e in idx_events) / len(idx_events)
        else:
            total_throughput = 0.0

        last_query_at = None
        if events:
            last_ts = max(e.timestamp for e in events)
            last_query_at = datetime.fromtimestamp(last_ts).strftime("%H:%M:%S")

        return MetricsSummary(
            n_queries_total=n_total,
            n_queries_1h=n_1h,
            cache_hit_rate_t1=round(t1_rate, 4),
            cache_hit_rate_t2=round(t2_rate, 4),
            cache_hit_rate_total=round(total_rate, 4),
            avg_latency_s=round(avg_lat, 3),
            p50_latency_s=round(p50, 3),
            p95_latency_s=round(p95, 3),
            hallucination_rate=round(hal_rate, 4),
            total_chunks_indexed=self._total_chunks_indexed,
            avg_indexing_throughput=round(total_throughput, 1),
            uptime_s=round(now - self._start_time, 0),
            last_query_at=last_query_at,
        )

    def get_query_timeline(self, last_n_minutes: int = 60) -> List[Tuple[str, int]]:
        """Return (minute_bucket, count) pairs for the last N minutes."""
        with self._lock:
            events = list(self._query_history)

        now = time.time()
        cutoff = now - last_n_minutes * 60
        relevant = [e for e in events if e.timestamp >= cutoff]

        buckets: Dict[str, int] = {}
        for e in relevant:
            minute = datetime.fromtimestamp(e.timestamp).strftime("%H:%M")
            buckets[minute] = buckets.get(minute, 0) + 1

        return sorted(buckets.items())

    def get_latency_histogram(self) -> Dict[str, int]:
        """Group latencies into buckets for histogram display."""
        with self._lock:
            latencies = [e.latency_s for e in self._query_history]

        buckets = {
            "<0.1s": 0,
            "0.1-0.5s": 0,
            "0.5-1s": 0,
            "1-2s": 0,
            "2-5s": 0,
            ">5s": 0,
        }
        for lat in latencies:
            if lat < 0.1:
                buckets["<0.1s"] += 1
            elif lat < 0.5:
                buckets["0.1-0.5s"] += 1
            elif lat < 1.0:
                buckets["0.5-1s"] += 1
            elif lat < 2.0:
                buckets["1-2s"] += 1
            elif lat < 5.0:
                buckets["2-5s"] += 1
            else:
                buckets[">5s"] += 1
        return buckets

    def reset(self):
        """Clear all metrics history."""
        with self._lock:
            self._query_history.clear()
            self._index_history.clear()
            self._total_chunks_indexed = 0
            self._start_time = time.time()
