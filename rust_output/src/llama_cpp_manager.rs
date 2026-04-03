/// LlamaCppManager - Cross-platform llama.cpp detection and monitoring
/// 
/// Detects installed llama-server, checks version, monitors health, and provides
/// download information for updates.
/// 
/// Thread-safe with RLock for concurrent access.

use anyhow::{Result, Context};
use regex::Regex;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Status of llama.cpp installation and runtime
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlamaCppStatus {
    pub installed: bool,
    pub version: Option<String>,
    pub latest_version: Option<String>,
    pub needs_update: bool,
    pub path: Option<PathBuf>,
    pub running: bool,
    pub port: i64,
    pub pid: Option<i64>,
    pub error: Option<String>,
}

impl LlamaCppStatus {
    /// Convert to JSON-serializable dict
    pub fn to_dict(&self) -> HashMap {
        // Convert to JSON-serializable dict
        HashMap::from([("installed".to_string(), self.installed), ("version".to_string(), self.version), ("latest_version".to_string(), self.latest_version), ("needs_update".to_string(), self.needs_update), ("path".to_string(), if self.path { self.path.to_string() } else { None }), ("running".to_string(), self.running), ("port".to_string(), self.port), ("pid".to_string(), self.pid), ("error".to_string(), self.error)])
    }
}

/// Detect and monitor llama.cpp installation
#[derive(Debug, Clone)]
pub struct LlamaCppManager {
    pub _lock: RLock,
    pub _status_cache: Option<serde_json::Value>,
    pub _cache_timestamp: f64,
    pub _cache_ttl: f64,
    pub _cache_valid: bool,
    pub _last_error: Option<serde_json::Value>,
}

impl LlamaCppManager {
    /// Initialize manager with thread-safe lock
    pub fn new() -> Self {
        Self {
            _lock: RLock(),
            _status_cache: None,
            _cache_timestamp: 0.0_f64,
            _cache_ttl: 2.0_f64,
            _cache_valid: false,
            _last_error: None,
        }
    }
    /// Run subprocess::run with retries, timeout handling, and consistent return.
    /// 
    /// Returns a simple object with `returncode` and `stdout`, or None on fatal failure.
    pub fn _safe_run(&mut self, args: String, timeout: f64, retries: i64, backoff: f64) -> Result<()> {
        // Run subprocess::run with retries, timeout handling, and consistent return.
        // 
        // Returns a simple object with `returncode` and `stdout`, or None on fatal failure.
        let mut attempt = 0;
        while attempt <= retries {
            // try:
            {
                let mut res = std::process::Command::new("sh").arg("-c").arg(args, /* capture_output= */ true, /* text= */ true, /* timeout= */ timeout).output().unwrap();
                res
            }
            // except FileNotFoundError as _e:
            // except subprocess::TimeoutExpired as e:
            // except Exception as e:
            attempt += 1;
            std::thread::sleep(std::time::Duration::from_secs_f64((backoff * (2)).pow(attempt as u32)));
        }
        Ok(None)
    }
    /// Find llama-server executable in common locations
    /// 
    /// Returns:
    /// Path to executable or None if not found
    pub fn find_llama_server(&mut self) -> Option<PathBuf> {
        // Find llama-server executable in common locations
        // 
        // Returns:
        // Path to executable or None if not found
        let mut system = platform.system();
        let mut search_paths = self.SEARCH_PATHS.get(&system).cloned().unwrap_or(self.SEARCH_PATHS["Linux".to_string()]);
        let mut exe_names = self.EXECUTABLE_NAMES.get(&system).cloned().unwrap_or(self.EXECUTABLE_NAMES["Linux".to_string()]);
        for search_path in search_paths.iter() {
            for exe_name in exe_names.iter() {
                let mut exe_path = (search_path / exe_name);
                if exe_path.exists() {
                    logger.info(format!("Found llama-server at {}", exe_path));
                    exe_path
                }
            }
        }
        for exe_name in exe_names.iter() {
            let mut which_path = shutil::which(exe_name);
            if which_path {
                logger.info(format!("Found llama-server in PATH at {}", which_path));
                PathBuf::from(which_path)
            }
        }
        logger.warning("llama-server not found in any known location".to_string());
        None
    }
    /// Check if llama.cpp is installed and get version
    /// 
    /// Returns:
    /// (installed: bool, version: str or None, path: Path or None)
    pub fn check_installed(&mut self) -> Result<(bool, Option<String>, Option<PathBuf>)> {
        // Check if llama.cpp is installed and get version
        // 
        // Returns:
        // (installed: bool, version: str or None, path: Path or None)
        // try:
        {
            let mut exe_path = self.find_llama_server();
            if !exe_path {
                (false, None, None)
            }
            let mut result = self._safe_run(vec![exe_path.to_string(), "--version".to_string()], /* timeout= */ 5, /* retries= */ 1);
            if (result && /* hasattr(result, "stdout".to_string()) */ true) {
                let mut version = result.stdout.trim().to_string();
                let mut r#match = regex::Regex::new(&"(\\d+\\.\\d+\\.\\d+)".to_string()).unwrap().is_match(&version);
                if r#match {
                    let mut version = r#match.group(1);
                }
                (true, version, exe_path)
            }
            logger.warning(format!("Could not get version for {}; last_error={}", exe_path, self._last_error));
            (true, None, exe_path)
        }
        // except Exception as e:
    }
    /// Get latest llama.cpp version from GitHub API
    /// 
    /// Returns:
    /// Version string or None if lookup fails
    pub fn get_latest_version(&mut self) -> Result<Option<String>> {
        // Get latest llama.cpp version from GitHub API
        // 
        // Returns:
        // Version string or None if lookup fails
        let mut url = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest".to_string();
        // try:
        {
            let mut req = urllib::request.Request(url, /* headers= */ HashMap::from([("Accept".to_string(), "application/vnd.github.v3+json".to_string()), ("User-Agent".to_string(), "MARKET_AI".to_string())]));
            let mut resp = urllib::request.urlopen(req, /* timeout= */ 5);
            {
                let mut data = serde_json::from_str(&resp.read().decode("utf-8".to_string())).unwrap();
                let mut tag = data.get(&"tag_name".to_string()).cloned().unwrap_or("".to_string());
                let mut version = tag.trim_start_matches(|c: char| "b".to_string().contains(c)).to_string();
                if version {
                    version
                }
            }
        }
        // except Exception as e:
        let mut res = self._safe_run(vec!["curl".to_string(), "-s".to_string(), url, "-H".to_string(), "Accept: application/vnd.github.v3+json".to_string()], /* timeout= */ 5, /* retries= */ 1);
        if (res && /* hasattr(res, "stdout".to_string()) */ true) {
            // try:
            {
                let mut data = serde_json::from_str(&res.stdout).unwrap();
                let mut tag = data.get(&"tag_name".to_string()).cloned().unwrap_or("".to_string());
                let mut version = tag.trim_start_matches(|c: char| "b".to_string().contains(c)).to_string();
                if version {
                    version
                }
            }
            // except Exception as _e:
        }
        Ok(None)
    }
    /// Check if update is needed by comparing versions
    /// 
    /// Args:
    /// current: Current version string
    /// latest: Latest version string
    /// 
    /// Returns:
    /// true if update recommended
    pub fn check_update_needed(current: String, latest: String) -> Result<bool> {
        // Check if update is needed by comparing versions
        // 
        // Args:
        // current: Current version string
        // latest: Latest version string
        // 
        // Returns:
        // true if update recommended
        // try:
        {
            let mut current_parts = current.split(".".to_string()).map(|s| s.to_string()).collect::<Vec<String>>().iter().map(|x| x.to_string().parse::<i64>().unwrap_or(0)).collect::<Vec<_>>();
            let mut latest_parts = latest.split(".".to_string()).map(|s| s.to_string()).collect::<Vec<String>>().iter().map(|x| x.to_string().parse::<i64>().unwrap_or(0)).collect::<Vec<_>>();
            while current_parts.len() < latest_parts.len() {
                current_parts.push(0);
            }
            while latest_parts.len() < current_parts.len() {
                latest_parts.push(0);
            }
            latest_parts > current_parts
        }
        // except Exception as _e:
    }
    /// Check if llama-server process is running
    /// 
    /// Returns:
    /// (running: bool, pid: int or None)
    pub fn is_running(&mut self) -> Result<(bool, Option<i64>)> {
        // Check if llama-server process is running
        // 
        // Returns:
        // (running: bool, pid: int or None)
        let mut system = platform.system();
        // try:
        {
            if psutil.is_some() {
                for proc in psutil.process_iter(vec!["pid".to_string(), "name".to_string(), "cmdline".to_string()]).iter() {
                    // try:
                    {
                        let mut name = (proc.info.get(&"name".to_string()).cloned() || "".to_string()).to_lowercase();
                        let mut cmd = (proc.info.get(&"cmdline".to_string()).cloned() || vec![]).join(&" ".to_string()).to_lowercase();
                        if (name.contains(&"llama-server".to_string()) || cmd.contains(&"llama-server".to_string())) {
                            (true, proc.info.get(&"pid".to_string()).cloned().to_string().parse::<i64>().unwrap_or(0))
                        }
                    }
                    // except Exception as _e:
                }
            }
            if system == "Windows".to_string() {
                let mut result = self._safe_run(vec!["tasklist".to_string(), "/FI".to_string(), "IMAGENAME eq llama-server::exe".to_string()], /* timeout= */ 5);
                if (result && (result.stdout || "".to_string()).contains(&"llama-server::exe".to_string())) {
                    let mut lines = (result.stdout || "".to_string()).trim().to_string().split("\n".to_string()).map(|s| s.to_string()).collect::<Vec<String>>();
                    for line in lines.iter() {
                        if line.contains(&"llama-server::exe".to_string()) {
                            let mut parts = line.split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>();
                            if parts.len() >= 2 {
                                // try:
                                {
                                    let mut pid = parts[1].to_string().parse::<i64>().unwrap_or(0);
                                    (true, pid)
                                }
                                // except ValueError as _e:
                            }
                        }
                    }
                    (true, None)
                }
            } else {
                let mut result = self._safe_run(vec!["pgrep".to_string(), "-f".to_string(), "llama-server".to_string()], /* timeout= */ 5);
                if (result && result.returncode == 0 && (result.stdout || "".to_string()).trim().to_string()) {
                    // try:
                    {
                        let mut pid = (result.stdout || "".to_string()).trim().to_string().split_whitespace().map(|s| s.to_string()).collect::<Vec<String>>()[0].to_string().parse::<i64>().unwrap_or(0);
                        (true, pid)
                    }
                    // except (ValueError, IndexError) as _e:
                }
            }
        }
        // except Exception as e:
        Ok((false, None))
    }
    /// Get comprehensive status of llama.cpp
    /// 
    /// Returns:
    /// LlamaCppStatus dataclass with all info
    pub fn get_status(&mut self) -> Result<LlamaCppStatus> {
        // Get comprehensive status of llama.cpp
        // 
        // Returns:
        // LlamaCppStatus dataclass with all info
        let _ctx = self._lock;
        {
            // try:
            {
                let mut now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
                if (self._status_cache && (now - self._cache_timestamp) < self._cache_ttl) {
                    self._status_cache
                }
                let (mut installed, mut version, mut path) = self.check_installed();
                let mut status = LlamaCppStatus(/* installed= */ installed, /* version= */ version, /* path= */ path);
                if installed {
                    // try:
                    {
                        let mut latest = self.get_latest_version();
                        if (latest && version) {
                            status.latest_version = latest;
                            status.needs_update = self.check_update_needed(version, latest);
                        }
                    }
                    // except Exception as e:
                    // try:
                    {
                        let (mut running, mut pid) = self.is_running();
                        status.running = running;
                        if pid {
                            status.pid = pid;
                        }
                    }
                    // except Exception as e:
                }
                self._status_cache = status;
                self._cache_timestamp = now;
                status
            }
            // except Exception as e:
        }
    }
    /// Get download URL for llama.cpp
    pub fn get_download_url(&self) -> String {
        // Get download URL for llama.cpp
        let mut system = platform.system();
        if system == "Windows".to_string() {
            "https://github.com/ggerganov/llama.cpp/releases".to_string()
        } else if system == "Darwin".to_string() {
            "https://github.com/ggerganov/llama.cpp/releases (or: brew install llama-cpp)".to_string()
        } else {
            "https://github.com/ggerganov/llama.cpp/releases".to_string()
        }
    }
    /// Quick check if ready to use
    pub fn is_ready(&mut self) -> bool {
        // Quick check if ready to use
        let mut status = self.get_status();
        (status.installed && !status.needs_update)
    }
}
