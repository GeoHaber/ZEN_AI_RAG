/// ZEN_RAG Hardware Detection Module
/// ==================================
/// Single source of truth for hardware detection across all modules.
/// Consolidates duplicated code from utils::py, api_server::py, and startup/.
/// 
/// UNIFIED FUNCTIONS:
/// - get_hardware_profile()     : Cross-platform hardware detection
/// - detect_cpu()               : CPU vendor/cores detection
/// - detect_memory()            : RAM detection
/// - detect_gpu()               : GPU detection (Windows with VRAM)
/// - get_recommendation_tier()  : Model-size recommendation based on hardware
/// 
/// USAGE:
/// from utils_hardware import get_hardware_profile
/// hw = get_hardware_profile()
/// print(f"Running on {hw['cpu_vendor']} with {hw['ram_gb']}GB RAM")

use anyhow::{Result, Context};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Backward-compatible wrapper for legacy utils::py code.
#[derive(Debug, Clone)]
pub struct HardwareProfiler {
}

impl HardwareProfiler {
    /// Legacy method - use get_hardware_profile() instead.
    pub fn get_profile() -> HashMap {
        // Legacy method - use get_hardware_profile() instead.
        let mut profile = get_hardware_profile(/* detailed= */ false);
        HashMap::from([("type".to_string(), profile["cpu".to_string()]["vendor".to_string()]), ("ram_gb".to_string(), profile["memory".to_string()]["total_gb".to_string()]), ("vram_mb".to_string(), if profile["gpu".to_string()] { profile["gpu".to_string()]["vram_mb".to_string()] } else { 0 }), ("threads".to_string(), profile["cpu".to_string()]["logical_cores".to_string()]), ("gpu".to_string(), if profile["gpu".to_string()] { profile["gpu".to_string()]["name".to_string()] } else { None })])
    }
}

/// Detect CPU vendor, cores, frequency.
/// 
/// Returns:
/// Dict with keys: vendor, name, logical_cores, physical_cores, freq_mhz
pub fn detect_cpu() -> Result<HashMap<String, Box<dyn std::any::Any>>> {
    // Detect CPU vendor, cores, frequency.
    // 
    // Returns:
    // Dict with keys: vendor, name, logical_cores, physical_cores, freq_mhz
    let mut cpu_info = HashMap::from([("vendor".to_string(), "Unknown".to_string()), ("name".to_string(), (platform.processor() || "Unknown".to_string())), ("logical_cores".to_string(), (os::cpu_count() || 1)), ("physical_cores".to_string(), (os::cpu_count() || 1)), ("freq_mhz".to_string(), None)]);
    // try:
    {
        // TODO: import psutil
        let mut physical = psutil.cpu_count(/* logical= */ false);
        if physical {
            cpu_info["physical_cores".to_string()] = physical;
        }
        let mut freq = psutil.cpu_freq();
        if freq {
            cpu_info["freq_mhz".to_string()] = ((freq.current as f64) * 10f64.powi(0)).round() / 10f64.powi(0);
        }
    }
    // except ImportError as exc:
    let mut name_upper = cpu_info["name".to_string()].to_uppercase();
    if name_upper.contains(&"INTEL".to_string()) {
        cpu_info["vendor".to_string()] = "Intel".to_string();
    } else if name_upper.contains(&"AMD".to_string()) {
        cpu_info["vendor".to_string()] = "AMD".to_string();
    } else if name_upper.contains(&"ARM".to_string()) {
        cpu_info["vendor".to_string()] = "ARM".to_string();
    }
    Ok(cpu_info)
}

/// Detect RAM availability and usage.
/// 
/// Returns:
/// Dict with keys: total_gb, available_gb, used_percent
pub fn detect_memory() -> Result<HashMap<String, Box<dyn std::any::Any>>> {
    // Detect RAM availability and usage.
    // 
    // Returns:
    // Dict with keys: total_gb, available_gb, used_percent
    let mut mem_info = HashMap::from([("total_gb".to_string(), 8.0_f64), ("available_gb".to_string(), 4.0_f64), ("used_percent".to_string(), 50.0_f64)]);
    // try:
    {
        // TODO: import psutil
        let mut vm = psutil.virtual_memory();
        mem_info["total_gb".to_string()] = (((vm.total / (1024).pow(3 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1);
        mem_info["available_gb".to_string()] = (((vm.available / (1024).pow(3 as u32)) as f64) * 10f64.powi(1)).round() / 10f64.powi(1);
        mem_info["used_percent".to_string()] = vm.percent;
    }
    // except ImportError as _e:
    Ok(mem_info)
}

/// Detect dedicated GPU (Windows only with PowerShell/WMI).
/// 
/// Returns:
/// Dict with keys: vendor, name, vram_mb
/// Or None if no discrete GPU found
pub fn detect_gpu() -> Result<Option<HashMap<String, Box<dyn std::any::Any>>>> {
    // Detect dedicated GPU (Windows only with PowerShell/WMI).
    // 
    // Returns:
    // Dict with keys: vendor, name, vram_mb
    // Or None if no discrete GPU found
    if sys::platform != "win32".to_string() {
        None
    }
    // try:
    {
        let mut cmd = vec!["powershell".to_string(), "-NoProfile".to_string(), "-Command".to_string(), "Get-CimInstance Win32_VideoController | Where-Object {$_.Name -notmatch \"Remote|RDP\"} | Select-Object Name, AdapterRAM | ConvertTo-Json".to_string()];
        let mut output = subprocess::check_output(cmd, /* shell= */ false, /* text= */ true, /* stderr= */ subprocess::DEVNULL, /* timeout= */ 5).trim().to_string();
        if !output {
            None
        }
        let mut gpus = serde_json::from_str(&output).unwrap();
        if !/* /* isinstance(gpus, list) */ */ true {
            let mut gpus = vec![gpus];
        }
        for gpu_raw in gpus.iter() {
            let mut name = gpu_raw.get(&"Name".to_string()).cloned().unwrap_or("".to_string()).to_uppercase();
            if vec!["INTEL".to_string(), "BASIC".to_string(), "UHD".to_string(), "IRIS".to_string()].iter().map(|x| name.contains(&x)).collect::<Vec<_>>().iter().any(|v| *v) {
                continue;
            }
            let mut vram_bytes = gpu_raw.get(&"AdapterRAM".to_string()).cloned().unwrap_or(0);
            let mut vram_mb = 1.max((vram_bytes / (1024).pow(2 as u32)));
            let mut gpu_info = HashMap::from([("name".to_string(), gpu_raw.get(&"Name".to_string()).cloned().unwrap_or("Unknown".to_string())), ("vram_mb".to_string(), vram_mb), ("vendor".to_string(), "Unknown".to_string())]);
            if (name.contains(&"NVIDIA".to_string()) || name.contains(&"GEFORCE".to_string()) || name.contains(&"TESLA".to_string())) {
                gpu_info["vendor".to_string()] = "NVIDIA".to_string();
            } else if (name.contains(&"AMD".to_string()) || name.contains(&"RADEON".to_string()) || name.contains(&"EPYC".to_string())) {
                gpu_info["vendor".to_string()] = "AMD".to_string();
            } else if name.contains(&"INTEL".to_string()) {
                gpu_info["vendor".to_string()] = "Intel".to_string();
            }
            gpu_info
        }
    }
    // except Exception as e:
}

/// Recommend LLM tier based on hardware.
/// 
/// Args:
/// ram_gb: Total system RAM in GB
/// cpu_cores: Logical CPU cores
/// 
/// Returns:
/// Dict with: tier, max_model_params, quantization, n_gpu_layers, note
pub fn get_recommendation_tier(ram_gb: f64, cpu_cores: i64) -> HashMap<String, Box<dyn std::any::Any>> {
    // Recommend LLM tier based on hardware.
    // 
    // Args:
    // ram_gb: Total system RAM in GB
    // cpu_cores: Logical CPU cores
    // 
    // Returns:
    // Dict with: tier, max_model_params, quantization, n_gpu_layers, note
    if ram_gb < 4 {
        let mut tier = "potato".to_string();
        let mut max_params = "1B-3B".to_string();
        let mut quant = "Q4_K_S".to_string();
        let mut gpu_layers = 0;
        let mut note = "Very tight resources. Consider 1B models like TinyLlama".to_string();
    } else if ram_gb < 8 {
        let mut tier = "budget".to_string();
        let mut max_params = "3B-7B".to_string();
        let mut quant = "Q4_K_S or Q5_K_M".to_string();
        let mut gpu_layers = 0;
        let mut note = "Focus on 3B-7B quantized models".to_string();
    } else if ram_gb < 16 {
        let mut tier = "mid_range".to_string();
        let mut max_params = "7B-13B".to_string();
        let mut quant = "Q5_K_M or Q6_K".to_string();
        let mut gpu_layers = if ram_gb > 12 { 10 } else { 5 };
        let mut note = "Good range: 7B Mistral, Llama 2-7B".to_string();
    } else if ram_gb < 32 {
        let mut tier = "comfortable".to_string();
        let mut max_params = "13B-34B".to_string();
        let mut quant = "Q5_K_M, Q6_K, or Q8_0".to_string();
        let mut gpu_layers = if ram_gb > 24 { 20 } else { 15 };
        let mut note = "Can run larger models: Llama 2-13B, Mistral 7B without Q".to_string();
    } else {
        let mut tier = "rich".to_string();
        let mut max_params = "34B-70B+".to_string();
        let mut quant = "Q6_K, Q8_0, or full precision".to_string();
        let mut gpu_layers = 40;
        let mut note = "Plenty of resources: Llama 2-70B, Code Llama, Mixtral".to_string();
    }
    HashMap::from([("tier".to_string(), tier), ("ram_gb".to_string(), ram_gb), ("cpu_cores".to_string(), cpu_cores), ("max_model_params".to_string(), max_params), ("recommended_quant".to_string(), quant), ("n_gpu_layers".to_string(), gpu_layers), ("note".to_string(), note)])
}

/// Get complete hardware profile for ZEN_RAG.
/// 
/// Args:
/// detailed: If true, include recommendation tier and extra info
/// 
/// Returns:
/// Comprehensive hardware dictionary:
/// {
/// "platform": "Windows/Linux/Darwin",
/// "architecture": "x86_64/arm64/etc",
/// "cpu": {...},
/// "memory": {...},
/// "gpu": {...} or None,
/// "recommendation": {...} if detailed=true
/// }
pub fn get_hardware_profile(detailed: bool) -> HashMap<String, Box<dyn std::any::Any>> {
    // Get complete hardware profile for ZEN_RAG.
    // 
    // Args:
    // detailed: If true, include recommendation tier and extra info
    // 
    // Returns:
    // Comprehensive hardware dictionary:
    // {
    // "platform": "Windows/Linux/Darwin",
    // "architecture": "x86_64/arm64/etc",
    // "cpu": {...},
    // "memory": {...},
    // "gpu": {...} or None,
    // "recommendation": {...} if detailed=true
    // }
    let mut profile = HashMap::from([("platform".to_string(), sys::platform), ("architecture".to_string(), platform.machine()), ("cpu".to_string(), detect_cpu()), ("memory".to_string(), detect_memory()), ("gpu".to_string(), detect_gpu())]);
    if detailed {
        profile["recommendation".to_string()] = get_recommendation_tier(profile["memory".to_string()]["total_gb".to_string()], profile["cpu".to_string()]["logical_cores".to_string()]);
    }
    profile
}

/// Quick hardware summary for CLI tools (cached).
/// 
/// Used by: api_server /health endpoint
/// Returns minimal key info for status checks.
pub fn get_hardware_summary() -> HashMap<String, Box<dyn std::any::Any>> {
    // Quick hardware summary for CLI tools (cached).
    // 
    // Used by: api_server /health endpoint
    // Returns minimal key info for status checks.
    let mut profile = get_hardware_profile();
    let mut summary = HashMap::from([("ram_total_gb".to_string(), profile["memory".to_string()]["total_gb".to_string()]), ("ram_available_gb".to_string(), profile["memory".to_string()]["available_gb".to_string()]), ("cpu_count".to_string(), profile["cpu".to_string()]["logical_cores".to_string()]), ("cpu_physical".to_string(), profile["cpu".to_string()]["physical_cores".to_string()]), ("cpu_vendor".to_string(), profile["cpu".to_string()]["vendor".to_string()])]);
    if profile["gpu".to_string()] {
        summary["gpu_name".to_string()] = profile["gpu".to_string()]["name".to_string()];
        summary["gpu_vram_mb".to_string()] = profile["gpu".to_string()]["vram_mb".to_string()];
    }
    summary
}
