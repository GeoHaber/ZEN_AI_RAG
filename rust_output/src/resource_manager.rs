/// resource_manager::py - Dynamic Resource Management for ZenAI V2
/// Monitors system RAM and determines model loading strategies to prevent crashes.

use anyhow::{Result, Context};
use crate::config_system::{config};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static RESOURCE_MANAGER: std::sync::LazyLock<ResourceManager> = std::sync::LazyLock::new(|| Default::default());

/// Monitors system resources and delegates loading strategies.
/// 
/// Strategies:
/// - SERIAL: Unload current -> Load new (Safe, Slow). Used when RAM < 8GB.
/// - SWAP: Keep Orchestrator, swap Experts. Used for 8-16GB RAM.
/// - PARALLEL: Keep Orchestrator + Expert loaded. Used for > 16GB RAM.
#[derive(Debug, Clone)]
pub struct ResourceManager {
    pub strategy: Literal<serde_json::Value>,
    pub total_ram_gb: i64,
    pub available_ram_gb: i64,
    pub _worker_threads: Vec<threading::Thread>,
    pub _threads_lock: std::sync::Mutex<()>,
}

impl ResourceManager {
    /// Initialize instance.
    pub fn new() -> Self {
        Self {
            strategy: Default::default(),
            total_ram_gb: 0,
            available_ram_gb: 0,
            _worker_threads: Vec::new(),
            _threads_lock: std::sync::Mutex::new(()),
        }
    }
    /// Start and register a background thread, optionally enforcing a max worker count.
    /// 
    /// Returns the Thread object.
    pub fn add_worker_thread(&mut self, target: String, args: String, daemon: String, max_workers: Option<i64>) -> Result<()> {
        // Start and register a background thread, optionally enforcing a max worker count.
        // 
        // Returns the Thread object.
        if max_workers.is_some() { max_workers } else { /* getattr */ 4 };
        let mut t = std::thread::spawn(|| {});
        let _ctx = self._threads_lock;
        {
            self._worker_threads.push(t);
            if max_workers.is_some() {
                self.cleanup_finished_threads();
                if self._worker_threads.len() >= max_workers {
                    return Err(anyhow::anyhow!("RuntimeError('Max worker threads reached')"));
                }
            }
        }
        t.start();
        Ok(t)
    }
    /// Remove finished worker threads from internal registry.
    pub fn cleanup_finished_threads(&mut self) -> () {
        // Remove finished worker threads from internal registry.
        let _ctx = self._threads_lock;
        {
            self._worker_threads = self._worker_threads.iter().filter(|t| t.is_alive()).map(|t| t).collect::<Vec<_>>();
        }
    }
    pub fn get_worker_count(&self) -> i64 {
        let _ctx = self._threads_lock;
        {
            self.cleanup_finished_threads();
            self._worker_threads.len()
        }
    }
    /// Run `func(*args)` in a background thread, return an asyncio.Future tied to the current loop.
    /// 
    /// The thread is tracked in the internal registry so cleanup can prune finished threads.
    /// Raises RuntimeError if max_workers would be exceeded.
    pub fn run_in_thread_future(&mut self, func: String, args: Vec<Box<dyn std::any::Any>>) -> Result<()> {
        // Run `func(*args)` in a background thread, return an asyncio.Future tied to the current loop.
        // 
        // The thread is tracked in the internal registry so cleanup can prune finished threads.
        // Raises RuntimeError if max_workers would be exceeded.
        // try:
        {
            let mut r#loop = asyncio.get_running_loop();
        }
        // except RuntimeError as _e:
        let mut fut = r#loop.create_future();
        let _target = || {
            // try:
            {
                let mut res = func(/* *args */);
            }
            // except Exception as e:
            r#loop.call_soon_threadsafe(fut.set_result, res);
        };
        let mut effective_max = if max_workers.is_some() { max_workers } else { /* getattr */ 4 };
        let mut t = std::thread::spawn(|| {});
        let _ctx = self._threads_lock;
        {
            self._worker_threads.push(t);
            if effective_max.is_some() {
                self.cleanup_finished_threads();
                if self._worker_threads.len() > effective_max {
                    self._worker_threads.pop().unwrap();
                    return Err(anyhow::anyhow!("RuntimeError('Max worker threads reached')"));
                }
            }
        }
        t.start();
        Ok(fut)
    }
    /// Update current memory stats.
    pub fn _refresh_stats(&mut self) -> () {
        // Update current memory stats.
        if PSUTIL_AVAILABLE {
            let mut mem = psutil.virtual_memory();
            self.total_ram_gb = (mem.total / (1024).pow(3 as u32));
            self.available_ram_gb = (mem.available / (1024).pow(3 as u32));
        } else {
            self.total_ram_gb = 8.0_f64;
            self.available_ram_gb = 4.0_f64;
        }
    }
    /// Calculate best strategy based on Total RAM.
    pub fn _determine_strategy(&mut self) -> () {
        // Calculate best strategy based on Total RAM.
        if self.total_ram_gb < 8.5_f64 {
            self.strategy = "SERIAL".to_string();
        } else if self.total_ram_gb < 16.5_f64 {
            self.strategy = "SWAP".to_string();
        } else {
            self.strategy = "PARALLEL".to_string();
        }
        logger.info(format!("[ResourceManager] Strategy: {} (Total: {:.1}GB, Avail: {:.1}GB)", self.strategy, self.total_ram_gb, self.available_ram_gb));
    }
    /// Check if we have enough RAM to load a model of size_gb.
    pub fn can_load_model(&mut self, model_size_gb: f64) -> bool {
        // Check if we have enough RAM to load a model of size_gb.
        self._refresh_stats();
        let mut safe_margin = 2.0_f64;
        self.available_ram_gb > (model_size_gb + safe_margin)
    }
    /// Return current status for UI.
    pub fn get_status(&self) -> HashMap {
        // Return current status for UI.
        self._refresh_stats();
        HashMap::from([("strategy".to_string(), self.strategy), ("total_ram".to_string(), format!("{:.1} GB", self.total_ram_gb)), ("available_ram".to_string(), format!("{:.1} GB", self.available_ram_gb)), ("psutil".to_string(), PSUTIL_AVAILABLE)])
    }
}
