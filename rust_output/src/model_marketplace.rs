/// Core/model_marketplace::py — Model Marketplace for ZEN_RAG
/// 
/// Discover, browse, recommend, and download GGUF models from HuggingFace.
/// Hardware-aware recommendations filter models by your machine's capabilities.
/// 
/// Features:
/// - 8 curated "Staff Picks" with specialty tags & strength badges
/// - HuggingFace live search (cached 24h) — zero heavy deps (stdlib only)
/// - Trending models feed (cached 1h)
/// - Zero-dependency hardware detection (CPU, RAM, GPU, AVX2, NEON)
/// - Auto-tier classification: high/medium/low/minimal
/// - Smart recommendations: filters curated list by hardware tier
/// - Download from HuggingFace with progress callback
/// - Parse model filenames → params, quantization, RAM estimate, specialty
/// 
/// Ported from: C:\Users\Yo930\Desktop\_Python\Local_LLM
/// - Core/analysis/model_discovery.py  (search, trending, curated catalog)
/// - Core/services/hardware_detection.py (CPU, RAM, GPU profiling)
/// - Core/models::py  (HardwareProfile, ModelCapabilities, tiers)
/// 
/// Author : ZEN_RAG v4.8 — Model Marketplace
/// License: MIT

use anyhow::{Result, Context};
use regex::Regex;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static CURATED_MODELS: std::sync::LazyLock<Vec<HashMap<String, Box<dyn std::any::Any>>>> = std::sync::LazyLock::new(|| Vec::new());

pub const _CACHE_DIR: &str = "Path.home() / '.cache' / 'rag_rat' / 'hf_marketplace";

pub const _CACHE_TTL: i64 = 86400;

pub const _TRENDING_TTL: i64 = 3600;

pub const _HF_API: &str = "https://huggingface.co/api/models";

pub static _UA: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

pub static _MARKETPLACE: std::sync::LazyLock<Option<ModelMarketplace>> = std::sync::LazyLock::new(|| None);

pub static _MARKETPLACE_LOCK: std::sync::LazyLock<RLock> = std::sync::LazyLock::new(|| Default::default());

/// System hardware profile for LLM capacity planning.
/// 
/// Detected automatically by ``detect_hardware()``.
/// The ``tier`` property classifies the machine so we can
/// recommend compatible models without manual configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HardwareProfile {
    pub os_name: String,
    pub os_version: String,
    pub arch: String,
    pub cpu_brand: String,
    pub cpu_cores: i64,
    pub ram_gb: f64,
    pub available_ram_gb: f64,
    pub gpu_name: String,
    pub gpu_vram_gb: f64,
    pub avx2: bool,
    pub avx512: bool,
    pub neon: bool,
}

impl HardwareProfile {
    /// Capability tier: minimal | low | medium | high.
    /// 
    /// - high   : ≥8 GB VRAM  (GPU offload for 7B-13B+)
    /// - medium : <8 GB VRAM but ≥16 GB RAM + AVX2  (CPU-only up to 13B)
    /// - low    : 8-15 GB RAM + AVX2  (small quants only)
    /// - minimal: everything else  (tiny models only)
    pub fn tier(&self) -> &String {
        // Capability tier: minimal | low | medium | high.
        // 
        // - high   : ≥8 GB VRAM  (GPU offload for 7B-13B+)
        // - medium : <8 GB VRAM but ≥16 GB RAM + AVX2  (CPU-only up to 13B)
        // - low    : 8-15 GB RAM + AVX2  (small quants only)
        // - minimal: everything else  (tiny models only)
        if self.gpu_vram_gb >= 8 {
            "high".to_string()
        }
        if (self.ram_gb >= 16 && self.avx2) {
            "medium".to_string()
        }
        if (self.ram_gb >= 8 && self.avx2) {
            "low".to_string()
        }
        "minimal".to_string()
    }
    pub fn tier_label(&self) -> &String {
        let mut labels = HashMap::from([("high".to_string(), "🟢 High — GPU offload, 7B-13B+ models".to_string()), ("medium".to_string(), "🟡 Medium — 7B-13B models on CPU".to_string()), ("low".to_string(), "🟠 Low — small quants (Q2-Q4), ≤7B".to_string()), ("minimal".to_string(), "🔴 Minimal — tiny models only (≤1B)".to_string())]);
        labels.get(&self.tier).cloned().unwrap_or(self.tier)
    }
    pub fn tier_emoji(&self) -> &String {
        HashMap::from([("high".to_string(), "🟢".to_string()), ("medium".to_string(), "🟡".to_string()), ("low".to_string(), "🟠".to_string()), ("minimal".to_string(), "🔴".to_string())]).get(&self.tier).cloned().unwrap_or("⚪".to_string())
    }
    pub fn recommended_gpu_layers(&self) -> i64 {
        let mut gpu = self.gpu_name.to_lowercase();
        if ("nvidia".to_string(), "geforce".to_string(), "rtx".to_string(), "gtx".to_string(), "quadro".to_string(), "tesla".to_string()).iter().map(|k| gpu.contains(&k)).collect::<Vec<_>>().iter().any(|v| *v) {
            -1
        }
        if ("radeon rx".to_string(), "radeon pro".to_string(), "rocm".to_string()).iter().map(|k| gpu.contains(&k)).collect::<Vec<_>>().iter().any(|v| *v) {
            -1
        }
        if (gpu.contains(&"metal".to_string()) || self.neon) {
            -1
        }
        0
    }
    pub fn to_dict(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        HashMap::from([("os_name".to_string(), self.os_name), ("os_version".to_string(), self.os_version), ("arch".to_string(), self.arch), ("cpu_brand".to_string(), self.cpu_brand), ("cpu_cores".to_string(), self.cpu_cores), ("ram_gb".to_string(), ((self.ram_gb as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("available_ram_gb".to_string(), ((self.available_ram_gb as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("gpu_name".to_string(), self.gpu_name), ("gpu_vram_gb".to_string(), ((self.gpu_vram_gb as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("avx2".to_string(), self.avx2), ("avx512".to_string(), self.avx512), ("neon".to_string(), self.neon), ("tier".to_string(), self.tier), ("tier_label".to_string(), self.tier_label), ("recommended_gpu_layers".to_string(), self.recommended_gpu_layers)])
    }
}

/// Top-level orchestrator for the Model Marketplace.
/// 
/// Combines hardware detection, curated catalog, HF search,
/// and local model scanning into one unified interface.
#[derive(Debug, Clone)]
pub struct ModelMarketplace {
    pub _instance: Option<serde_json::Value>,
}

impl ModelMarketplace {
    pub fn __new__(&self, cls: String) -> () {
        let _ctx = cls._lock;
        {
            if cls._instance.is_none() {
                cls._instance = r#super().__new__(cls);
                cls._instance._initialized = false;
            }
            cls._instance
        }
    }
    pub fn new() -> Self {
        Self {
            _instance: None,
        }
    }
    /// Get cached hardware profile (refreshes every 5 min).
    pub fn get_hardware(&mut self, force_refresh: bool) -> HardwareProfile {
        // Get cached hardware profile (refreshes every 5 min).
        if (self._hardware.is_none() || force_refresh || (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - self._hardware_ts) > 300) {
            self._hardware = detect_hardware();
            self._hardware_ts = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        }
        self._hardware
    }
    /// Return all 8 curated Staff Picks.
    pub fn get_curated_models(&self) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Return all 8 curated Staff Picks.
        CURATED_MODELS.into_iter().collect::<Vec<_>>()
    }
    /// Filter curated models by hardware tier.
    pub fn get_recommended_for_hardware(&mut self) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Filter curated models by hardware tier.
        let mut hw = self.get_hardware();
        let mut tier = hw.tier;
        if tier == "high".to_string() {
            CURATED_MODELS.into_iter().collect::<Vec<_>>()
        } else if tier == "medium".to_string() {
            CURATED_MODELS.iter().filter(|m| m.get(&"min_ram_gb".to_string()).cloned().unwrap_or(0) <= hw.ram_gb).map(|m| m).collect::<Vec<_>>()
        } else if tier == "low".to_string() {
            CURATED_MODELS.iter().filter(|m| m.get(&"size_gb".to_string()).cloned().unwrap_or(0) <= 4.5_f64).map(|m| m).collect::<Vec<_>>()
        } else {
            CURATED_MODELS.iter().filter(|m| m.get(&"size_gb".to_string()).cloned().unwrap_or(0) <= 2.5_f64).map(|m| m).collect::<Vec<_>>()
        }
    }
    /// Filter curated models by category: coding, fast, balanced, large.
    pub fn get_models_by_category(&self, category: String) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Filter curated models by category: coding, fast, balanced, large.
        CURATED_MODELS.iter().filter(|m| m.get(&"category".to_string()).cloned() == category).map(|m| m).collect::<Vec<_>>()
    }
    /// Scan local directories for .gguf model files.
    pub fn scan_local_models(&mut self, model_dirs: Option<Vec<String>>) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Scan local directories for .gguf model files.
        if model_dirs.is_none() {
            let mut model_dirs = self._default_model_dirs();
        }
        let mut models = vec![];
        let mut seen = HashSet::new();
        for dir_str in model_dirs.iter() {
            let mut d = PathBuf::from(dir_str);
            if !d.exists() {
                continue;
            }
            for f in d.rglob("*.gguf".to_string()).iter() {
                if seen.contains(&f.name) {
                    continue;
                }
                seen.insert(f.name);
                let mut size_bytes = f.stat().st_size;
                let mut size_gb = (size_bytes / (1024).pow(3 as u32));
                let mut info = parse_model_info(f.name, size_gb);
                models::push(HashMap::from([("name".to_string(), f.file_stem().unwrap_or_default().to_str().unwrap_or("")), ("filename".to_string(), f.name), ("path".to_string(), f.to_string()), ("size_gb".to_string(), ((size_gb as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("size_bytes".to_string(), size_bytes)]));
            }
        }
        self._local_models = models;
        self._local_scan_ts = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64();
        models
    }
    /// Get last scan results (or scan if never done).
    pub fn get_local_models(&self) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Get last scan results (or scan if never done).
        if !self._local_models {
            self.scan_local_models();
        }
        self._local_models
    }
    /// Platform-aware default directories to scan for models.
    pub fn _default_model_dirs(&self) -> Vec<String> {
        // Platform-aware default directories to scan for models.
        let mut dirs = vec![];
        for candidate in vec![PathBuf::from("C:/AI/Models".to_string()), ((Path.home() / "AI".to_string()) / "Models".to_string()), (((Path.home() / ".cache".to_string()) / "lm-studio".to_string()) / "models".to_string()), ((Path.home() / ".ollama".to_string()) / "models".to_string()), (Path.home() / "models".to_string())].iter() {
            if candidate.exists() {
                dirs.push(candidate.to_string());
            }
        }
        dirs
    }
    /// Search HuggingFace for GGUF models.
    pub fn search(&self, query: String, limit: i64, sort: String) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Search HuggingFace for GGUF models.
        search_huggingface(query, limit, /* sort= */ sort)
    }
    /// Get trending GGUF models from HuggingFace.
    pub fn get_trending(&self, limit: i64) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
        // Get trending GGUF models from HuggingFace.
        get_trending_models(limit)
    }
    /// Download a model from HuggingFace.
    /// 
    /// Uses direct urllib download (no huggingface_hub required).
    /// Progress callback receives percentage (0-100).
    /// 
    /// Returns dict with: status, local_path, error.
    pub fn download_model(&mut self, repo_id: String, filename: String, target_dir: Option<String>, on_progress: Option<Box<dyn Fn(serde_json::Value)>>) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
        // Download a model from HuggingFace.
        // 
        // Uses direct urllib download (no huggingface_hub required).
        // Progress callback receives percentage (0-100).
        // 
        // Returns dict with: status, local_path, error.
        if target_dir.is_none() {
            let mut target_dir = ((Path.home() / "AI".to_string()) / "Models".to_string()).to_string();
        }
        let mut target = PathBuf::from(target_dir);
        target.create_dir_all();
        let mut dest = (target / filename);
        if dest.exists() {
            HashMap::from([("status".to_string(), "exists".to_string()), ("local_path".to_string(), dest.to_string()), ("error".to_string(), None)])
        }
        let mut url = format!("https://huggingface.co/{}/resolve/main/{}", repo_id, filename);
        let mut task_id = format!("{}/{}", repo_id, filename);
        self._download_tasks[task_id] = HashMap::from([("status".to_string(), "downloading".to_string()), ("progress".to_string(), 0.0_f64), ("started".to_string(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64())]);
        // try:
        {
            let _report = |block_num, block_size, total_size| {
                if total_size > 0 {
                    let mut pct = 100.0_f64.min((((block_num * block_size) * 100) / total_size));
                    self._download_tasks[&task_id]["progress".to_string()] = pct;
                    if on_progress {
                        on_progress(pct);
                    }
                }
            };
            urllib::request.urlretrieve(url, dest.to_string(), /* reporthook= */ _report);
            self._download_tasks[&task_id].extend(HashMap::from([("status".to_string(), "completed".to_string()), ("progress".to_string(), 100.0_f64)]));
            self.scan_local_models();
            HashMap::from([("status".to_string(), "completed".to_string()), ("local_path".to_string(), dest.to_string()), ("error".to_string(), None)])
        }
        // except Exception as e:
    }
    /// Get all download tasks with their status.
    pub fn get_download_tasks(&self) -> HashMap<String, HashMap<String, Box<dyn std::any::Any>>> {
        // Get all download tasks with their status.
        /* dict(self._download_tasks) */ HashMap::new()
    }
    /// Complete marketplace status for the UI.
    pub fn get_marketplace_summary(&mut self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Complete marketplace status for the UI.
        let mut hw = self.get_hardware();
        let mut local = self.get_local_models();
        let mut recommended = self.get_recommended_for_hardware();
        HashMap::from([("hardware".to_string(), hw.to_dict()), ("local_models_count".to_string(), local.len()), ("local_models".to_string(), local), ("curated_count".to_string(), CURATED_MODELS.len()), ("recommended_count".to_string(), recommended.len()), ("recommended_models".to_string(), recommended), ("active_downloads".to_string(), self._download_tasks.values().iter().filter(|t| t.get(&"status".to_string()).cloned() == "downloading".to_string()).map(|t| 1).collect::<Vec<_>>().iter().sum::<i64>())])
    }
}

pub fn _detect_cpu_brand() -> Result<String> {
    let mut system = platform.system();
    // try:
    {
        if system == "Windows".to_string() {
            // TODO: import winreg
            let mut key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0".to_string());
            let (mut name, _) = winreg.QueryValueEx(key, "ProcessorNameString".to_string());
            winreg.CloseKey(key);
            name.trim().to_string()
        } else if system == "Linux".to_string() {
            let mut f = File::open("/proc/cpuinfo".to_string())?;
            {
                for line in f.iter() {
                    if line.starts_with(&*"model name".to_string()) {
                        line.split(":".to_string(), 1)[1].trim().to_string()
                    }
                }
            }
        } else if system == "Darwin".to_string() {
            let mut out = subprocess::check_output(vec!["sysctl".to_string(), "-n".to_string(), "machdep.cpu.brand_string".to_string()], /* text= */ true, /* timeout= */ 5).trim().to_string();
            if out {
                out
            }
        }
    }
    // except Exception as exc:
    Ok((platform.processor() || "Unknown CPU".to_string()))
}

pub fn _detect_ram_gb() -> Result<f64> {
    let mut system = platform.system();
    // try:
    {
        if system == "Windows".to_string() {
            // TODO: import ctypes
            // TODO: nested class MEMORYSTATUSEX
            let mut mem = MEMORYSTATUSEX();
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX);
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem));
            (mem.ullTotalPhys / (1024).pow(3 as u32))
        } else if system == "Linux".to_string() {
            let mut f = File::open("/proc/meminfo".to_string())?;
            {
                for line in f.iter() {
                    if line.starts_with(&*"MemTotal".to_string()) {
                        let mut kb = regex::Regex::new(&"\\d+".to_string()).unwrap().is_match(&line).group().to_string().parse::<i64>().unwrap_or(0);
                        (kb / (1024).pow(2 as u32))
                    }
                }
            }
        } else if system == "Darwin".to_string() {
            let mut out = subprocess::check_output(vec!["sysctl".to_string(), "-n".to_string(), "hw.memsize".to_string()], /* text= */ true, /* timeout= */ 5).trim().to_string();
            (out.to_string().parse::<i64>().unwrap_or(0) / (1024).pow(3 as u32))
        }
    }
    // except Exception as exc:
    Ok(8.0_f64)
}

pub fn _detect_available_ram_gb() -> Result<f64> {
    let mut system = platform.system();
    // try:
    {
        if system == "Windows".to_string() {
            // TODO: import ctypes
            // TODO: nested class MEMORYSTATUSEX
            let mut mem = MEMORYSTATUSEX();
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX);
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem));
            (mem.ullAvailPhys / (1024).pow(3 as u32))
        } else if system == "Linux".to_string() {
            let mut f = File::open("/proc/meminfo".to_string())?;
            {
                for line in f.iter() {
                    if line.starts_with(&*"MemAvailable".to_string()) {
                        let mut kb = regex::Regex::new(&"\\d+".to_string()).unwrap().is_match(&line).group().to_string().parse::<i64>().unwrap_or(0);
                        (kb / (1024).pow(2 as u32))
                    }
                }
            }
        } else if system == "Darwin".to_string() {
            let mut total = _detect_ram_gb();
            (total * 0.5_f64)
        }
    }
    // except Exception as exc:
    Ok((_detect_ram_gb() * 0.5_f64))
}

/// Detect GPU name and VRAM.  Checks: NVIDIA → AMD → Apple Metal → WMI.
pub fn _detect_gpu() -> Result<(String, f64)> {
    // Detect GPU name and VRAM.  Checks: NVIDIA → AMD → Apple Metal → WMI.
    // try:
    {
        let mut out = subprocess::check_output(vec!["nvidia-smi".to_string(), "--query-gpu=name,memory.total".to_string(), "--format=csv,noheader,nounits".to_string()], /* text= */ true, /* timeout= */ 10, /* stderr= */ subprocess::DEVNULL).trim().to_string();
        if out {
            let mut parts = out.split(",".to_string()).map(|s| s.to_string()).collect::<Vec<String>>();
            let mut name = parts[0].trim().to_string();
            let mut vram_mb = if parts.len() > 1 { parts[1].trim().to_string().to_string().parse::<f64>().unwrap_or(0.0) } else { 0 };
            (format!("NVIDIA {}", name), (vram_mb / 1024))
        }
    }
    // except Exception as exc:
    // try:
    {
        let mut out = subprocess::check_output(vec!["rocm-smi".to_string(), "--showmeminfo".to_string(), "vram".to_string()], /* text= */ true, /* timeout= */ 10, /* stderr= */ subprocess::DEVNULL);
        if out.contains(&"Total".to_string()) {
            let mut m = regex::Regex::new(&"Total Memory.*?(\\d+)".to_string()).unwrap().is_match(&out);
            let mut vram = if m { (m.group(1).to_string().parse::<i64>().unwrap_or(0) / (1024).pow(2 as u32)) } else { 0 };
            ("AMD GPU (ROCm)".to_string(), vram)
        }
    }
    // except Exception as exc:
    if (platform.system() == "Darwin".to_string() && platform.machine().to_lowercase().contains(&"arm".to_string())) {
        let mut ram = _detect_ram_gb();
        (format!("Apple {} (Metal)", platform.machine()), (ram * 0.75_f64))
    }
    if platform.system() == "Windows".to_string() {
        // try:
        {
            let mut out = subprocess::check_output(vec!["powershell".to_string(), "-NoProfile".to_string(), "-Command".to_string(), "(Get-CimInstance Win32_VideoController).Name".to_string()], /* text= */ true, /* timeout= */ 10, /* stderr= */ subprocess::DEVNULL, /* encoding= */ "utf-8".to_string(), /* errors= */ "replace".to_string()).trim().to_string();
            if out {
                let mut names = out.lines().map(|s| s.to_string()).collect::<Vec<String>>().iter().filter(|n| n.trim().to_string()).map(|n| n.trim().to_string()).collect::<Vec<_>>();
                let mut discrete = names.iter().filter(|n| !("microsoft basic".to_string(), "virtual".to_string(), "remote".to_string()).iter().map(|x| n.to_lowercase().contains(&x)).collect::<Vec<_>>().iter().any(|v| *v)).map(|n| n).collect::<Vec<_>>();
                let mut gpu_name = if discrete { discrete[0] } else { names[0] };
                (gpu_name, 0.0_f64)
            }
        }
        // except Exception as exc:
    }
    Ok(("none".to_string(), 0.0_f64))
}

pub fn _detect_avx() -> Result<(bool, bool)> {
    let mut system = platform.system();
    let (mut avx2, mut avx512) = (false, false);
    // try:
    {
        if system == "Windows".to_string() {
            // TODO: import winreg
            let mut key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0".to_string());
            let (mut ident, _) = winreg.QueryValueEx(key, "Identifier".to_string());
            winreg.CloseKey(key);
            let mut m = regex::Regex::new(&"Model\\s+(\\d+)".to_string()).unwrap().is_match(&ident);
            if m {
                let mut model = m.group(1).to_string().parse::<i64>().unwrap_or(0);
                if model >= 60 {
                    let mut avx2 = true;
                }
                if model >= 85 {
                    let mut avx512 = true;
                }
            }
        } else if system == "Linux".to_string() {
            let mut f = File::open("/proc/cpuinfo".to_string())?;
            {
                let mut text = f.read();
            }
            let mut avx2 = text.contains(&"avx2".to_string());
            let mut avx512 = text.contains(&"avx512".to_string());
        } else if system == "Darwin".to_string() {
            let mut out = subprocess::check_output(vec!["sysctl".to_string(), "-a".to_string()], /* text= */ true, /* timeout= */ 5, /* stderr= */ subprocess::DEVNULL);
            let mut avx2 = out.contains(&"hw.optional.avx2_0: 1".to_string());
            let mut avx512 = (out.contains(&"hw.optional.avx512".to_string()) && out.contains(&": 1".to_string()));
        }
    }
    // except Exception as exc:
    Ok((avx2, avx512))
}

/// Auto-detect the full hardware profile of this machine.  Never raises.
pub fn detect_hardware() -> HardwareProfile {
    // Auto-detect the full hardware profile of this machine.  Never raises.
    let mut os_name = platform.system();
    let mut os_version = platform.release();
    let mut arch = platform.machine();
    let mut cpu_brand = _detect_cpu_brand();
    let mut cpu_cores = (os::cpu_count() || 1);
    let mut ram_gb = _detect_ram_gb();
    let mut available_ram_gb = _detect_available_ram_gb();
    let (mut gpu_name, mut gpu_vram) = _detect_gpu();
    let (mut avx2, mut avx512) = _detect_avx();
    let mut neon = (arch.to_lowercase().contains(&"aarch64".to_string()) || arch.to_lowercase().contains(&"arm64".to_string()));
    let mut hw = HardwareProfile(/* os_name= */ os_name, /* os_version= */ os_version, /* arch= */ arch, /* cpu_brand= */ cpu_brand, /* cpu_cores= */ cpu_cores, /* ram_gb= */ ram_gb, /* available_ram_gb= */ available_ram_gb, /* gpu_name= */ gpu_name, /* gpu_vram_gb= */ gpu_vram, /* avx2= */ avx2, /* avx512= */ avx512, /* neon= */ neon);
    logger.info("Hardware: %s, %d cores, %.1f GB RAM, GPU=%s (%.1f GB), AVX2=%s, tier=%s".to_string(), cpu_brand, cpu_cores, ram_gb, gpu_name, gpu_vram, avx2, hw.tier);
    hw
}

/// Parse a GGUF filename and return human-readable metadata.
pub fn parse_model_info(model_name: String, file_size_gb: f64) -> HashMap<String, Box<dyn std::any::Any>> {
    // Parse a GGUF filename and return human-readable metadata.
    let mut info = HashMap::from([("parameters".to_string(), "Unknown".to_string()), ("quantization".to_string(), "".to_string()), ("ram_estimate".to_string(), "Unknown".to_string()), ("speed_rating".to_string(), "⚡".to_string()), ("quality_rating".to_string(), "⭐⭐⭐".to_string()), ("best_for".to_string(), "General chat".to_string())]);
    let mut pm = regex::Regex::new(&"(\\d+\\.?\\d*)\\s*[BbMm](?![a-z])".to_string()).unwrap().is_match(&model_name);
    if pm {
        let mut num = pm.group(1).to_string().parse::<f64>().unwrap_or(0.0);
        let mut unit = pm.group(0)[-1].to_uppercase();
        let mut billions = if unit == "M".to_string() { (num / 1000) } else { num };
        info["parameters".to_string()] = format!("{}{}", num, unit);
        let mut est_ram = ((billions * 0.7_f64) + 0.5_f64);
        if est_ram < 4 {
            info["ram_estimate".to_string()] = format!("~{} GB", 1.max(est_ram.to_string().parse::<i64>().unwrap_or(0)));
            info["speed_rating".to_string()] = "⚡⚡⚡ Fast".to_string();
        } else if est_ram < 8 {
            info["ram_estimate".to_string()] = format!("~{} GB", est_ram.to_string().parse::<i64>().unwrap_or(0));
            info["speed_rating".to_string()] = "⚡⚡ Balanced".to_string();
        } else if est_ram < 16 {
            info["ram_estimate".to_string()] = format!("~{} GB", est_ram.to_string().parse::<i64>().unwrap_or(0));
            info["speed_rating".to_string()] = "⚡ Moderate".to_string();
        } else {
            info["ram_estimate".to_string()] = ">16 GB".to_string();
            info["speed_rating".to_string()] = "🐢 Heavy".to_string();
        }
    }
    let mut qm = regex::Regex::new(&"[Qq](\\d+)(?:_K_[MSL]|_\\d)?".to_string()).unwrap().is_match(&model_name);
    if qm {
        let mut q = qm.group(1).to_string().parse::<i64>().unwrap_or(0);
        info["quantization".to_string()] = qm.group(0).to_uppercase();
        if q <= 3 {
            info["quality_rating".to_string()] = "⭐⭐".to_string();
        } else if q == 4 {
            info["quality_rating".to_string()] = "⭐⭐⭐⭐ Recommended".to_string();
        } else if q >= 5 {
            info["quality_rating".to_string()] = "⭐⭐⭐⭐⭐".to_string();
        }
    }
    let mut nl = model_name.to_lowercase();
    if (nl.contains(&"coder".to_string()) || nl.contains(&"code".to_string())) {
        info["best_for".to_string()] = "💻 Coding & programming".to_string();
    } else if nl.contains(&"instruct".to_string()) {
        info["best_for".to_string()] = "💬 Instruction following".to_string();
    } else if nl.contains(&"chat".to_string()) {
        info["best_for".to_string()] = "💬 Conversation".to_string();
    } else if nl.contains(&"math".to_string()) {
        info["best_for".to_string()] = "🔢 Mathematics".to_string();
    }
    info["explanation".to_string()] = format!("{} params • {} • {}", info["parameters".to_string()], (info["quantization".to_string()] || "?".to_string()), info["ram_estimate".to_string()]);
    info
}

pub fn _ensure_cache_dir() -> Result<()> {
    // try:
    {
        _CACHE_DIR.create_dir_all();
    }
    // except Exception as exc:
}

pub fn _cache_path(key: String) -> PathBuf {
    let mut safe = regex::Regex::new(&"[^\\w\\-.]".to_string()).unwrap().replace_all(&"_".to_string(), key).to_string();
    (_CACHE_DIR / format!("{}.json", safe))
}

pub fn _read_cache(key: String, ttl: i64) -> Result<Option<Box<dyn std::any::Any>>> {
    let mut p = _cache_path(key);
    if !p.exists() {
        None
    }
    // try:
    {
        let mut data = serde_json::from_str(&p.read_to_string())).unwrap();
        if (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - data.get(&"_ts".to_string()).cloned().unwrap_or(0)) < ttl {
            data.get(&"payload".to_string()).cloned()
        }
    }
    // except Exception as exc:
    Ok(None)
}

pub fn _write_cache(key: String, payload: Box<dyn std::any::Any>) -> Result<()> {
    _ensure_cache_dir();
    // try:
    {
        _cache_path(key)std::fs::write(&serde_json::to_string(&HashMap::from([("_ts".to_string(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64()), ("payload".to_string(), payload)])).unwrap(), /* encoding= */ "utf-8".to_string());
    }
    // except Exception as exc:
}

pub fn _hf_get(params: HashMap<String, Box<dyn std::any::Any>>, timeout: i64) -> Result<Vec<HashMap>> {
    let mut qs = params.iter().iter().map(|(k, v)| format!("{}={}", k, v)).collect::<Vec<_>>().join(&"&".to_string());
    let mut url = format!("{}?{}", _HF_API, qs);
    let mut req = urllib::request.Request(url, /* headers= */ _UA);
    // try:
    {
        let mut r = urllib::request.urlopen(req, /* timeout= */ timeout);
        {
            serde_json::from_str(&r.read()).unwrap()
        }
    }
    // except Exception as e:
}

/// true when RAG_LOCAL_ONLY=1: skip HuggingFace API calls (return cache only or []).
pub fn _local_only_skip_hf() -> Result<bool> {
    // true when RAG_LOCAL_ONLY=1: skip HuggingFace API calls (return cache only or []).
    // try:
    {
        // TODO: from config_system import config
        /* getattr */ false
    }
    // except Exception as _e:
}

/// Search HuggingFace for GGUF models. Cached 24h. When RAG_LOCAL_ONLY=1, no API call (cache or []).
pub fn search_huggingface(query: String, limit: i64) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
    // Search HuggingFace for GGUF models. Cached 24h. When RAG_LOCAL_ONLY=1, no API call (cache or []).
    if (!query || !query.trim().to_string()) {
        vec![]
    }
    let mut cache_key = format!("hf_search_{}_{}_{}", query, limit, sort);
    let mut cached = _read_cache(cache_key);
    if cached.is_some() {
        cached
    }
    if _local_only_skip_hf() {
        vec![]
    }
    let mut raw = _hf_get(HashMap::from([("search".to_string(), query), ("filter".to_string(), "gguf".to_string()), ("sort".to_string(), sort), ("direction".to_string(), "-1".to_string()), ("limit".to_string(), limit.to_string())]));
    let mut results = vec![];
    for m in raw.iter() {
        let mut mid = m.get(&"id".to_string()).cloned().unwrap_or("".to_string());
        let mut entry = HashMap::from([("id".to_string(), mid), ("repo".to_string(), mid), ("name".to_string(), if mid.contains(&"/".to_string()) { mid.split("/".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[-1] } else { mid }), ("author".to_string(), if mid.contains(&"/".to_string()) { mid.split("/".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0] } else { "".to_string() }), ("downloads".to_string(), m.get(&"downloads".to_string()).cloned().unwrap_or(0)), ("likes".to_string(), m.get(&"likes".to_string()).cloned().unwrap_or(0)), ("last_modified".to_string(), (m.get(&"lastModified".to_string()).cloned() || "".to_string())[..10]), ("pipeline_tag".to_string(), m.get(&"pipeline_tag".to_string()).cloned().unwrap_or("".to_string())), ("tags".to_string(), m.get(&"tags".to_string()).cloned().unwrap_or(vec![])[..12])]);
        entry.extend(parse_model_info(mid));
        results.push(entry);
    }
    _write_cache(cache_key, results);
    results
}

/// Fetch currently trending GGUF models.  Cached 1h.
pub fn get_trending_models(limit: i64) -> Vec<HashMap<String, Box<dyn std::any::Any>>> {
    // Fetch currently trending GGUF models.  Cached 1h.
    let mut cache_key = format!("hf_trending_{}", limit);
    let mut cached = _read_cache(cache_key, /* ttl= */ _TRENDING_TTL);
    if cached.is_some() {
        cached
    }
    let mut raw = _hf_get(HashMap::from([("search".to_string(), "gguf".to_string()), ("sort".to_string(), "trending".to_string()), ("direction".to_string(), "-1".to_string()), ("limit".to_string(), (limit * 3).to_string()), ("filter".to_string(), "gguf".to_string())]));
    let mut results = vec![];
    for m in raw.iter() {
        let mut dl = m.get(&"downloads".to_string()).cloned().unwrap_or(0);
        if dl < 500 {
            continue;
        }
        let mut mid = m.get(&"id".to_string()).cloned().unwrap_or("".to_string());
        let mut entry = HashMap::from([("id".to_string(), mid), ("repo".to_string(), mid), ("name".to_string(), if mid.contains(&"/".to_string()) { mid.split("/".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[-1] } else { mid }), ("author".to_string(), if mid.contains(&"/".to_string()) { mid.split("/".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0] } else { "".to_string() }), ("downloads".to_string(), dl), ("likes".to_string(), m.get(&"likes".to_string()).cloned().unwrap_or(0)), ("last_modified".to_string(), (m.get(&"lastModified".to_string()).cloned() || "".to_string())[..10]), ("pipeline_tag".to_string(), m.get(&"pipeline_tag".to_string()).cloned().unwrap_or("".to_string())), ("tags".to_string(), m.get(&"tags".to_string()).cloned().unwrap_or(vec![])[..12]), ("trending".to_string(), true)]);
        entry.extend(parse_model_info(mid));
        results.push(entry);
        if results.len() >= limit {
            break;
        }
    }
    _write_cache(cache_key, results);
    results
}

/// Add popularity_tier and freshness to a model dict.  Mutates in place.
pub fn enrich_with_popularity(model: HashMap<String, Box<dyn std::any::Any>>) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
    // Add popularity_tier and freshness to a model dict.  Mutates in place.
    let mut dl = model.get(&"downloads".to_string()).cloned().unwrap_or(0);
    if /* /* isinstance(dl, str) */ */ true {
        model.entry("popularity_tier".to_string()).or_insert("popular".to_string());
    } else if dl > 500000 {
        model["popularity_tier".to_string()] = "trending".to_string();
    } else if dl > 100000 {
        model["popularity_tier".to_string()] = "popular".to_string();
    } else if dl > 10000 {
        model["popularity_tier".to_string()] = "established".to_string();
    } else {
        model["popularity_tier".to_string()] = "niche".to_string();
    }
    let mut lm = model.get(&"last_modified".to_string()).cloned().unwrap_or("".to_string());
    if lm {
        // try:
        {
            let mut dt = datetime::fromisoformat(lm.replace(&*"Z".to_string(), &*"+00:00".to_string()));
            let mut age = (datetime::now(dt.tzinfo) - dt).days;
        }
        // except Exception as _e:
        if age < 30 {
            model["freshness".to_string()] = "🔥 Hot".to_string();
        } else if age < 90 {
            model["freshness".to_string()] = "🆕 New".to_string();
        } else if age < 365 {
            model["freshness".to_string()] = "✅ Current".to_string();
        } else {
            model["freshness".to_string()] = "📦 Stable".to_string();
        }
    }
    Ok(model)
}

pub fn fmt_downloads(n: String) -> String {
    if /* /* isinstance(n, str) */ */ true {
        n
    }
    if n >= 1000000 {
        format!("{:.1}M", (n / 1000000))
    }
    if n >= 1000 {
        format!("{:.0}K", (n / 1000))
    }
    n.to_string()
}

pub fn fmt_likes(n: String) -> String {
    if /* /* isinstance(n, str) */ */ true {
        n
    }
    if n >= 1000 {
        format!("{:.1}K", (n / 1000))
    }
    n.to_string()
}

pub fn fmt_size(gb: f64) -> String {
    if gb < 1 {
        format!("{:.0} MB", (gb * 1024))
    }
    format!("{:.1} GB", gb)
}

/// Get the singleton ModelMarketplace instance.
pub fn get_marketplace() -> ModelMarketplace {
    // Get the singleton ModelMarketplace instance.
    // global/nonlocal _marketplace
    if _marketplace.is_none() {
        let _ctx = _marketplace_lock;
        {
            if _marketplace.is_none() {
                let mut _marketplace = ModelMarketplace();
            }
        }
    }
    _marketplace
}
