use anyhow::{Result, Context};
use crate::config_system::{config};
use crate::handlers::{BaseZenHandler, ModelHandler, VoiceHandler, StaticHandler, ChatHandler, HealthHandler, OrchestrationHandler};
use crate::server::{ThreadingHTTPServer, BaseHTTPRequestHandler};
use crate::utils::{logger, ensure_package, safe_print, ProcessManager, is_port_active, kill_process_by_name, kill_process_by_port};
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub const MODEL_PATH: &str = "config::MODEL_DIR / config::default_model";

pub const SERVER_EXE: &str = "config::BIN_DIR / 'llama-server::exe";

pub static EXPERT_PROCESSES: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub static SERVER_PROCESS: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static EXPERT_LOCK: std::sync::LazyLock<std::sync::Mutex<()>> = std::sync::LazyLock::new(|| std::sync::Mutex::new(()));

pub static MONITORED_PROCESSES: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub static PROCESS_LOCK: std::sync::LazyLock<std::sync::Mutex<()>> = std::sync::LazyLock::new(|| std::sync::Mutex::new(()));

pub static MODEL_PATH_LOCK: std::sync::LazyLock<std::sync::Mutex<()>> = std::sync::LazyLock::new(|| std::sync::Mutex::new(()));

pub static PENDING_MODEL_SWAP: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static _MODEL_MANAGER_CACHE: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

pub static _VOICE_SERVICE_CACHE: std::sync::LazyLock<Option<serde_json::Value>> = std::sync::LazyLock::new(|| None);

/// Reads stdout from a subprocess in a non-blocking thread and logs it.
/// Prevents pipe buffer deadlocks on Windows.
/// Hardened: Uses chunk-based reading to handle non-newline output and binary artifacts.
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
    pub fn run(&mut self) -> Result<()> {
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
                // except Exception as exc:
            }
        }
        // except Exception as exc:
    }
}

/// Management API (Port 8002)
/// Handles:
/// - Model Swapping (Hot Swap)
/// - Swarm Expert Launching
/// - System Health & Telemetry
/// - Voice Transcription Relay
#[derive(Debug, Clone)]
pub struct ZenAIOrchestrator {
}

impl ZenAIOrchestrator {
    pub fn do_POST(&mut self) -> Result<()> {
        // try:
        {
            let mut length = self.headers.get(&"content-length".to_string()).cloned().unwrap_or(0).to_string().parse::<i64>().unwrap_or(0);
            let mut body = self.rfile.read(length).decode("utf-8".to_string());
            let mut data = if body { serde_json::from_str(&body).unwrap() } else { HashMap::new() };
            if self.path == "/model/swap".to_string() {
                let mut model_name = data.get(&"model".to_string()).cloned();
                if !model_name {
                    self._send_json(400, HashMap::from([("error".to_string(), "Missing model name".to_string())]));
                    return;
                }
                safe_print(format!("🔄 Request to swap to: {}", model_name));
                // global/nonlocal PENDING_MODEL_SWAP
                let mut PENDING_MODEL_SWAP = model_name;
                self._send_json(200, HashMap::from([("status".to_string(), "swap_scheduled".to_string()), ("model".to_string(), model_name)]));
            } else if self.path == "/swarm/launch".to_string() {
                let mut model_name = data.get(&"model".to_string()).cloned();
                let mut port = data.get(&"port".to_string()).cloned().unwrap_or(8005).to_string().parse::<i64>().unwrap_or(0);
                if !model_name {
                    self._send_json(400, HashMap::from([("error".to_string(), "Missing model name".to_string())]));
                    return;
                }
                let mut target_path = (config::MODEL_DIR / model_name);
                if !target_path.exists() {
                    let mut target_path = (((Path.home() / "AI".to_string()) / "Models".to_string()) / model_name);
                    if !target_path.exists() {
                        self._send_json(404, HashMap::from([("error".to_string(), format!("Model {} not found", model_name))]));
                        return;
                    }
                }
                if (EXPERT_PROCESSES.contains(&port) && EXPERT_PROCESSES[&port].poll().is_none()) {
                    self._send_json(200, HashMap::from([("status".to_string(), "already_running".to_string()), ("port".to_string(), port)]));
                    return;
                }
                safe_print(format!("🚀 Launching Expert: {} on Port {}...", model_name, port));
                let mut cmd = build_llama_cmd(/* port= */ port, /* threads= */ 4, /* ctx= */ 2048, /* batch= */ 512, /* ubatch= */ 512, /* model_path= */ target_path);
                let mut proc = subprocess::Popen(cmd, /* cwd= */ config::BIN_DIR.to_string(), /* stdout= */ subprocess::PIPE, /* stderr= */ subprocess::STDOUT, /* shell= */ false);
                EXPERT_PROCESSES[port] = proc;
                let mut relay = LogRelay(proc, /* prefix= */ format!("[Expert-{}]", port));
                relay.start();
                let mut active = false;
                for _ in 0..20.iter() {
                    if is_port_active(port) {
                        let mut active = true;
                        break;
                    }
                    std::thread::sleep(std::time::Duration::from_secs_f64(1));
                }
                if active {
                    self._send_json(200, HashMap::from([("status".to_string(), "launched".to_string()), ("port".to_string(), port), ("pid".to_string(), proc.pid)]));
                } else {
                    self._send_json(500, HashMap::from([("error".to_string(), "Expert process started but port unreachable".to_string())]));
                }
            } else if self.path == "/voice/transcribe".to_string() {
                self._send_json(200, HashMap::from([("text".to_string(), "[Voice transcription placeholder]".to_string())]));
            } else {
                self._send_json(404, HashMap::from([("error".to_string(), "Unknown endpoint".to_string())]));
            }
        }
        // except Exception as e:
    }
    pub fn do_GET(&mut self) -> () {
        if self.path == "/health".to_string() {
            let mut status = if (SERVER_PROCESS && SERVER_PROCESS.poll().is_none()) { "online".to_string() } else { "offline".to_string() };
            let mut experts = EXPERT_PROCESSES.iter().iter().map(|(p, proc)| (p, if proc.poll().is_none() { "running".to_string() } else { "dead".to_string() })).collect::<HashMap<_, _>>();
            self._send_json(200, HashMap::from([("status".to_string(), status), ("model".to_string(), MODEL_PATH.name), ("experts".to_string(), experts)]));
        } else {
            self._send_json(404, HashMap::from([("error".to_string(), "Not found".to_string())]));
        }
    }
    pub fn _send_json(&self, code: String, data: String) -> Result<()> {
        self.send_response(code);
        self.send_header("Content-type".to_string(), "application/json".to_string());
        self.end_headers();
        Ok(self.wfile.write(serde_json::to_string(&data).unwrap().encode("utf-8".to_string())))
    }
}

#[derive(Debug, Clone)]
pub struct ZenAIOrchestrator {
}

impl ZenAIOrchestrator {
    /// Main GET routing entry point.
    pub fn do_GET(&self) -> () {
        // Main GET routing entry point.
        if HealthHandler.handle_get(self) {
            return;
        }
        if ModelHandler.handle_get(self) {
            return;
        }
        if VoiceHandler.handle_get(self) {
            return;
        }
        if StaticHandler.handle_get(self) {
            return;
        }
        self.send_json_response(200, HashMap::from([("status".to_string(), "ZenAI Hub Active".to_string()), ("path".to_string(), self.path)]));
    }
    /// Main POST routing entry point.
    pub fn do_POST(&self) -> () {
        // Main POST routing entry point.
        if !self.check_request_size() {
            return;
        }
        if OrchestrationHandler.handle_post(self) {
            return;
        }
        if ModelHandler.handle_post(self) {
            return;
        }
        if VoiceHandler.handle_post(self) {
            return;
        }
        if ChatHandler.handle_post(self) {
            return;
        }
        self.send_json_response(404, HashMap::from([("error".to_string(), "Endpoint not found".to_string())]));
    }
}

#[derive(Debug, Clone)]
pub struct VoiceStreamHandler {
    pub clients: HashSet<String>,
}

impl VoiceStreamHandler {
    pub fn new() -> Self {
        Self {
            clients: HashSet::new(),
        }
    }
    pub async fn handle_client(&self, ws: String) -> Result<()> {
        self.clients.insert(ws);
        // try:
        {
            // async for
            while let Some(msg) = ws.next().await {
                // pass
            }
        }
        // finally:
            Ok(self.clients.remove(ws))
    }
}

/// Safely exit the application, ensuring all output is flushed first.
pub fn safe_exit(code: i64, delay: f64) -> () {
    // Safely exit the application, ensuring all output is flushed first.
    std::thread::sleep(std::time::Duration::from_secs_f64(delay));
    std::process::exit(code);
}

/// Pre-flight validation: Check binaries, models, and dependencies.
pub fn validate_environment() -> () {
    // Pre-flight validation: Check binaries, models, and dependencies.
    safe_print("[Pre-flight] Validating core components...".to_string());
    if !SERVER_EXE.exists() {
        safe_print(format!("❌ Error: Engine binary not found: {}", SERVER_EXE));
        false
    }
    if SERVER_EXE.stat().st_size < 1000 {
        safe_print("❌ Error: Engine binary seems corrupted (size too small).".to_string());
        false
    }
    if !MODEL_PATH.exists() {
        safe_print(format!("❌ Error: Model file not found: {}", MODEL_PATH));
        false
    }
    if MODEL_PATH.stat().st_size < 1000000 {
        safe_print(format!("❌ Error: Model file seems corrupted or incomplete: {}", MODEL_PATH));
        false
    }
    let mut critical_ports = vec![config::llm_port, config::mgmt_port];
    for port in critical_ports.iter() {
        if is_port_active(port) {
            safe_print(format!("⚠️ Port {} is ALREADY ACTIVE. Attempting cleanup...", port));
            kill_process_by_port(port);
            std::thread::sleep(std::time::Duration::from_secs_f64(1));
            if is_port_active(port) {
                safe_print(format!("❌ Error: Port {} is held by an unkillable process.", port));
                false
            }
        }
    }
    safe_print("✅ Pre-flight validation: SUCCESS".to_string());
    true
}

/// Register a process for health monitoring.
pub fn register_process(name: String, process: String, critical: String) -> () {
    // Register a process for health monitoring.
    let _ctx = PROCESS_LOCK;
    {
        MONITORED_PROCESSES[name] = HashMap::from([("process".to_string(), process), ("critical".to_string(), critical), ("restarts".to_string(), 0), ("max_restarts".to_string(), if critical { 3 } else { 1 }), ("start_time".to_string(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64())]);
    }
    logger.info(format!("[Monitor] Registered {}process: {} (PID: {})", if critical { "CRITICAL ".to_string() } else { "".to_string() }, name, process.pid));
}

/// Check health of all monitored processes. Returns list of crashed ones.
pub fn check_processes() -> Result<()> {
    // Check health of all monitored processes. Returns list of crashed ones.
    let mut crashed = vec![];
    let _ctx = PROCESS_LOCK;
    {
        let mut to_remove = vec![];
        for (name, info) in MONITORED_PROCESSES.iter().iter() {
            let mut proc = info["process".to_string()];
            // try:
            {
                let mut exit_code = proc.poll();
                if exit_code.is_some() {
                    crashed.push((name, exit_code, info["critical".to_string()]));
                    to_remove.push(name);
                }
            }
            // except Exception as e:
        }
        for name in to_remove.iter() {
            drop(MONITORED_PROCESSES[name]);
        }
    }
    Ok(crashed)
}

pub fn get_model_manager() -> Result<()> {
    // global/nonlocal _model_manager_cache
    if _model_manager_cache.is_none() {
        // try:
        {
            // TODO: import model_manager
            let mut _model_manager_cache = model_manager;
        }
        // except ImportError as _e:
    }
    Ok(_model_manager_cache)
}

pub fn get_cached_voice_service() -> Result<()> {
    // global/nonlocal _voice_service_cache
    if _voice_service_cache.is_none() {
        // try:
        {
            // TODO: import voice_service
            let mut _voice_service_cache = voice_service;
        }
        // except ImportError as _e:
    }
    Ok(_voice_service_cache)
}

/// Read integer from environment variable with fallback to default.
pub fn env_int(name: String, default: i64) -> Result<i64> {
    // Read integer from environment variable with fallback to default.
    let mut val = std::env::var(&name).unwrap_or_default().cloned().unwrap_or("".to_string()).trim().to_string();
    if !val {
        default
    }
    // try:
    {
        val.to_string().parse::<i64>().unwrap_or(0)
    }
    // except ValueError as _e:
}

/// Build llama-server::exe command arguments.
pub fn build_llama_cmd(port: i64, threads: i64, ctx: i64, gpu_layers: i64, batch: i64, ubatch: i64, model_path: PathBuf, timeout: i64, threads_batch: i64, parallel: i64) -> Vec {
    // Build llama-server::exe command arguments.
    if model_path.is_none() {
        let mut model_path = MODEL_PATH;
    }
    if threads_batch.is_none() {
        let mut threads_batch = threads;
    }
    vec![SERVER_EXE.to_string(), "--model".to_string(), model_path.to_string(), "--host".to_string(), "127.0.0.1".to_string(), "--port".to_string(), port.to_string(), "--ctx-size".to_string(), ctx.to_string(), "--n-gpu-layers".to_string(), gpu_layers.to_string(), "--threads".to_string(), threads.to_string(), "--threads-batch".to_string(), threads_batch.to_string(), "--batch-size".to_string(), batch.to_string(), "--ubatch-size".to_string(), ubatch.to_string(), "--repeat-penalty".to_string(), "1.1".to_string(), "--repeat-last-n".to_string(), "1024".to_string(), "--min-p".to_string(), "0.1".to_string(), "--alias".to_string(), "local-model".to_string(), "--no-warmup".to_string(), "--timeout".to_string(), timeout.to_string(), "-np".to_string(), parallel.to_string()]
}

/// Signal the main loop to perform a Hot Swap.
pub fn restart_with_model(name: String) -> () {
    // Signal the main loop to perform a Hot Swap.
    // global/nonlocal PENDING_MODEL_SWAP, SERVER_PROCESS
    logger.info(format!("[Orchestrator] Initiating Hot Swap to: {}", name));
    let mut PENDING_MODEL_SWAP = name;
    if SERVER_PROCESS {
        SERVER_PROCESS.terminate();
    }
}

/// Cleanly launch an expert LLM instance.
pub fn launch_expert_process(port: i64, threads: i64, model_path: PathBuf) -> Result<()> {
    // Cleanly launch an expert LLM instance.
    let mut env = os::environ.clone();
    env["LLM_PORT".to_string()] = port.to_string();
    env["LLM_THREADS".to_string()] = threads.to_string();
    let mut root_dir = config::BASE_DIR.to_string();
    let mut current_pp = env.get(&"PYTHONPATH".to_string()).cloned().unwrap_or("".to_string());
    let mut sep = if os::name == "nt".to_string() { ";".to_string() } else { ":".to_string() };
    env["PYTHONPATH".to_string()] = if current_pp { format!("{}{}{}", root_dir, sep, current_pp) } else { root_dir };
    let mut script_path = os::path.abspath(file!());
    let mut cmd = vec![sys::executable, script_path, "--guard-bypass".to_string()];
    if (model_path && model_path.exists()) {
        cmd.extend(vec!["--model".to_string(), model_path.to_string()]);
    } else if MODEL_PATH.exists() {
        cmd.extend(vec!["--model".to_string(), MODEL_PATH.to_string()]);
    }
    let mut p = subprocess::Popen(cmd, /* env= */ env, /* cwd= */ root_dir, /* creationflags= */ if os::name == "nt".to_string() { subprocess::CREATE_NO_WINDOW } else { 0 }, /* shell= */ false);
    register_process(format!("Expert-{}", port), p);
    Ok(p)
}

/// Dynamically adjust the number of running experts.
pub fn scale_swarm(target_count: i64) -> () {
    // Dynamically adjust the number of running experts.
    // global/nonlocal EXPERT_PROCESSES
    let _ctx = EXPERT_LOCK;
    {
        let mut current_ports = { let mut v = EXPERT_PROCESSES.keys().clone(); v.sort(); v };
        let mut current_count = current_ports.len();
        if target_count > current_count {
            let mut needed = (target_count - current_count);
            for i in 0..needed.iter() {
                let mut port = (8005 + EXPERT_PROCESSES.len());
                EXPERT_PROCESSES[port] = launch_expert_process(port, 2);
            }
        } else if target_count < current_count {
            let mut to_remove = (current_count - target_count);
            for _ in 0..to_remove.iter() {
                let (mut port, mut proc) = EXPERT_PROCESSES.popitem();
                ProcessManager.kill_tree(proc.pid);
            }
        }
    }
}

/// Start the Management API (Hub) - uses ASGI by default.
pub fn start_hub() -> Result<()> {
    // Start the Management API (Hub) - uses ASGI by default.
    let mut use_asgi = std::env::var(&"ZENAI_USE_ASGI".to_string()).unwrap_or_default().cloned().unwrap_or("1".to_string()) == "1".to_string();
    if use_asgi {
        // try:
        {
            // TODO: import uvicorn
            // TODO: from zena_mode.asgi_server import app
            safe_print(format!("[*] Starting ASGI Hub API on 127.0.0.1:{}...", config::mgmt_port));
            let run_uvicorn = || {
                // TODO: import asyncio
                let mut r#loop = asyncio.new_event_loop();
                asyncio.set_event_loop(r#loop);
                let mut uvicorn_config = uvicorn.Config(app, /* host= */ "127.0.0.1".to_string(), /* port= */ config::mgmt_port, /* log_level= */ "warning".to_string(), /* loop= */ "asyncio".to_string());
                let mut server = uvicorn.Server(uvicorn_config);
                r#loop.run_until_complete(server::serve());
            };
            std::thread::spawn(|| {});
            safe_print(format!("[*] ASGI Hub API listening on 127.0.0.1:{}", config::mgmt_port));
        }
        // except Exception as e:
    } else {
        _start_sync_hub();
    }
}

/// Legacy sync HTTP server fallback.
pub fn _start_sync_hub() -> Result<()> {
    // Legacy sync HTTP server fallback.
    // try:
    {
        safe_print(format!("[*] Starting sync Hub API on port {}...", config::mgmt_port));
        let mut hub = ThreadingHTTPServer(("127.0.0.1".to_string(), config::mgmt_port), ZenAIOrchestrator);
        std::thread::spawn(|| {});
        safe_print(format!("[*] Sync Hub API listening on 127.0.0.1:{}", config::mgmt_port));
    }
    // except Exception as e:
}

pub async fn run_ws_server() -> Result<()> {
    if websockets {
        // try:
        {
            let _ctx = websockets.serve(VoiceStreamHandler().handle_client, "0.0.0.0".to_string(), 8003);
            {
                safe_print("[*] Voice Stream Server listening on Port 8003".to_string());
                asyncio.Future().await;
            }
        }
        // except OSError as e:
        // except Exception as e:
    }
}

pub fn start_voice_stream_server() -> () {
    if websockets {
        std::thread::spawn(|| {});
    }
}

pub fn start_server() -> Result<NoReturn> {
    // global/nonlocal MODEL_PATH, SERVER_PROCESS, EXPERT_PROCESSES, PENDING_MODEL_SWAP
    let mut relay = None;
    let mut port = env_int("LLM_PORT".to_string(), 8001);
    if !SERVER_EXE.exists() {
        safe_print(format!("❌ Critical Error: llama-server::exe NOT FOUND at {}", SERVER_EXE));
        std::process::exit(1);
    }
    if !MODEL_PATH.exists() {
        let mut ggufs = config::MODEL_DIR.glob("*.gguf".to_string()).into_iter().collect::<Vec<_>>();
        if ggufs {
            let mut MODEL_PATH = ggufs[0];
            logger.info(format!("[Engine] Default model missing, using discovered: {}", MODEL_PATH.name));
        } else {
            safe_print(format!("❌ ERROR: No .gguf models found in {}", config::MODEL_DIR));
            std::process::exit(1);
        }
    }
    let mut threads = env_int("LLM_THREADS".to_string(), config::threads);
    let mut gpu_layers = env_int("LLM_GPU_LAYERS".to_string(), config::gpu_layers);
    logger.info(format!("[Engine] Configured with {} threads and {} GPU layers.", threads, gpu_layers));
    let mut cmd = build_llama_cmd(/* port= */ port, /* threads= */ threads, /* ctx= */ config::context_size, /* batch= */ config::batch_size, /* ubatch= */ config::ubatch_size);
    if (!cmd.contains(&"--n-gpu-layers".to_string()) && !cmd.contains(&"--n_gpu_layers".to_string())) {
        cmd.extend(vec!["--n-gpu-layers".to_string(), gpu_layers.to_string()]);
    }
    if std::env::var(&"ZENA_SKIP_PRUNE".to_string()).unwrap_or_default().cloned() != "1".to_string() {
        safe_print("[*] Engine Guard: Ensuring ports are clean...".to_string());
        ProcessManager.prune(port, /* allowed_names= */ vec!["llama-server::exe".to_string(), "python.exe".to_string()]);
        kill_process_by_name("llama-server::exe".to_string());
        std::thread::sleep(std::time::Duration::from_secs_f64(1));
    }
    // try:
    {
        safe_print(format!("[*] Hub Check: port={}, config::llm_port={}, bypass={}", port, config::llm_port, std::env::args().collect::<Vec<String>>().contains(&"--guard-bypass".to_string())));
        if (!std::env::args().collect::<Vec<String>>().contains(&"--guard-bypass".to_string()) || port == config::llm_port) {
            start_hub();
            start_voice_stream_server();
        }
        if (SERVER_PROCESS && SERVER_PROCESS.poll().is_none()) {
            logger.info("[Engine] Existing SERVER_PROCESS detected (skipping native engine launch)".to_string());
        } else {
            logger.info(format!("[Engine] Launching: {}", cmd.join(&" ".to_string())));
            // try:
            {
                let mut SERVER_PROCESS = subprocess::Popen(cmd, /* env= */ os::environ, /* cwd= */ config::BIN_DIR.to_string(), /* stdout= */ subprocess::PIPE, /* stderr= */ subprocess::STDOUT, /* text= */ false, /* bufsize= */ -1, /* shell= */ false);
                let mut relay = LogRelay(SERVER_PROCESS);
                relay.start();
                register_process("LLM-Server".to_string(), SERVER_PROCESS, /* critical= */ true);
            }
            // except FileNotFoundError as e:
        }
        if (!std::env::args().collect::<Vec<String>>().contains(&"--guard-bypass".to_string()) && !std::env::args().collect::<Vec<String>>().contains(&"--no-ui".to_string())) {
            let mut ui_script = (config::BASE_DIR / "app::py".to_string());
            if !ui_script.exists() {
                let mut ui_script = (config::BASE_DIR / "zena.py".to_string());
            }
            let mut ui_env = os::environ.clone();
            ui_env["ZENA_SKIP_PRUNE".to_string()] = "1".to_string();
            let mut ui_process = subprocess::Popen(vec![sys::executable, "-m".to_string(), "streamlit".to_string(), "run".to_string(), ui_script.to_string()], /* cwd= */ config::BASE_DIR.to_string(), /* env= */ ui_env, /* stdout= */ subprocess::PIPE, /* stderr= */ subprocess::STDOUT, /* shell= */ false);
            let mut ui_relay = LogRelay(ui_process, /* prefix= */ "[UI]".to_string(), /* chunk_size= */ 1024);
            ui_relay.start();
            register_process("RAG-UI".to_string(), ui_process, /* critical= */ false);
            safe_print(format!("[*] UI Launched ({}) - Logs proxied to debug log", ui_script.name));
        }
        safe_print(format!("[*] Waiting for LLM-Server to bind to port {}...", port));
        let mut bound = false;
        for _ in 0..30.iter() {
            if is_port_active(port) {
                let mut bound = true;
                break;
            }
            let mut p_code = SERVER_PROCESS.poll();
            if p_code.is_some() {
                safe_print(format!("❌ LLM-Server CRASHED during startup (exit code {}).", p_code));
                if (relay && relay.last_lines) {
                    safe_print((("\n".to_string() + ("🏁".to_string() * 15)) + "\n  ENGINE'S LAST WORDS:".to_string()));
                    for line in relay.last_lines.iter() {
                        safe_print(format!("  > {}", line));
                    }
                    safe_print((("🏁".to_string() * 15) + "\n".to_string()));
                }
                std::process::exit(1);
            }
            if (_ % 5) == 0 {
                safe_print(format!("[*] Port binding poll: {}/30...", _));
            }
            std::thread::sleep(std::time::Duration::from_secs_f64(1));
        }
        if !bound {
            safe_print(format!("⚠️ Port {} still not active after 30s. Check logs.", port));
        } else {
            safe_print(format!("✅ LLM-Server online on port {}", port));
        }
        while true {
            let mut crashed = check_processes();
            for (name, code, critical) in crashed.iter() {
                if (name == "LLM-Server".to_string() && PENDING_MODEL_SWAP) {
                    safe_print(format!("[Monitor] LLM-Server stopped for swap (code {}). Proceeding to restart...", code));
                    continue;
                }
                safe_print(format!("[!] {} crashed (exit code {})", name, code));
                if critical {
                    if (relay && relay.last_lines) {
                        safe_print((("\n".to_string() + ("🏁".to_string() * 15)) + "\n  ENGINE'S LAST WORDS:".to_string()));
                        for line in relay.last_lines.iter() {
                            safe_print(format!("  > {}", line));
                        }
                        safe_print((("🏁".to_string() * 15) + "\n".to_string()));
                    }
                    safe_print(format!("❌ Critical process {} died. System shutdown initiated.", name));
                    std::process::exit(1);
                }
            }
            if SERVER_PROCESS {
                let mut p_code = SERVER_PROCESS.poll();
                if p_code.is_some() {
                    if PENDING_MODEL_SWAP {
                        safe_print(format!("🔄 Hot Swap Detected! Switching to {}...", PENDING_MODEL_SWAP));
                        let mut new_model_path = (config::MODEL_DIR / PENDING_MODEL_SWAP);
                        if !new_model_path.exists() {
                            safe_print(format!("❌ Swap Error: Model {} not found! Reverting to default.", PENDING_MODEL_SWAP));
                            let mut PENDING_MODEL_SWAP = None;
                        } else {
                            let mut MODEL_PATH = new_model_path;
                        }
                        let mut cmd = build_llama_cmd(/* port= */ port, /* threads= */ threads, /* ctx= */ config::context_size, /* batch= */ config::batch_size, /* ubatch= */ config::ubatch_size, /* model_path= */ MODEL_PATH);
                        if !cmd.contains(&"--n-gpu-layers".to_string()) {
                            cmd.extend(vec!["--n-gpu-layers".to_string(), gpu_layers.to_string()]);
                        }
                        safe_print(format!("[*] Re-launching Engine: {}", cmd.join(&" ".to_string())));
                        // try:
                        {
                            let mut SERVER_PROCESS = subprocess::Popen(cmd, /* env= */ os::environ, /* cwd= */ config::BIN_DIR.to_string(), /* stdout= */ subprocess::PIPE, /* stderr= */ subprocess::STDOUT, /* text= */ false, /* bufsize= */ -1, /* shell= */ false);
                            let mut relay = LogRelay(SERVER_PROCESS);
                            relay.start();
                            register_process("LLM-Server".to_string(), SERVER_PROCESS, /* critical= */ true);
                            let mut PENDING_MODEL_SWAP = None;
                            safe_print(format!("[*] Waiting for swap to complete (port {})...", port));
                            std::thread::sleep(std::time::Duration::from_secs_f64(2));
                            continue;
                        }
                        // except Exception as e:
                    }
                    safe_print(format!("[*] Main Engine poll() returned {}.", p_code));
                    if (relay && relay.last_lines) {
                        safe_print((("\n".to_string() + ("🏁".to_string() * 15)) + "\n  ENGINE'S LAST WORDS:".to_string()));
                        for line in relay.last_lines.iter() {
                            safe_print(format!("  > {}", line));
                        }
                        safe_print((("🏁".to_string() * 15) + "\n".to_string()));
                    }
                    break;
                }
            } else {
                break;
            }
            std::thread::sleep(std::time::Duration::from_secs_f64(2));
        }
    }
    // except KeyboardInterrupt as _e:
    // except Exception as e:
    // finally:
        safe_print("[*] Shutting down all managed processes...".to_string());
        if SERVER_PROCESS {
            // try:
            {
                ProcessManager.kill_tree(SERVER_PROCESS.pid);
            }
            // except Exception as exc:
        }
        let _ctx = EXPERT_LOCK;
        {
            for p in EXPERT_PROCESSES.values().iter() {
                // try:
                {
                    ProcessManager.kill_tree(p.pid);
                }
                // except Exception as exc:
            }
        }
        Ok(safe_print("[*] Orchestrator shutdown complete.".to_string()))
}
