/// utils::py - ZenAI Unified Utility System
/// =======================================
/// Consolidated utilities for process management, hardware profiling, and diagnostics.
/// Strictly follows zena_master_spec.md v3.1.

use anyhow::{Result, Context};
use crate::config_system::{EMOJI, config};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub const BASE_DIR: &str = "config::BASE_DIR";

pub const PROC_NAME: &str = "str(getattr(sys::modules.get('__main__'), 'file!()', 'unknown'))";

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Unified handler for process lifecycle and 'Zombie' pruning.
#[derive(Debug, Clone)]
pub struct ProcessManager {
}

impl ProcessManager {
    /// Identifies hanging processes by port or script name.
    pub fn get_zombies(ports: Vec<i64>, scripts: Vec<String>) -> Result<HashMap<i64, HashMap>> {
        // Identifies hanging processes by port or script name.
        let mut zombies = HashMap::new();
        if !psutil {
            zombies
        }
        let mut target_ports = (ports || vec![config::llm_port, config::mgmt_port, config::ui_port, config::voice_port]);
        let mut target_scripts = (scripts || vec!["zena.py".to_string(), "start_llm::py".to_string(), "llama-server::exe".to_string()]);
        let mut current_pid = os::getpid();
        // try:
        {
            let mut parent_pid = psutil.Process(current_pid).ppid();
        }
        // except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as _e:
        // try:
        {
            for conn in psutil.net_connections(/* kind= */ "inet".to_string()).iter() {
                if (target_ports.contains(&conn.laddr.port) && conn.status != "LISTEN".to_string()) {
                    continue;
                }
                // try:
                {
                    let mut p = psutil.Process(conn.pid);
                    if (current_pid, parent_pid).contains(&conn.pid) {
                        continue;
                    }
                    zombies[conn.pid] = HashMap::from([("type".to_string(), "Port Conflict".to_string()), ("port".to_string(), conn.laddr.port), ("name".to_string(), p.name()), ("cmd".to_string(), p.cmdline()[..3].join(&" ".to_string()))]);
                }
                // except (psutil.NoSuchProcess, psutil.AccessDenied) as _e:
            }
        }
        // except (psutil.AccessDenied, OSError) as _e:
        for p in psutil.process_iter(vec!["pid".to_string(), "name".to_string(), "cmdline".to_string()]).iter() {
            // try:
            {
                let mut pid = p.info["pid".to_string()];
                if ((current_pid, parent_pid).contains(&pid) || zombies.contains(&pid)) {
                    continue;
                }
                let mut cmd = (p.info["cmdline".to_string()] || vec![]);
                let mut cmd_str = cmd.join(&" ".to_string()).to_lowercase();
                for target in target_scripts.iter() {
                    if !cmd_str.contains(&target.to_lowercase()) {
                        continue;
                    }
                    zombies[pid] = HashMap::from([("type".to_string(), "Hanging Instance".to_string()), ("port".to_string(), "N/A".to_string()), ("name".to_string(), p.info["name".to_string()]), ("cmd".to_string(), cmd_str[..100])]);
                    break;
                }
            }
            // except (psutil.NoSuchProcess, psutil.AccessDenied) as _e:
        }
        Ok(zombies)
    }
    /// Safely terminates a process and all its children.
    pub fn kill_tree(pid: i64) -> Result<()> {
        // Safely terminates a process and all its children.
        // try:
        {
            if (!psutil || !psutil.pid_exists(pid)) {
                return;
            }
            let mut parent = psutil.Process(pid);
            for child in parent.children(/* recursive= */ true).iter() {
                // try:
                {
                    child.terminate();
                }
                // except (psutil.NoSuchProcess, psutil.AccessDenied) as _e:
            }
            parent.terminate();
        }
        // except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as _e:
    }
    /// Detect and kill zombies for a clean startup.
    pub fn prune(auto_confirm: bool, ports: Vec<i64>, scripts: Vec<String>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Result<bool> {
        // Detect and kill zombies for a clean startup.
        if kwargs.contains(&"allowed_names".to_string()) {
            let mut scripts = kwargs["allowed_names".to_string()];
        }
        let mut zombies = ProcessManager.get_zombies(/* ports= */ ports, /* scripts= */ scripts);
        if !zombies {
            true
        }
        safe_print(format!("\n{} ZOMBIE PROCESSES DETECTED", EMOJI["warning".to_string()]));
        for (pid, info) in zombies.iter().iter() {
            safe_print(format!("  - [{}] {} (PID: {}, Port: {})", info["type".to_string()], info["name".to_string()], pid, info["port".to_string()]));
        }
        if !auto_confirm {
            let mut ans = input("\nKill these processes to allow a clean startup? (y/n): ".to_string()).to_lowercase();
            if ans != "y".to_string() {
                false
            }
        }
        for pid in zombies.iter() {
            // try:
            {
                if psutil {
                    let mut p = psutil.Process(pid);
                    p.kill();
                } else {
                    os::kill(pid, signal::SIGTERM);
                }
                safe_print(format!("  {} Terminated PID {}", EMOJI["success".to_string()], pid));
            }
            // except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as _e:
        }
        std::thread::sleep(std::time::Duration::from_secs_f64(1));
        Ok(true)
    }
}

/// v3.1 Smoke Test Engine.
#[derive(Debug, Clone)]
pub struct DiagnosticRunner {
}

impl DiagnosticRunner {
    /// Run smoke test.
    pub async fn run_smoke_test() -> () {
        // Run smoke test.
        let mut results = vec![];
        safe_print(format!("\n{} Running Global System Health Check...", EMOJI["search".to_string()]));
        results.push(("Config Integrity".to_string(), if /* hasattr(config, "BIN_DIR".to_string()) */ true { "OK".to_string() } else { "FAIL".to_string() }));
        results.push(("Engine Binary".to_string(), if (config::BIN_DIR / "llama-server::exe".to_string()).exists() { "OK".to_string() } else { "MISSING".to_string() }));
        results.push(("API Port Availability".to_string(), if !is_port_active(config::llm_port) { "OK".to_string() } else { "BUSY".to_string() }));
        for (name, status) in results.iter() {
            let mut icon = if status == "OK".to_string() { EMOJI["success".to_string()] } else { EMOJI["error".to_string()] };
            safe_print(format!("{} {:<20}: {}", icon, name, status));
        }
        results.iter().map(|(_, s)| s == "OK".to_string()).collect::<Vec<_>>().iter().all(|v| *v)
    }
}

/// Thread-safe and encoding-safe print with automatic flush.
/// 
/// Handles:
/// - UnicodeEncodeError: strips non-ASCII chars on encoding failures
/// - OSError: silently skips print when no console is attached (Windows Explorer launch)
pub fn safe_print(args: Vec<Box<dyn std::any::Any>>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Result<()> {
    // Thread-safe and encoding-safe print with automatic flush.
    // 
    // Handles:
    // - UnicodeEncodeError: strips non-ASCII chars on encoding failures
    // - OSError: silently skips print when no console is attached (Windows Explorer launch)
    kwargs["flush".to_string()] = kwargs.get(&"flush".to_string()).cloned().unwrap_or(true);
    let mut sep = kwargs.get(&"sep".to_string()).cloned().unwrap_or(" ".to_string());
    let mut text = args.iter().map(|a| a.to_string()).collect::<Vec<_>>().join(&sep);
    // try:
    {
        println!("{}", text, /* ** */ kwargs);
    }
    // except UnicodeEncodeError as _e:
    // except OSError as _e:
    // try:
    {
        sys::stdout.flush();
    }
    // except Exception as _e:
    // try:
    {
        sys::stdout.flush();
    }
    // except (OSError, AttributeError) as _e:
    let mut lvl = level.to_lowercase();
    if lvl == "debug".to_string() {
        logger.debug(text);
    } else if lvl == "warning".to_string() {
        logger.warning(text);
    } else if lvl == "error".to_string() {
        logger.error(text);
    } else {
        logger.info(text);
    }
}

/// Computes SHA256 hash of a file.
pub fn sha256sum(path: PathBuf) -> Result<String> {
    // Computes SHA256 hash of a file.
    let mut h = hashlib::sha256();
    let mut f = File::open(path)?;
    {
        for chunk in iter(|| f.read(8192), b"").iter() {
            h.extend(chunk);
        }
    }
    Ok(h.hexdigest())
}

/// Checks if a TCP port is open/active.
pub fn is_port_active(port: i64, host: String) -> bool {
    // Checks if a TCP port is open/active.
    let mut s = socket::socket(socket::AF_INET, socket::SOCK_STREAM);
    {
        s.settimeout(1.0_f64);
        s.connect_ex((host, port)) == 0
    }
}

/// Waits for a port to become active.
pub fn wait_for_port(port: i64, timeout: i64, host: String) -> bool {
    // Waits for a port to become active.
    let mut start = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
    while (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - start) < timeout {
        if is_port_active(port, host) {
            true
        }
        std::thread::sleep(std::time::Duration::from_secs_f64(1));
    }
    false
}

/// Guarantees a Python package is available.
pub fn ensure_package(import_name: String, install_name: String) -> Result<()> {
    // Guarantees a Python package is available.
    if !install_name {
        let mut install_name = import_name;
    }
    // try:
    {
        __import__(import_name);
    }
    // except ImportError as _e:
}

/// Restarts the current python program.
pub fn restart_program() -> () {
    // Restarts the current python program.
    os::execl(sys::executable, sys::executable, /* *std::env::args().collect::<Vec<String>>() */);
}

pub fn prune_zombies(auto_confirm: String) -> () {
    ProcessManager.prune(auto_confirm)
}

pub fn kill_process_tree(pid: String) -> () {
    ProcessManager.kill_tree(pid)
}

/// Legacy shim.
pub fn kill_process_by_name(name: String) -> Result<()> {
    // Legacy shim.
    if !psutil {
        return;
    }
    for p in psutil.process_iter(vec!["name".to_string()]).iter() {
        if p.info["name".to_string()] != name {
            continue;
        }
        // try:
        {
            p.kill();
        }
        // except (psutil.NoSuchProcess, psutil.AccessDenied) as _e:
    }
}

/// Legacy shim.
pub fn kill_process_by_port(port: i64) -> Result<()> {
    // Legacy shim.
    if !psutil {
        return;
    }
    for conn in psutil.net_connections().iter() {
        if conn.laddr.port != port {
            continue;
        }
        // try:
        {
            psutil.Process(conn.pid).kill();
        }
        // except (psutil.NoSuchProcess, psutil.AccessDenied) as _e:
    }
}

/// Legacy shim.
pub fn trace_log(msg: String, level: String) -> () {
    // Legacy shim.
    safe_print(format!("[Trace] {}", msg), /* level= */ level);
}

/// Formats a user message to include attached file content.
pub fn format_message_with_attachment(user_query: String, filename: String, content: String) -> String {
    // Formats a user message to include attached file content.
    // TODO: import os
    let mut ext = os::path.splitext(filename)[1].to_lowercase();
    if (content.contains(&"[Binary file:".to_string()) || content.contains(&"[Binary Content]".to_string())) {
        format!("[Attached: {}] {}", filename, user_query)
    }
    let mut code_extensions = vec![".py".to_string(), ".js".to_string(), ".html".to_string(), ".css".to_string(), ".json".to_string(), ".cpp".to_string(), ".c".to_string(), ".java".to_string(), ".go".to_string(), ".rs".to_string(), ".ts".to_string(), ".sh".to_string(), ".bat".to_string()];
    if code_extensions.contains(&ext) {
        let mut lang = ext[1..];
        if lang == "py".to_string() {
            let mut lang = "python".to_string();
        }
        let mut context_block = format!("I have attached a code file '{}'. Please analyze and review its logic:\\n\\n```{}\\n{}\\n```", filename, lang, content);
    } else {
        let mut context_block = format!("I have attached a file '{}' for context:\\n\\n[Start of File]\\n{}\\n[End of File]", filename, content);
    }
    format!("{}\\n\\n{}", context_block, user_query)
}

/// Sanitizes user input to prevent prompt injection.
pub fn sanitize_prompt(text: String) -> String {
    // Sanitizes user input to prevent prompt injection.
    if !text {
        "".to_string()
    }
    let mut forbidden = vec!["<|im_start|>".to_string(), "<|im_end|>".to_string(), "<|system|>".to_string(), "<|user|>".to_string(), "<|assistant|>".to_string(), "[INST]".to_string(), "[/INST]".to_string()];
    for token in forbidden.iter() {
        let mut text = text.replace(&*token, &*"".to_string());
    }
    text.trim().to_string()
}

/// Normalizes input (url, path, etc.).
pub fn normalize_input(value: String, input_type: String) -> String {
    // Normalizes input (url, path, etc.).
    if !value {
        "".to_string()
    }
    let mut value = value.trim().to_string().trim_matches(|c: char| "\"".to_string().contains(c)).to_string().trim_matches(|c: char| "'".to_string().contains(c)).to_string();
    if input_type == "url".to_string() {
        if (value && !value.starts_with(&*("http://".to_string(), "https://".to_string(), "file://".to_string()))) {
            if (value.contains(&"localhost".to_string()) || value.contains(&"127.0.0.1".to_string())) {
                format!("http://{}", value)
            }
            format!("https://{}", value)
        }
    } else if input_type == "path".to_string() {
        let mut value = value.replace(&*"/".to_string(), &*os::sep).replace(&*"\\".to_string(), &*os::sep);
    }
    value
}

/// Secure extraction helper.
pub fn safe_extract(zip_path: PathBuf, dest: PathBuf) -> Result<()> {
    // Secure extraction helper.
    // TODO: import zipfile
    let mut z = zipfile.ZipFile(zip_path, "r".to_string());
    {
        for member in z.namelist().iter() {
            let mut target = (dest / member);
            if !target.canonicalize().unwrap_or_default().to_string().starts_with(&*dest.canonicalize().unwrap_or_default().to_string()) {
                return Err(anyhow::anyhow!("RuntimeError('Security Alert: Zip Slip attempt detected!')"));
            }
        }
        z.extractall(dest);
    }
}
