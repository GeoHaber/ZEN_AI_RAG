use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static MONITOR: std::sync::LazyLock<PerformanceMonitor> = std::sync::LazyLock::new(|| Default::default());

/// Singleton class to track and hold performance metrics.
#[derive(Debug, Clone)]
pub struct PerformanceMonitor {
}

impl PerformanceMonitor {
    /// New.
    pub fn __new__(&self, cls: String) -> () {
        // New.
        if cls._instance.is_some() {
            return;
        }
        cls._instance = r#super(PerformanceMonitor, cls).__new__(cls);
        cls._instance.metrics = HashMap::from([("llm_tps".to_string(), deque(/* maxlen= */ 50)), ("llm_ttft".to_string(), deque(/* maxlen= */ 50)), ("rag_retrieval".to_string(), deque(/* maxlen= */ 50)), ("expert_latency".to_string(), deque(/* maxlen= */ 50)), ("traces".to_string(), HashMap::new())]);
        cls._instance
    }
    /// Generates a new trace ID for a request batch.
    pub fn start_trace(&mut self) -> String {
        // Generates a new trace ID for a request batch.
        let mut trace_id = /* uuid */ "00000000-0000-0000-0000-000000000000".to_string().to_string()[..8];
        self.metrics["traces".to_string()][trace_id] = vec![];
        trace_id
    }
    /// Append a message to a specific trace.
    pub fn log_trace(&self, trace_id: String, message: String) -> () {
        // Append a message to a specific trace.
        if !self.metrics["traces".to_string()].contains(&trace_id) {
            return;
        }
        self.metrics["traces".to_string()][&trace_id].push(format!("[{}] {}", time::strftime("%H:%M:%S".to_string()), message));
        logger.debug(format!("[Trace:{}] {}", trace_id, message));
    }
    pub fn add_metric(&self, key: String, value: f64) -> () {
        if !self.metrics.contains(&key) {
            return;
        }
        self.metrics[&key].push(value);
        logger.debug(format!("[Metric] {}: {:.2}", key, value));
    }
    pub fn get_averages(&self) -> () {
        self.metrics.iter().iter().map(|(k, v)| (k, if v { (v.iter().sum::<i64>() / v.len()) } else { 0 })).collect::<HashMap<_, _>>()
    }
}

/// Decorator to measure execution time of a function.
/// Automatically logs results to PerformanceMonitor.
pub fn profile_execution(name: String) -> () {
    // Decorator to measure execution time of a function.
    // Automatically logs results to PerformanceMonitor.
    let decorator = |func| {
        // Decorator.
        let wrapper = || {
            // Wrapper.
            let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            let mut result = func(/* *args */, /* ** */ kwargs);
            let mut duration_ms = ((std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start) * 1000);
            if name.to_lowercase().contains(&"rag".to_string()) {
                monitor.add_metric("rag_retrieval".to_string(), duration_ms);
            } else if name.to_lowercase().contains(&"expert".to_string()) {
                monitor.add_metric("expert_latency".to_string(), duration_ms);
            }
            logger.info(format!("[Profiler] {} took {:.1}ms", name, duration_ms));
            result
        };
        wrapper
    };
    decorator
}

/// Async version of the execution profiler.
pub fn profile_async_execution(name: String) -> () {
    // Async version of the execution profiler.
    let decorator = |func| {
        // Decorator.
        let wrapper = || {
            // Wrapper.
            let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
            let mut result = func(/* *args */, /* ** */ kwargs).await;
            let mut duration_ms = ((std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start) * 1000);
            if name.to_lowercase().contains(&"rag".to_string()) {
                monitor.add_metric("rag_retrieval".to_string(), duration_ms);
            }
            logger.info(format!("[Profiler] {} took {:.1}ms", name, duration_ms));
            result
        };
        wrapper
    };
    decorator
}
