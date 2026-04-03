/// Hardware detection and GPU presets.
/// 
/// Extracted from api_server::py.

use anyhow::{Result, Context};
use crate::helpers::{get_llm, get_state};
use std::collections::HashMap;

pub static GPU_PRESETS: std::sync::LazyLock<HashMap<String, serde_json::Value>> = std::sync::LazyLock::new(|| HashMap::new());

/// Quick hardware fingerprint for /health — cached after first call.
pub fn detect_hardware_summary() -> Result<Option<HashMap<String, Box<dyn std::any::Any>>>> {
    // Quick hardware fingerprint for /health — cached after first call.
    if /* hasattr(detect_hardware_summary, "_cached".to_string()) */ true {
        detect_hardware_summary._cached
    }
    let mut hw = HashMap::new();
    // try:
    {
        // TODO: import psutil
        let mut vm = psutil.virtual_memory();
        hw["ram_total_gb".to_string()] = (((vm.total / (1024).pow(3 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1);
        hw["ram_available_gb".to_string()] = (((vm.available / (1024).pow(3 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1);
        hw["cpu_count".to_string()] = psutil.cpu_count(/* logical= */ true);
        hw["cpu_physical".to_string()] = psutil.cpu_count(/* logical= */ false);
    }
    // except ImportError as exc:
    let mut state = get_state();
    if (state && state::ready) {
        let mut llm = get_llm();
        if (llm && /* hasattr(llm, "metadata".to_string()) */ true && llm.metadata) {
            let mut n_gpu = llm.metadata.get(&"n_gpu_layers".to_string()).cloned();
            if n_gpu.is_some() {
                hw["n_gpu_layers".to_string()] = n_gpu.to_string().parse::<i64>().unwrap_or(0);
            }
        }
    }
    detect_hardware_summary._cached = hw;
    Ok(hw)
}

/// Full hardware report for /v1/system/hardware.
pub fn detect_hardware_full() -> Result<HashMap<String, Box<dyn std::any::Any>>> {
    // Full hardware report for /v1/system/hardware.
    let mut hw = HashMap::from([("platform".to_string(), sys::platform)]);
    // try:
    {
        // TODO: import platform as _platform
        hw["machine".to_string()] = _platform.machine();
        hw["processor".to_string()] = (_platform.processor() || "unknown".to_string());
        hw["python_version".to_string()] = _platform.python_version();
    }
    // except Exception as exc:
    // try:
    {
        // TODO: import psutil
        let mut vm = psutil.virtual_memory();
        hw["ram".to_string()] = HashMap::from([("total_gb".to_string(), (((vm.total / (1024).pow(3 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("available_gb".to_string(), (((vm.available / (1024).pow(3 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("used_percent".to_string(), vm.percent)]);
        hw["cpu".to_string()] = HashMap::from([("logical_cores".to_string(), psutil.cpu_count(/* logical= */ true)), ("physical_cores".to_string(), psutil.cpu_count(/* logical= */ false)), ("freq_mhz".to_string(), if psutil.cpu_freq() { ((psutil.cpu_freq().current as f64) * 10f64.powi(0)).round() / 10f64.powi(0) } else { None })]);
        let mut phys = (psutil.cpu_count(/* logical= */ false) || 1);
        let mut logical = (psutil.cpu_count(/* logical= */ true) || 1);
        hw["cpu".to_string()]["hyperthreading".to_string()] = logical > phys;
    }
    // except ImportError as _e:
    let mut state = get_state();
    if (state && state::ready) {
        let mut llm = get_llm();
        let mut inner = if state { state::get_inner_adapter() } else { None };
        let mut gpu_info = HashMap::from([("n_gpu_layers".to_string(), 0)]);
        if (inner && /* hasattr(inner, "model_path".to_string()) */ true) {
            gpu_info["model_path".to_string()] = /* getattr */ None.to_string();
        }
        if llm {
            if /* hasattr(llm, "n_ctx".to_string()) */ true {
                gpu_info["context_length".to_string()] = llm.n_ctx();
            }
            if (/* hasattr(llm, "metadata".to_string()) */ true && llm.metadata) {
                let mut meta = llm.metadata;
                for key in ("general.file_type".to_string(), "general.quantization_version".to_string()).iter() {
                    let mut val = meta.get(&key).cloned();
                    if val.is_some() {
                        gpu_info[key.split(".".to_string()).map(|s| s.to_string()).collect::<Vec<String>>()[-1]] = val;
                    }
                }
            }
        }
        hw["model_gpu".to_string()] = gpu_info;
    }
    // try:
    {
        // TODO: import psutil
        let mut ram_gb = (psutil.virtual_memory().total / (1024).pow(3 as u32));
        if ram_gb < 8 {
            hw["recommendation".to_string()] = HashMap::from([("tier".to_string(), "potato".to_string()), ("max_model_params".to_string(), "3B dense / 7B MoE".to_string()), ("quant".to_string(), "Q4_K_S or IQ4_XS".to_string()), ("n_gpu_layers".to_string(), 0), ("tip".to_string(), "MoE models punch above their weight — try Qwen 30B-A3B".to_string())]);
        } else if ram_gb < 16 {
            hw["recommendation".to_string()] = HashMap::from([("tier".to_string(), "budget".to_string()), ("max_model_params".to_string(), "7B dense / 16B MoE".to_string()), ("quant".to_string(), "Q4_K_M".to_string()), ("n_gpu_layers".to_string(), -1), ("tip".to_string(), "Dual-channel RAM is mandatory for CPU inference bandwidth".to_string())]);
        } else if ram_gb < 32 {
            hw["recommendation".to_string()] = HashMap::from([("tier".to_string(), "mid_range".to_string()), ("max_model_params".to_string(), "14B dense / 30B MoE".to_string()), ("quant".to_string(), "Q5_K_M or Q4_K_M".to_string()), ("n_gpu_layers".to_string(), -1), ("tip".to_string(), "Sweet spot — try Qwen3-30B-A3B for best quality/speed".to_string())]);
        } else if ram_gb < 64 {
            hw["recommendation".to_string()] = HashMap::from([("tier".to_string(), "comfortable".to_string()), ("max_model_params".to_string(), "30B dense / 70B MoE".to_string()), ("quant".to_string(), "Q5_K_M or Q6_K".to_string()), ("n_gpu_layers".to_string(), -1), ("tip".to_string(), "Can run most models — quality quants recommended".to_string())]);
        } else {
            hw["recommendation".to_string()] = HashMap::from([("tier".to_string(), "rich".to_string()), ("max_model_params".to_string(), "70B+ dense / 120B+ MoE".to_string()), ("quant".to_string(), "Q6_K or Q8_0".to_string()), ("n_gpu_layers".to_string(), -1), ("tip".to_string(), "No limits — try GPT-OSS-120B MXFP4 for maximum quality".to_string())]);
        }
    }
    // except ImportError as exc:
    Ok(hw)
}
