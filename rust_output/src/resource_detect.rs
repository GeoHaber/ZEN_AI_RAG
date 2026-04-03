/// resource_detect::py - Dedicated Hardware Discovery Module
/// ======================================================
/// The "Senses" of ZenAI. Detects CPU, GPU, and VRAM capabilities
/// to optimize the "Brain" (LLM Engine).

use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Detects available hardware resources for AI Inference.
#[derive(Debug, Clone)]
pub struct HardwareProfiler {
}

impl HardwareProfiler {
    /// Get FREE VRAM in MiB using nvidia-smi.
    pub fn _get_nvidia_vram() -> Result<i64> {
        // Get FREE VRAM in MiB using nvidia-smi.
        // try:
        {
            let mut creation_flags = if sys::platform == "win32".to_string() { subprocess::CREATE_NO_WINDOW } else { 0 };
            let mut out = subprocess::check_output(vec!["nvidia-smi".to_string(), "--query-gpu=memory.free".to_string(), "--format=csv,noheader,nounits".to_string()], /* encoding= */ "utf-8".to_string(), /* creationflags= */ creation_flags, /* shell= */ false);
            out.trim().to_string().split("\n".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[0].to_string().parse::<i64>().unwrap_or(0)
        }
        // except Exception as _e:
    }
    /// Scan system for CPU threads and GPU VRAM.
    /// Returns dict: {
    /// "type": "CPU" | "NVIDIA" | "AMD",
    /// "ram_gb": float,
    /// "vram_mb": int (Total/Estimated),
    /// "free_vram_mb": int (Actual Free),
    /// "threads": int (Physical Cores)
    /// }
    pub fn get_profile() -> Result<HashMap> {
        // Scan system for CPU threads and GPU VRAM.
        // Returns dict: {
        // "type": "CPU" | "NVIDIA" | "AMD",
        // "ram_gb": float,
        // "vram_mb": int (Total/Estimated),
        // "free_vram_mb": int (Actual Free),
        // "threads": int (Physical Cores)
        // }
        let mut cpu_threads = (os::cpu_count() || 4);
        if psutil {
            // try:
            {
                let mut phy_cores = psutil.cpu_count(/* logical= */ false);
                if phy_cores {
                    let mut cpu_threads = phy_cores;
                }
            }
            // except Exception as _e:
        }
        let mut profile = HashMap::from([("type".to_string(), "CPU".to_string()), ("ram_gb".to_string(), 8.0_f64), ("vram_mb".to_string(), 0), ("free_vram_mb".to_string(), 0), ("threads".to_string(), cpu_threads)]);
        // try:
        {
            if psutil {
                profile["ram_gb".to_string()] = (((psutil.virtual_memory().total / (1024).pow(3 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1);
            }
            if sys::platform == "win32".to_string() {
                let mut free_vram = HardwareProfiler._get_nvidia_vram();
                if free_vram > 0 {
                    profile["type".to_string()] = "NVIDIA".to_string();
                    profile["free_vram_mb".to_string()] = free_vram;
                    profile["vram_mb".to_string()] = free_vram;
                } else {
                    let mut cmd = "powershell -NoProfile -Command \"Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json\"".to_string();
                    let mut out = subprocess::check_output(cmd, /* shell= */ false, /* text= */ true, /* stderr= */ subprocess::DEVNULL, /* timeout= */ 3).trim().to_string();
                    if out {
                        // TODO: import json
                        let mut gpus = serde_json::from_str(&out).unwrap();
                        if !/* /* isinstance(gpus, list) */ */ true {
                            let mut gpus = vec![gpus];
                        }
                        for g in gpus.iter() {
                            let mut name = g.get(&"Name".to_string()).cloned().unwrap_or("".to_string()).to_uppercase();
                            let mut ram = (g.get(&"AdapterRAM".to_string()).cloned().unwrap_or(0) || 0);
                            let mut ram_mb = (ram / (1024).pow(2 as u32));
                            if name.contains(&"NVIDIA".to_string()) {
                                profile["type".to_string()] = "NVIDIA".to_string();
                                profile["vram_mb".to_string()] = ram_mb;
                                break;
                            } else if (name.contains(&"AMD".to_string()) || name.contains(&"RADEON".to_string())) {
                                profile["type".to_string()] = "AMD".to_string();
                                profile["vram_mb".to_string()] = ram_mb;
                                break;
                            }
                        }
                    }
                }
            }
        }
        // except (subprocess::SubprocessError, ValueError, KeyError, OSError, ImportError) as _e:
        logger.info(format!("[Profiler] Detected: {} | {}GB RAM | {}MB Free VRAM | {} Threads", profile["type".to_string()], profile["ram_gb".to_string()], profile["free_vram_mb".to_string()], profile["threads".to_string()]));
        Ok(profile)
    }
}
