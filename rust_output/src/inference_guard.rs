/// Core/inference_guard::py — Inference crash diagnostics & performance profiling.
/// 
/// Wraps every LLM inference call with:
/// - Memory snapshots (RSS, VMS, GPU, system) before + after
/// - Wall-clock + per-phase timing with named checkpoints
/// - Crash classification (MEMORY, FIFO, THREAD, TIMEOUT, LLAMA_CPP, etc.)
/// - Request profiling ring buffer (last N successful calls)
/// - Crash history ring buffer (last N failures)
/// - Aggregate stats (timing, memory deltas)
/// 
/// Architecture:
/// GuardMetrics     — all counters/aggregates in one class
/// MemorySnapshot   — one-shot RSS/VMS/GPU/system capture
/// CrashReport      — structured diagnostic with auto-classify
/// InferenceGuard   — async context manager wrapping any inference call
/// Decorators       — inference_guard(), inference_guard_generator()
/// 
/// This module is the ONLY place that tracks timing, memory, and crash data.
/// Ported from ZEN_RAG.

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _METRICS: std::sync::LazyLock<GuardMetrics> = std::sync::LazyLock::new(|| Default::default());

/// Thread-safe aggregate metrics for all guarded inference calls.
#[derive(Debug, Clone)]
pub struct GuardMetrics {
    pub _lock: std::sync::Mutex<()>,
    pub total_guarded_calls: i64,
    pub total_crashes: i64,
    pub total_inference_ms: f64,
    pub fastest_ms: f64,
    pub slowest_ms: f64,
    pub total_rss_delta_mb: f64,
    pub max_rss_delta_mb: f64,
    pub _crash_history: Deque<HashMap<String, Box<dyn std::any::Any>>>,
    pub _request_profiles: Deque<HashMap<String, Box<dyn std::any::Any>>>,
}

impl GuardMetrics {
    pub fn new(max_crashes: i64, max_profiles: i64) -> Self {
        Self {
            _lock: std::sync::Mutex::new(()),
            total_guarded_calls: 0,
            total_crashes: 0,
            total_inference_ms: 0.0,
            fastest_ms: 0.0,
            slowest_ms: 0.0,
            total_rss_delta_mb: 0.0,
            max_rss_delta_mb: 0.0,
            _crash_history: Default::default(),
            _request_profiles: Default::default(),
        }
    }
    pub fn record_call(&mut self) -> () {
        let _ctx = self._lock;
        {
            self.total_guarded_calls += 1;
        }
    }
    pub fn record_success(&mut self, elapsed_ms: f64, rss_delta_mb: f64, profile: HashMap<String, Box<dyn std::any::Any>>) -> () {
        let _ctx = self._lock;
        {
            self.total_inference_ms += elapsed_ms;
            if elapsed_ms < self.fastest_ms {
                self.fastest_ms = elapsed_ms;
            }
            if elapsed_ms > self.slowest_ms {
                self.slowest_ms = elapsed_ms;
            }
            self.total_rss_delta_mb += (rss_delta_mb).abs();
            if (rss_delta_mb).abs() > self.max_rss_delta_mb {
                self.max_rss_delta_mb = (rss_delta_mb).abs();
            }
            self._request_profiles.push(profile);
        }
    }
    pub fn record_crash(&mut self, report_dict: HashMap<String, Box<dyn std::any::Any>>) -> () {
        let _ctx = self._lock;
        {
            self.total_crashes += 1;
            self._crash_history.push(report_dict);
        }
    }
    pub fn get_crash_history(&self) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        let _ctx = self._lock;
        {
            self._crash_history.iter().rev().into_iter().collect::<Vec<_>>()
        }
    }
    pub fn get_request_profiles(&mut self, last_n: i64) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        let _ctx = self._lock;
        {
            let mut items = self._request_profiles.iter().rev().into_iter().collect::<Vec<_>>();
            items[..last_n]
        }
    }
    pub fn get_stats(&mut self) -> HashMap<String, Box<dyn std::any::Any>> {
        let _ctx = self._lock;
        {
            let mut n = self.total_guarded_calls;
            let mut avg_ms = if n > 0 { (self.total_inference_ms / n) } else { 0 };
            HashMap::from([("total_guarded_calls".to_string(), n), ("total_crashes".to_string(), self.total_crashes), ("crash_rate".to_string(), if n > 0 { format!("{:.2}%", ((self.total_crashes / n) * 100)) } else { "0%".to_string() }), ("crashes_in_history".to_string(), self._crash_history.len()), ("profiles_in_history".to_string(), self._request_profiles.len()), ("timing".to_string(), HashMap::from([("avg_ms".to_string(), ((avg_ms as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("fastest_ms".to_string(), if self.fastest_ms != "inf".to_string().to_string().parse::<f64>().unwrap_or(0.0) { ((self.fastest_ms as f64) * 10f64.powi(1)).round() / 10f64.powi(1) } else { None }), ("slowest_ms".to_string(), ((self.slowest_ms as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("total_ms".to_string(), ((self.total_inference_ms as f64) * 10f64.powi(1)).round() / 10f64.powi(1))])), ("memory".to_string(), HashMap::from([("total_rss_delta_mb".to_string(), ((self.total_rss_delta_mb as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("max_rss_delta_mb".to_string(), ((self.max_rss_delta_mb as f64) * 10f64.powi(1)).round() / 10f64.powi(1))]))])
        }
    }
}

/// Capture process + system memory at a point in time.
#[derive(Debug, Clone)]
pub struct MemorySnapshot {
    pub timestamp: String /* time::time */,
    pub rss_mb: round,
    pub vms_mb: round,
    pub percent: round,
    pub sys_total_mb: round,
    pub sys_available_mb: round,
    pub sys_percent: String,
    pub gpu_mb: _get_gpu_memory_mb,
}

impl MemorySnapshot {
    pub fn new() -> Self {
        Self {
            timestamp: std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64(),
            rss_mb: (((mem.rss / (1024).pow(2 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1),
            vms_mb: (((mem.vms / (1024).pow(2 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1),
            percent: ((proc.memory_percent() as f64) * 10f64.powi(2)).round() / 10f64.powi(2),
            sys_total_mb: (((sysmem.total / (1024).pow(2 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1),
            sys_available_mb: (((sysmem.available / (1024).pow(2 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1),
            sys_percent: sysmem.percent,
            gpu_mb: _get_gpu_memory_mb(),
        }
    }
    pub fn to_dict(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        HashMap::from([("rss_mb".to_string(), self.rss_mb), ("vms_mb".to_string(), self.vms_mb), ("process_percent".to_string(), self.percent), ("system_total_mb".to_string(), self.sys_total_mb), ("system_available_mb".to_string(), self.sys_available_mb), ("system_percent".to_string(), self.sys_percent), ("gpu_allocated_mb".to_string(), self.gpu_mb)])
    }
    pub fn delta(&self, other: String) -> HashMap<String, f64> {
        HashMap::from([("rss_delta_mb".to_string(), (((self.rss_mb - other.rss_mb) as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("vms_delta_mb".to_string(), (((self.vms_mb - other.vms_mb) as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("sys_available_delta_mb".to_string(), (((self.sys_available_mb - other.sys_available_mb) as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("gpu_delta_mb".to_string(), if (self.gpu_mb.is_some() && other.gpu_mb.is_some()) { (((self.gpu_mb - other.gpu_mb) as f64) * 10f64.powi(1)).round() / 10f64.powi(1) } else { None })])
    }
}

/// Full diagnostic report when inference fails.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrashReport {
    pub operation: String,
    pub error_type: String,
    pub error_message: String,
    pub traceback: String,
    pub timestamp: f64,
    pub phase: String,
    pub elapsed_seconds: f64,
    pub checkpoints: HashMap<String, f64>,
    pub memory_before: Option<HashMap>,
    pub memory_after: Option<HashMap>,
    pub memory_delta: Option<HashMap>,
    pub fifo_state: Option<HashMap>,
    pub llm_state: Option<HashMap>,
    pub thread_state: Option<HashMap>,
    pub request_info: Option<HashMap>,
    pub likely_cause: String,
}

impl CrashReport {
    pub fn to_dict(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        asdict(self)
    }
    /// Auto-classify the likely cause based on error text + memory evidence.
    pub fn classify(&mut self) -> () {
        // Auto-classify the likely cause based on error text + memory evidence.
        let mut err = self.error_message.to_lowercase();
        let mut etype = self.error_type.to_lowercase();
        if ("memory".to_string(), "oom".to_string(), "alloc".to_string(), "mmap".to_string(), "out of memory".to_string(), "cuda_error".to_string()).iter().map(|w| err.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            self.likely_cause = "MEMORY: Out of memory (RAM or GPU)".to_string();
            return;
        }
        if self.memory_after {
            let mut sys_pct = self.memory_after.get(&"system_percent".to_string()).cloned().unwrap_or(0);
            if sys_pct > 95 {
                self.likely_cause = format!("MEMORY: System memory at {}% — OS may have killed the process", sys_pct);
                return;
            }
        }
        if self.memory_delta {
            let mut rss_delta = self.memory_delta.get(&"rss_delta_mb".to_string()).cloned().unwrap_or(0);
            if (rss_delta && rss_delta > 2000) {
                self.likely_cause = format!("MEMORY: RSS grew {:.0} MB during inference — likely context overflow or repeated allocation", rss_delta);
                return;
            }
        }
        if ("fifo".to_string(), "buffer".to_string(), "queue".to_string(), "timeout".to_string(), "backpressure".to_string()).iter().map(|w| err.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            self.likely_cause = "FIFO: Buffer overflow or timeout".to_string();
            return;
        }
        if ("deadlock".to_string(), "lock".to_string(), "semaphore".to_string(), "thread".to_string()).iter().map(|w| err.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            self.likely_cause = "THREAD: Deadlock or lock contention".to_string();
            return;
        }
        if (err.contains(&"timeout".to_string()) || err.contains(&"timed out".to_string())) {
            self.likely_cause = if self.elapsed_seconds > 30 { format!("TIMEOUT: Inference took {:.1}s", self.elapsed_seconds) } else { "TIMEOUT: Operation timed out".to_string() };
            return;
        }
        if ("llama".to_string(), "gguf".to_string(), "ggml".to_string(), "segfault".to_string(), "access violation".to_string()).iter().map(|w| err.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            self.likely_cause = "LLAMA_CPP: Internal engine error".to_string();
            return;
        }
        if ("connection".to_string(), "broken pipe".to_string(), "reset".to_string(), "refused".to_string()).iter().map(|w| err.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            self.likely_cause = "CRASH: Server process died during inference".to_string();
            return;
        }
        if ("context".to_string(), "n_ctx".to_string(), "too many tokens".to_string(), "exceeds".to_string()).iter().map(|w| err.contains(&w)).collect::<Vec<_>>().iter().any(|v| *v) {
            self.likely_cause = "CONTEXT: Prompt exceeds model context window".to_string();
            return;
        }
        if self.elapsed_seconds > 60 {
            self.likely_cause = format!("SLOW: Inference took {:.1}s — may need smaller max_tokens or model", self.elapsed_seconds);
        } else {
            self.likely_cause = format!("UNKNOWN: {}", etype);
        }
    }
}

/// Wrap inference with full crash diagnostics and performance profiling.
/// 
/// Usage:
/// async with InferenceGuard("streaming", adapter=adapter) as guard:
/// guard.mark("tokens_started")
/// async for token in stream_tokens(...):
/// yield token
/// guard.mark("tokens_done")
#[derive(Debug, Clone)]
pub struct InferenceGuard {
    pub operation: String,
    pub adapter: String,
    pub request_info: String,
    pub start_time: Option<f64>,
    pub mem_before: Option<MemorySnapshot>,
    pub checkpoints: HashMap<String, f64>,
    pub _phase: String,
}

impl InferenceGuard {
    pub fn new(operation: String) -> Self {
        Self {
            operation,
            adapter: adapter,
            request_info: (request_info || HashMap::new()),
            start_time: None,
            mem_before: None,
            checkpoints: HashMap::new(),
            _phase: "pre_inference".to_string(),
        }
    }
    pub fn set_request_info(&mut self, info: HashMap<String, Box<dyn std::any::Any>>) -> () {
        self.request_info = info;
    }
    pub fn mark(&mut self, name: String) -> () {
        if self.start_time {
            self.checkpoints[name] = (((std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - self.start_time) as f64) * 10f64.powi(4)).round() / 10f64.powi(4);
        }
    }
    pub fn phase(&mut self, name: String) -> () {
        self._phase = name;
    }
    pub async fn __aenter__(&mut self) -> () {
        _metrics.record_call();
        self.start_time = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        self.mem_before = MemorySnapshot();
        self._phase = "inference".to_string();
        self
    }
    pub async fn __aexit__(&mut self, exc_type: String, exc_val: String, exc_tb: String) -> () {
        let mut elapsed = if self.start_time { (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - self.start_time) } else { 0 };
        if exc_type.is_none() {
            self._handle_success(elapsed);
        } else {
            self._handle_crash(elapsed, exc_type, exc_val);
        }
        false
    }
    pub fn _handle_success(&mut self, elapsed: f64) -> () {
        let mut mem_after = MemorySnapshot();
        let mut delta = mem_after.delta(self.mem_before);
        let mut rss_delta = delta.get(&"rss_delta_mb".to_string()).cloned().unwrap_or(0);
        let mut elapsed_ms = (elapsed * 1000);
        let mut profile = HashMap::from([("operation".to_string(), self.operation), ("status".to_string(), "ok".to_string()), ("elapsed_ms".to_string(), ((elapsed_ms as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("checkpoints".to_string(), self.checkpoints.clone()), ("memory_before".to_string(), HashMap::from([("rss_mb".to_string(), self.mem_before.rss_mb), ("sys_percent".to_string(), self.mem_before.sys_percent)])), ("memory_after".to_string(), HashMap::from([("rss_mb".to_string(), mem_after.rss_mb), ("sys_percent".to_string(), mem_after.sys_percent), ("gpu_mb".to_string(), mem_after.gpu_mb)])), ("memory_delta".to_string(), delta), ("request_info".to_string(), _sanitize_request_info(self.request_info)), ("timestamp".to_string(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64())]);
        if self.adapter {
            let mut fifo = _get_fifo_state(self.adapter);
            if fifo {
                profile["fifo_state".to_string()] = fifo;
            }
            let mut llm = _get_llm_state(self.adapter);
            if llm {
                profile["llm_state".to_string()] = llm;
            }
        }
        _metrics.record_success(elapsed_ms, rss_delta, profile);
        if (rss_delta).abs() > 100 {
            logger.warning("[InferenceGuard] %s OK in %.2fs but RSS changed %+.0f MB (now %.0f MB)".to_string(), self.operation, elapsed, rss_delta, mem_after.rss_mb);
        } else {
            logger.info("[InferenceGuard] %s OK in %.2fs RSS: %.0f -> %.0f MB (d%+.0f) | sys: %s%%".to_string(), self.operation, elapsed, self.mem_before.rss_mb, mem_after.rss_mb, rss_delta, mem_after.sys_percent);
        }
    }
    pub fn _handle_crash(&mut self, elapsed: f64, exc_type: String, exc_val: String) -> () {
        let mut mem_after = MemorySnapshot();
        let mut report = CrashReport(/* operation= */ self.operation, /* error_type= */ exc_type.module_path!(), /* error_message= */ exc_val.to_string(), /* traceback= */ traceback.format_exc(), /* phase= */ self._phase, /* elapsed_seconds= */ ((elapsed as f64) * 10f64.powi(3)).round() / 10f64.powi(3), /* checkpoints= */ self.checkpoints.clone(), /* memory_before= */ self.mem_before.to_dict(), /* memory_after= */ mem_after.to_dict(), /* memory_delta= */ mem_after.delta(self.mem_before), /* fifo_state= */ if self.adapter { _get_fifo_state(self.adapter) } else { None }, /* llm_state= */ if self.adapter { _get_llm_state(self.adapter) } else { None }, /* thread_state= */ _get_thread_state(), /* request_info= */ _sanitize_request_info(self.request_info));
        report.classify();
        _metrics.record_crash(report.to_dict());
        logger.error("\n%s\nINFERENCE CRASH — %s\n%s\n  Operation:  %s\n  Phase:      %s\n  Error:      %s: %s\n  Elapsed:    %.3fs\n  Memory:     RSS %.0f -> %.0f MB (d%+.0f MB)\n  System:     %s%% used (%.0f MB free)\n  GPU:        %s MB\n  Threads:    %s active\n%s".to_string(), ("=".to_string() * 70), report.likely_cause, ("=".to_string() * 70), report.operation, report.phase, report.error_type, report.error_message, report.elapsed_seconds, self.mem_before.rss_mb, mem_after.rss_mb, report.memory_delta["rss_delta_mb".to_string()], mem_after.sys_percent, mem_after.sys_available_mb, (mem_after.gpu_mb || "N/A".to_string()), report.thread_state["active_count".to_string()], ("=".to_string() * 70));
    }
}

/// Return the last N crash reports (newest first).
pub fn get_crash_history() -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
    // Return the last N crash reports (newest first).
    _metrics.get_crash_history()
}

/// Return the last N successful request profiles (newest first).
pub fn get_request_profiles(last_n: i64) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
    // Return the last N successful request profiles (newest first).
    _metrics.get_request_profiles(last_n)
}

/// Global inference guard statistics with timing + memory aggregates.
pub fn get_guard_stats() -> HashMap<String, Box<dyn std::any::Any>> {
    // Global inference guard statistics with timing + memory aggregates.
    _metrics.get_stats()
}

/// Try to get GPU memory usage (PyTorch CUDA -> nvidia-smi fallback).
pub fn _get_gpu_memory_mb() -> Result<Option<f64>> {
    // Try to get GPU memory usage (PyTorch CUDA -> nvidia-smi fallback).
    // try:
    {
        // TODO: import torch
        if torch.cuda.is_available() {
            (((torch.cuda.memory_allocated() / (1024).pow(2 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1)
        }
    }
    // except Exception as _e:
    // try:
    {
        // TODO: import subprocess
        let mut result = std::process::Command::new("sh").arg("-c").arg(vec!["nvidia-smi".to_string().output().unwrap(), "--query-gpu=memory.used".to_string(), "--format=csv,nounits,noheader".to_string()], /* capture_output= */ true, /* text= */ true, /* timeout= */ 3, /* shell= */ false);
        if (result.returncode == 0 && result.stdout.trim().to_string()) {
            result.stdout.trim().to_string().split("\n".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0].to_string().parse::<f64>().unwrap_or(0.0)
        }
    }
    // except Exception as _e:
    Ok(None)
}

/// Quick process+system memory dict for use by endpoints.
pub fn get_memory_snapshot() -> HashMap<String, Box<dyn std::any::Any>> {
    // Quick process+system memory dict for use by endpoints.
    let mut proc = psutil.Process(os::getpid());
    let mut mem = proc.memory_info();
    let mut sysmem = psutil.virtual_memory();
    HashMap::from([("process_rss_mb".to_string(), (((mem.rss / (1024).pow(2 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("process_vms_mb".to_string(), (((mem.vms / (1024).pow(2 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("process_percent".to_string(), ((proc.memory_percent() as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("system_total_mb".to_string(), (((sysmem.total / (1024).pow(2 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("system_available_mb".to_string(), (((sysmem.available / (1024).pow(2 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("system_percent".to_string(), sysmem.percent)])
}

pub fn _get_fifo_state(adapter: String) -> Result<Option<HashMap<String, Box<dyn std::any::Any>>>> {
    // try:
    {
        let mut inner = /* getattr */ adapter;
        if /* hasattr(inner, "get_stats".to_string()) */ true {
            inner.get_stats()
        }
        let mut result = HashMap::new();
        for attr_name in ("request_buffer".to_string(), "response_buffer".to_string()).iter() {
            let mut buf = /* getattr */ None;
            if (buf && /* hasattr(buf, "stats".to_string()) */ true) {
                result[attr_name] = buf.stats();
            }
        }
        if result { result } else { None }
    }
    // except Exception as e:
}

pub fn _get_llm_state(adapter: String) -> Result<Option<HashMap<String, Box<dyn std::any::Any>>>> {
    // try:
    {
        let mut inner = /* getattr */ adapter;
        let mut llm = /* getattr */ /* getattr */ None;
        if llm.is_none() {
            HashMap::from([("model_loaded".to_string(), false)])
        }
        let mut info = HashMap::from([("model_loaded".to_string(), true)]);
        if /* hasattr(llm, "n_ctx".to_string()) */ true {
            info["n_ctx".to_string()] = llm.n_ctx();
        }
        if /* hasattr(llm, "n_tokens".to_string()) */ true {
            info["n_tokens_used".to_string()] = llm.n_tokens();
        }
        let mut model_path = /* getattr */ /* getattr */ None;
        if model_path {
            let mut p = PathBuf::from(model_path);
            info["model_file".to_string()] = p.name;
            if p.exists() {
                info["model_size_gb".to_string()] = (((p.stat().st_size / (1024).pow(3 as u32)) as f64) * 10f64.powi(2)).round() / 10f64.powi(2);
            }
        }
        info
    }
    // except Exception as e:
}

pub fn _get_thread_state() -> HashMap<String, Box<dyn std::any::Any>> {
    let mut threads = threading::enumerate();
    HashMap::from([("active_count".to_string(), threads.len()), ("names".to_string(), threads[..20].iter().map(|t| t.name).collect::<Vec<_>>()), ("daemon_count".to_string(), threads.iter().filter(|t| t.daemon).map(|t| 1).collect::<Vec<_>>().iter().sum::<i64>())])
}

/// Remove sensitive data, truncate prompts for storage.
pub fn _sanitize_request_info(info: HashMap<String, Box<dyn std::any::Any>>) -> HashMap<String, Box<dyn std::any::Any>> {
    // Remove sensitive data, truncate prompts for storage.
    let mut sanitized = HashMap::new();
    for (k, v) in info.iter().iter() {
        if ("prompt".to_string(), "content".to_string(), "messages".to_string()).contains(&k) {
            if /* /* isinstance(v, str) */ */ true {
                sanitized[k] = if v.len() > 200 { (v[..200] + "...".to_string()) } else { v };
                sanitized[format!("{}_length", k)] = v.len();
            } else if /* /* isinstance(v, list) */ */ true {
                sanitized[format!("{}_count", k)] = v.len();
                sanitized[k] = v[..10].iter().map(|m| HashMap::from([("role".to_string(), m.get(&"role".to_string()).cloned().unwrap_or("?".to_string())), ("content_len".to_string(), m.get(&"content".to_string()).cloned().unwrap_or("".to_string()).len())])).collect::<Vec<_>>();
            } else {
                sanitized[k] = v.to_string()[..100];
            }
        } else {
            sanitized[k] = v;
        }
    }
    sanitized
}

/// Decorator wrapping an async function with crash diagnostics.
pub fn inference_guard(operation: String) -> () {
    // Decorator wrapping an async function with crash diagnostics.
    let decorator = |fn| {
        let wrapper = || {
            let mut adapter = if get_adapter { get_adapter() } else { None };
            let _ctx = InferenceGuard(operation, /* adapter= */ adapter);
            {
                r#fn(/* *args */, /* ** */ kwargs).await
            }
        };
        wrapper
    };
    decorator
}

/// Decorator for async generators (streaming endpoints).
pub fn inference_guard_generator(operation: String) -> Result<()> {
    // Decorator for async generators (streaming endpoints).
    let decorator = |fn| {
        let wrapper = || {
            let mut adapter = if get_adapter { get_adapter() } else { None };
            let mut guard = InferenceGuard(operation, /* adapter= */ adapter);
            guard.__aenter__().await;
            // try:
            {
                // async for
                while let Some(item) = r#fn(/* *args */, /* ** */ kwargs).next().await {
                    /* yield item */;
                }
                guard.__aexit__(None, None, None).await;
            }
            // except BaseException as _e:
        };
        wrapper
    };
    Ok(decorator)
}
