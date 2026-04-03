/// Core/metrics_tracker::py — Real-time performance metrics tracker for ZEN_RAG.
/// 
/// Quick Win #2: Tracks key operational metrics and exposes them for the Streamlit dashboard.
/// 
/// Tracked metrics:
/// - Cache hit rate (Tier 1 and Tier 2 separately)
/// - Retrieval latency (mean, p50, p95)
/// - Hallucination detection rate
/// - Indexing throughput (chunks/sec)
/// - Query volume over time
/// 
/// Thread-safe. Stores recent history in a ring buffer (no external DB needed).

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryEvent {
    pub timestamp: f64,
    pub query: String,
    pub latency_s: f64,
    pub cache_tier: Option<i64>,
    pub n_results: i64,
    pub hallucination_detected: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexEvent {
    pub timestamp: f64,
    pub chunks_added: i64,
    pub duration_s: f64,
    pub source: String,
}

/// Snapshot of current system health.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsSummary {
    pub n_queries_total: i64,
    pub n_queries_1h: i64,
    pub cache_hit_rate_t1: f64,
    pub cache_hit_rate_t2: f64,
    pub cache_hit_rate_total: f64,
    pub avg_latency_s: f64,
    pub p50_latency_s: f64,
    pub p95_latency_s: f64,
    pub hallucination_rate: f64,
    pub total_chunks_indexed: i64,
    pub avg_indexing_throughput: f64,
    pub uptime_s: f64,
    pub last_query_at: Option<String>,
}

/// Singleton-compatible, thread-safe metrics tracker for ZEN_RAG.
/// 
/// Usage:
/// tracker = MetricsTracker.get_instance()
/// tracker.record_query("my query", latency_s=0.45, cache_tier=1)
/// summary = tracker.get_summary()
#[derive(Debug, Clone)]
pub struct MetricsTracker {
    pub _instance: Option<serde_json::Value>,
    pub _lock: threading::Lock,
}

impl MetricsTracker {
    pub fn new(history_size: i64) -> Self {
        Self {
            _instance: None,
            _lock: std::sync::Mutex::new(()),
        }
    }
    /// Get or create the global singleton instance.
    pub fn get_instance() -> () {
        // Get or create the global singleton instance.
        if cls._instance.is_none() {
            let _ctx = cls._lock;
            {
                if cls._instance.is_none() {
                    cls._instance = cls();
                }
            }
        }
        cls._instance
    }
    /// Record a completed search query.
    pub fn record_query(&mut self, query: String, latency_s: f64, cache_tier: Option<i64>, n_results: i64, hallucination_detected: bool) -> () {
        // Record a completed search query.
        let mut event = QueryEvent(/* timestamp= */ std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64(), /* query= */ query[..100], /* latency_s= */ latency_s, /* cache_tier= */ cache_tier, /* n_results= */ n_results, /* hallucination_detected= */ hallucination_detected);
        let _ctx = self._lock;
        {
            self._query_history.push(event);
        }
    }
    /// Record a completed indexing operation.
    pub fn record_indexing(&mut self, chunks_added: i64, duration_s: f64, source: String) -> () {
        // Record a completed indexing operation.
        let _ctx = self._lock;
        {
            self._index_history.push(IndexEvent(/* timestamp= */ std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64(), /* chunks_added= */ chunks_added, /* duration_s= */ duration_s.max(0.001_f64), /* source= */ source));
            self._total_chunks_indexed += chunks_added;
        }
    }
    /// Compute and return current metrics summary.
    pub fn get_summary(&mut self) -> MetricsSummary {
        // Compute and return current metrics summary.
        let _ctx = self._lock;
        {
            let mut events = self._query_history.into_iter().collect::<Vec<_>>();
            let mut idx_events = self._index_history.into_iter().collect::<Vec<_>>();
        }
        let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut cutoff_1h = (now - 3600);
        let mut events_1h = events.iter().filter(|e| e.timestamp >= cutoff_1h).map(|e| e).collect::<Vec<_>>();
        let mut n_total = events.len();
        let mut n_1h = events_1h.len();
        if n_total > 0 {
            let mut t1_hits = events.iter().filter(|e| e.cache_tier == 1).map(|e| 1).collect::<Vec<_>>().iter().sum::<i64>();
            let mut t2_hits = events.iter().filter(|e| e.cache_tier == 2).map(|e| 1).collect::<Vec<_>>().iter().sum::<i64>();
            let mut total_hits = (t1_hits + t2_hits);
            let mut t1_rate = (t1_hits / n_total);
            let mut t2_rate = (t2_hits / n_total);
            let mut total_rate = (total_hits / n_total);
        } else {
            // TODO: t1_rate = t2_rate = total_rate = 0.0
        }
        let mut latencies = { let mut v = events.iter().map(|e| e.latency_s).collect::<Vec<_>>().clone(); v.sort(); v };
        let mut avg_lat = if latencies { (latencies.iter().sum::<i64>() / latencies.len()) } else { 0.0_f64 };
        let mut p50 = if latencies { latencies[&(latencies.len() * 0.5_f64).to_string().parse::<i64>().unwrap_or(0)] } else { 0.0_f64 };
        let mut p95 = if latencies { latencies[&(latencies.len() * 0.95_f64).to_string().parse::<i64>().unwrap_or(0)] } else { 0.0_f64 };
        let mut hal_rate = if n_total > 0 { (events.iter().filter(|e| e.hallucination_detected).map(|e| 1).collect::<Vec<_>>().iter().sum::<i64>() / n_total) } else { 0.0_f64 };
        if idx_events {
            let mut total_throughput = (idx_events.iter().map(|e| (e.chunks_added / e.duration_s)).collect::<Vec<_>>().iter().sum::<i64>() / idx_events.len());
        } else {
            let mut total_throughput = 0.0_f64;
        }
        let mut last_query_at = None;
        if events {
            let mut last_ts = events.iter().map(|e| e.timestamp).collect::<Vec<_>>().iter().max().unwrap();
            let mut last_query_at = datetime::fromtimestamp(last_ts).strftime("%H:%M:%S".to_string());
        }
        MetricsSummary(/* n_queries_total= */ n_total, /* n_queries_1h= */ n_1h, /* cache_hit_rate_t1= */ ((t1_rate as f64) * 10f64.powi(4)).round() / 10f64.powi(4), /* cache_hit_rate_t2= */ ((t2_rate as f64) * 10f64.powi(4)).round() / 10f64.powi(4), /* cache_hit_rate_total= */ ((total_rate as f64) * 10f64.powi(4)).round() / 10f64.powi(4), /* avg_latency_s= */ ((avg_lat as f64) * 10f64.powi(3)).round() / 10f64.powi(3), /* p50_latency_s= */ ((p50 as f64) * 10f64.powi(3)).round() / 10f64.powi(3), /* p95_latency_s= */ ((p95 as f64) * 10f64.powi(3)).round() / 10f64.powi(3), /* hallucination_rate= */ ((hal_rate as f64) * 10f64.powi(4)).round() / 10f64.powi(4), /* total_chunks_indexed= */ self._total_chunks_indexed, /* avg_indexing_throughput= */ ((total_throughput as f64) * 10f64.powi(1)).round() / 10f64.powi(1), /* uptime_s= */ (((now - self._start_time) as f64) * 10f64.powi(0)).round() / 10f64.powi(0), /* last_query_at= */ last_query_at)
    }
    /// Return (minute_bucket, count) pairs for the last N minutes.
    pub fn get_query_timeline(&mut self, last_n_minutes: i64) -> Vec<(String, i64)> {
        // Return (minute_bucket, count) pairs for the last N minutes.
        let _ctx = self._lock;
        {
            let mut events = self._query_history.into_iter().collect::<Vec<_>>();
        }
        let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        let mut cutoff = (now - (last_n_minutes * 60));
        let mut relevant = events.iter().filter(|e| e.timestamp >= cutoff).map(|e| e).collect::<Vec<_>>();
        let mut buckets = HashMap::new();
        for e in relevant.iter() {
            let mut minute = datetime::fromtimestamp(e.timestamp).strftime("%H:%M".to_string());
            buckets[minute] = (buckets.get(&minute).cloned().unwrap_or(0) + 1);
        }
        { let mut v = buckets.iter().clone(); v.sort(); v }
    }
    /// Group latencies into buckets for histogram display.
    pub fn get_latency_histogram(&mut self) -> HashMap<String, i64> {
        // Group latencies into buckets for histogram display.
        let _ctx = self._lock;
        {
            let mut latencies = self._query_history.iter().map(|e| e.latency_s).collect::<Vec<_>>();
        }
        let mut buckets = HashMap::from([("<0.1s".to_string(), 0), ("0.1-0.5s".to_string(), 0), ("0.5-1s".to_string(), 0), ("1-2s".to_string(), 0), ("2-5s".to_string(), 0), (">5s".to_string(), 0)]);
        for lat in latencies.iter() {
            if lat < 0.1_f64 {
                buckets["<0.1s".to_string()] += 1;
            } else if lat < 0.5_f64 {
                buckets["0.1-0.5s".to_string()] += 1;
            } else if lat < 1.0_f64 {
                buckets["0.5-1s".to_string()] += 1;
            } else if lat < 2.0_f64 {
                buckets["1-2s".to_string()] += 1;
            } else if lat < 5.0_f64 {
                buckets["2-5s".to_string()] += 1;
            } else {
                buckets[">5s".to_string()] += 1;
            }
        }
        buckets
    }
    /// Clear all metrics history.
    pub fn reset(&mut self) -> () {
        // Clear all metrics history.
        let _ctx = self._lock;
        {
            self._query_history.clear();
            self._index_history.clear();
            self._total_chunks_indexed = 0;
            self._start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        }
    }
}
