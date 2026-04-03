/// heart_and_brain::py - The Core Logic of ZenAI
/// ============================================
/// The "Heart" manages the Engine's pulse (Life, Restart, Recovery).
/// The "Brain" manages the Model's logic (Paths, Swarm, Experts).

use anyhow::{Result, Context};
use crate::config_system::{config, EMOJI};
use crate::resource_detect::{HardwareProfiler};
use crate::utils::{safe_print, is_port_active, wait_for_port, ProcessManager};
use std::collections::HashMap;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static ZEN_HEART: std::sync::LazyLock<ZenHeart> = std::sync::LazyLock::new(|| Default::default());

pub static ZEN_BRAIN: std::sync::LazyLock<ZenBrain> = std::sync::LazyLock::new(|| Default::default());

/// Reads stdout from a subprocess in a non-blocking thread and logs it.
/// Prevents pipe buffer deadlocks on Windows.
/// Hardened: Uses chunk-based reading.
#[derive(Debug, Clone)]
pub struct LogRelay {
    pub process: String,
    pub prefix: String,
    pub chunk_size: String,
    pub _stop_event: std::sync::Condvar,
    pub last_lines: Vec<serde_json::Value>,
    pub buffer_lock: std::sync::Mutex<()>,
}

impl LogRelay {
    /// Initialize instance.
    pub fn new(process: String, prefix: String, chunk_size: String) -> Self {
        Self {
            process,
            prefix,
            chunk_size,
            _stop_event: /* Event */ (),
            last_lines: vec![],
            buffer_lock: std::sync::Mutex::new(()),
        }
    }
    /// Run.
    pub fn run(&mut self) -> Result<()> {
        // Run.
        // try:
        {
            while !self._stop_event.is_set() {
                if !self.process {
                    break;
                }
                // try:
                {
                    let mut chunk = self.process.stdout.read(1024);
                }
                // except (ValueError, AttributeError, OSError) as _e:
                if !chunk {
                    break;
                }
                // try:
                {
                    let mut text = chunk.decode("utf-8".to_string(), /* errors= */ "replace".to_string());
                    if text {
                        let _ctx = self.buffer_lock;
                        {
                            self.last_lines.push(text.trim().to_string());
                            if self.last_lines.len() > 20 {
                                self.last_lines.remove(&0);
                            }
                        }
                        safe_print(format!("{} {}", self.prefix, text));
                    }
                }
                // except Exception as _e:
            }
        }
        // except Exception as _e:
    }
}

/// The Heart of the system.
/// Responsibilities:
/// - Pump Life: Start/Stop the LLM Engine
/// - Pacemaker: Check Health & Auto-Restart
/// - Blood Pressure: Manage Hardware/VRAM
#[derive(Debug, Clone)]
pub struct ZenHeart {
    pub server_process: Option<subprocess::Popen>,
    pub server_relay: Option<LogRelay>,
    pub monitored_pids: HashMap<i64, String>,
    pub restart_count: i64,
    pub health_checks_failed: i64,
    pub stop_event: std::sync::Condvar,
}

impl ZenHeart {
    /// Initialize instance.
    pub fn new() -> Self {
        Self {
            server_process: None,
            server_relay: None,
            monitored_pids: HashMap::new(),
            restart_count: 0,
            health_checks_failed: 0,
            stop_event: /* Event */ (),
        }
    }
    /// The Main Life-Support Loop.
    /// Monitors the engine, restarts it if it dies, and reports health.
    /// Should be run in the main thread (blocking).
    pub fn pump(&mut self) -> Result<()> {
        // The Main Life-Support Loop.
        // Monitors the engine, restarts it if it dies, and reports health.
        // Should be run in the main thread (blocking).
        logger.info("[Heart] Pump started. Monitoring vitals...".to_string());
        let mut MAX_RESTARTS = 3;
        while !self.stop_event.is_set() {
            if self.server_process {
                let mut p_code = self.server_process.poll();
                if p_code.is_some() {
                    logger.warning(format!("[Heart] Engine flatlined (Exit Code: {})", p_code));
                    if (self.server_relay && self.server_relay.last_lines) {
                        safe_print((("\n".to_string() + ("🏁".to_string() * 15)) + "\n  ENGINE'S LAST WORDS:".to_string()));
                        for l in self.server_relay.last_lines.iter() {
                            safe_print(format!("  > {}", l));
                        }
                        safe_print((("🏁".to_string() * 15) + "\n".to_string()));
                    }
                    if self.restart_count < MAX_RESTARTS {
                        self.restart_count += 1;
                        safe_print(format!("{} Attempting resuscitation {}/{}...", EMOJI["recovery".to_string()], self.restart_count, MAX_RESTARTS));
                        std::thread::sleep(std::time::Duration::from_secs_f64(2));
                        // try:
                        {
                            self.ignite();
                            safe_print(format!("{} Resuscitation successful!", EMOJI["success".to_string()]));
                        }
                        // except Exception as e:
                    } else {
                        safe_print("💀 Brain death confirmed. Shutting down system.".to_string());
                        self.stop_event.set();
                        return;
                    }
                } else if !self.pacemaker() {
                    if self.health_checks_failed > 3 {
                        safe_print(format!("{} Engine detected as ZOMBIE (Unresponsive). Force killing...", EMOJI["warning".to_string()]));
                        self.flatline();
                    }
                }
            }
            std::thread::sleep(std::time::Duration::from_secs_f64(2));
        }
    }
    /// Active Health Probe (HTTP Check).
    pub fn pacemaker(&mut self) -> Result<bool> {
        // Active Health Probe (HTTP Check).
        if !self.server_process {
            false
        }
        // try:
        {
            let mut resp = /* reqwest::get( */&format!("http://127.0.0.1:{}/health", config::llm_port)).cloned().unwrap_or(/* timeout= */ 2);
            if resp.status_code == 200 {
                self.health_checks_failed = 0;
                true
            }
        }
        // except Exception as _e:
        self.health_checks_failed += 1;
        Ok(false)
    }
    /// Kill the engine (Process Death).
    pub fn flatline(&mut self) -> () {
        // Kill the engine (Process Death).
        if self.server_process {
            ProcessManager.kill_tree(self.server_process.pid);
            self.server_process = None;
        }
    }
    /// Build the llama-server command with hardware-tuned parameters.
    pub fn _build_engine_cmd() -> () {
        // Build the llama-server command with hardware-tuned parameters.
        let mut profile = HardwareProfiler.get_profile();
        config::host = "127.0.0.1".to_string();
        let mut gpu_layers = config::gpu_layers;
        if (profile["type".to_string()] == "NVIDIA".to_string() && config::gpu_layers == -1) {
            let mut safe_vram = 0.max((profile["free_vram_mb".to_string()] - 500));
            if safe_vram < 500 {
                let mut gpu_layers = 0;
            } else {
                let mut gpu_layers = 99.min((safe_vram / 120).to_string().parse::<i64>().unwrap_or(0));
            }
            safe_print(format!("{} Nvidia Governor: {}MB Free -> {} layers safe.", EMOJI["hardware".to_string()], profile["free_vram_mb".to_string()], gpu_layers));
        } else if (profile["type".to_string()] == "AMD".to_string() && config::gpu_layers == -1) {
            let mut safe_vram = (profile["vram_mb".to_string()] * 0.7_f64).to_string().parse::<i64>().unwrap_or(0);
            let mut gpu_layers = 0.max((safe_vram / 120).to_string().parse::<i64>().unwrap_or(0));
            safe_print(format!("{} AMD Governor: {}MB Total -> {} layers (est).", EMOJI["hardware".to_string()], profile["vram_mb".to_string()], gpu_layers));
        }
        let mut threads = 1.max((profile["threads".to_string()] - 1));
        let mut model_path = (config::MODEL_DIR / config::default_model);
        let mut cmd = vec![(config::BIN_DIR / "llama-server::exe".to_string()).to_string(), "--model".to_string(), model_path.to_string(), "--host".to_string(), config::host, "--port".to_string(), config::llm_port.to_string(), "--n-gpu-layers".to_string(), gpu_layers.to_string(), "--threads".to_string(), threads.to_string(), "--ctx-size".to_string(), config::context_size.to_string(), "--batch-size".to_string(), config::batch_size.to_string(), "--parallel".to_string(), /* getattr */ 1.to_string(), "--log-disable".to_string()];
        logger.info(format!("Igniting Engine: {}", cmd.join(&" ".to_string())));
        cmd
    }
    /// Start the llama-server engine with optimal hardware settings.
    pub fn ignite(&mut self) -> Result<()> {
        // Start the llama-server engine with optimal hardware settings.
        let mut cmd = self._build_engine_cmd();
        if is_port_active(config::llm_port) {
            ProcessManager.prune(/* ports= */ vec![config::llm_port], /* auto_confirm= */ true);
        }
        // try:
        {
            let mut creation_flags = if sys::platform == "win32".to_string() { (subprocess::CREATE_NEW_CONSOLE | subprocess::HIGH_PRIORITY_CLASS) } else { 0 };
            self.server_process = subprocess::Popen(cmd, /* stdout= */ subprocess::PIPE, /* stderr= */ subprocess::STDOUT, /* text= */ false, /* creationflags= */ creation_flags, /* shell= */ false);
            self.monitored_pids[self.server_process.pid] = "Llama Engine".to_string();
            self.server_relay = LogRelay(self.server_process);
            self.server_relay.start();
            safe_print(format!("{} Waiting for Engine to Ignite (Port {})...", EMOJI["rocket".to_string()], config::llm_port));
            wait_for_port(config::llm_port, /* timeout= */ 30);
            self.server_process
        }
        // except Exception as e:
    }
}

/// The Brain of the system.
/// Responsibilities:
/// - Model Discovery: Find and catalog available GGUF models
/// - Model Selection: Recommend optimal model based on hardware
/// - Model Validation: Verify model integrity and compatibility
/// Uses LocalLLMManager (unified module from RAG_RAT)
#[derive(Debug, Clone)]
pub struct ZenBrain {
    pub manager: LocalLLMManager,
    pub status: Option<LocalLLMStatus>,
    pub selected_model: Option<String>,
}

impl ZenBrain {
    /// Initialize the brain with unified LLM management
    pub fn new(model_dir: Option<PathBuf>) -> Self {
        Self {
            manager: LocalLLMManager((model_dir || PathBuf::from(config::MODEL_DIR))),
            status: None,
            selected_model: None,
        }
    }
    /// Initialize and discover available models.
    /// Returns complete status of LLM infrastructure.
    pub fn wake_up(&mut self) -> Result<LocalLLMStatus> {
        // Initialize and discover available models.
        // Returns complete status of LLM infrastructure.
        logger.info("[Brain] Waking up... searching for llama-server and GGUF models".to_string());
        // try:
        {
            self.status = self.manager.initialize(/* check_updates= */ false);
            if self.status.llama_cpp_ready {
                safe_print(format!("{} llama.cpp detected: {}", EMOJI["success".to_string()], /* getattr */ "unknown".to_string()));
            } else {
                safe_print(format!("{} llama.cpp not found - check {}", EMOJI["warning".to_string()], config::BIN_DIR));
            }
            safe_print(format!("{} Discovered {} models", EMOJI["info".to_string()], self.status.models_discovered));
            if self.status.models {
                safe_print(format!("  Top models: {}", self.status.models[..3].iter().map(|m| m.name).collect::<Vec<_>>().join(&", ".to_string())));
            }
            self.status
        }
        // except Exception as e:
    }
    /// Get current brain status
    pub fn get_status(&self) -> HashMap {
        // Get current brain status
        if !self.status {
            self.wake_up();
        }
        if self.status { self.status.to_dict() } else { HashMap::new() }
    }
    /// Recommend a model based on hardware and category.
    /// 
    /// Args:
    /// category: Model category (e.g., 'chat', 'code', 'vision')
    /// 
    /// Returns:
    /// Recommended model filename or None
    pub fn recommend_model(&mut self, category: Option<String>) -> Option<String> {
        // Recommend a model based on hardware and category.
        // 
        // Args:
        // category: Model category (e.g., 'chat', 'code', 'vision')
        // 
        // Returns:
        // Recommended model filename or None
        if (!self.status || !self.status.models) {
            logger.warning("[Brain] No models available for recommendation".to_string());
            None
        }
        if category {
            let mut matching = self.status.models::iter().filter(|m| (m.category && m.category.to_lowercase() == category.to_lowercase())).map(|m| m).collect::<Vec<_>>();
            if matching {
                matching[0].filename
            }
        }
        if self.status.models {
            self.status.models[0].filename
        }
        None
    }
    /// Select a specific model
    pub fn select_model(&mut self, model_name: String) -> () {
        // Select a specific model
        self.selected_model = model_name;
        logger.info(format!("[Brain] Selected model: {}", model_name));
    }
}
