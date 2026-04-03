"""
ZEN_RAG Hardware Detection Module
==================================
Single source of truth for hardware detection across all modules.
Consolidates duplicated code from utils.py, api_server.py, and startup/.

UNIFIED FUNCTIONS:
    - get_hardware_profile()     : Cross-platform hardware detection
    - detect_cpu()               : CPU vendor/cores detection
    - detect_memory()            : RAM detection
    - detect_gpu()               : GPU detection (Windows with VRAM)
    - get_recommendation_tier()  : Model-size recommendation based on hardware

USAGE:
    from utils_hardware import get_hardware_profile
    hw = get_hardware_profile()
    print(f"Running on {hw['cpu_vendor']} with {hw['ram_gb']}GB RAM")
"""

import sys
import os
import platform
import subprocess
import json
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CPU DETECTION
# ============================================================================


def detect_cpu() -> Dict[str, Any]:
    """Detect CPU vendor, cores, frequency.

    Returns:
        Dict with keys: vendor, name, logical_cores, physical_cores, freq_mhz
    """
    cpu_info = {
        "vendor": "Unknown",
        "name": platform.processor() or "Unknown",
        "logical_cores": os.cpu_count() or 1,
        "physical_cores": os.cpu_count() or 1,
        "freq_mhz": None,
    }

    try:
        import psutil

        # Try to get physical core count (psutil has fallback)
        physical = psutil.cpu_count(logical=False)
        if physical:
            cpu_info["physical_cores"] = physical

        # Try to get CPU frequency
        freq = psutil.cpu_freq()
        if freq:
            cpu_info["freq_mhz"] = round(freq.current, 0)
    except ImportError as exc:
        logger.debug("%s", exc)

    # Vendor detection from name
    name_upper = cpu_info["name"].upper()
    if "INTEL" in name_upper:
        cpu_info["vendor"] = "Intel"
    elif "AMD" in name_upper:
        cpu_info["vendor"] = "AMD"
    elif "ARM" in name_upper:
        cpu_info["vendor"] = "ARM"

    return cpu_info


# ============================================================================
# MEMORY DETECTION
# ============================================================================


def detect_memory() -> Dict[str, Any]:
    """Detect RAM availability and usage.

    Returns:
        Dict with keys: total_gb, available_gb, used_percent
    """
    mem_info = {
        "total_gb": 8.0,  # Safe default
        "available_gb": 4.0,
        "used_percent": 50.0,
    }

    try:
        import psutil

        vm = psutil.virtual_memory()
        mem_info["total_gb"] = round(vm.total / (1024**3), 1)
        mem_info["available_gb"] = round(vm.available / (1024**3), 1)
        mem_info["used_percent"] = vm.percent
    except ImportError:
        logger.warning("psutil not available for detailed memory detection")

    return mem_info


# ============================================================================
# GPU DETECTION (Windows)
# ============================================================================


def detect_gpu() -> Optional[Dict[str, Any]]:
    """Detect dedicated GPU (Windows only with PowerShell/WMI).

    Returns:
        Dict with keys: vendor, name, vram_mb
        Or None if no discrete GPU found
    """
    if sys.platform != "win32":
        return None

    try:
        cmd = [
            "powershell", "-NoProfile", "-Command",
            'Get-CimInstance Win32_VideoController | '
            'Where-Object {$_.Name -notmatch "Remote|RDP"} | '
            'Select-Object Name, AdapterRAM | ConvertTo-Json',
        ]

        output = subprocess.check_output(cmd, shell=False, text=True, stderr=subprocess.DEVNULL, timeout=5).strip()

        if not output:
            return None

        gpus = json.loads(output)
        if not isinstance(gpus, list):
            gpus = [gpus]

        # Filter out integrated graphics
        for gpu_raw in gpus:
            name = gpu_raw.get("Name", "").upper()

            # Skip Intel iGPU and Microsoft Basic Display Adapter
            if any(x in name for x in ["INTEL", "BASIC", "UHD", "IRIS"]):
                continue

            vram_bytes = gpu_raw.get("AdapterRAM", 0)
            vram_mb = max(1, vram_bytes // (1024**2))  # At least 1MB

            gpu_info = {
                "name": gpu_raw.get("Name", "Unknown"),
                "vram_mb": vram_mb,
                "vendor": "Unknown",
            }

            # Detect vendor
            if "NVIDIA" in name or "GEFORCE" in name or "TESLA" in name:
                gpu_info["vendor"] = "NVIDIA"
            elif "AMD" in name or "RADEON" in name or "EPYC" in name:
                gpu_info["vendor"] = "AMD"
            elif "INTEL" in name:
                gpu_info["vendor"] = "Intel"

            return gpu_info

    except Exception as e:
        logger.debug(f"GPU detection failed: {e}")
        return None


# ============================================================================
# RECOMMENDATION ENGINE
# ============================================================================


def get_recommendation_tier(ram_gb: float, cpu_cores: int) -> Dict[str, Any]:
    """Recommend LLM tier based on hardware.

    Args:
        ram_gb: Total system RAM in GB
        cpu_cores: Logical CPU cores

    Returns:
        Dict with: tier, max_model_params, quantization, n_gpu_layers, note
    """

    # Tier decision logic
    if ram_gb < 4:
        tier = "potato"
        max_params = "1B-3B"
        quant = "Q4_K_S"
        gpu_layers = 0
        note = "Very tight resources. Consider 1B models like TinyLlama"

    elif ram_gb < 8:
        tier = "budget"
        max_params = "3B-7B"
        quant = "Q4_K_S or Q5_K_M"
        gpu_layers = 0
        note = "Focus on 3B-7B quantized models"

    elif ram_gb < 16:
        tier = "mid_range"
        max_params = "7B-13B"
        quant = "Q5_K_M or Q6_K"
        gpu_layers = 10 if ram_gb > 12 else 5
        note = "Good range: 7B Mistral, Llama 2-7B"

    elif ram_gb < 32:
        tier = "comfortable"
        max_params = "13B-34B"
        quant = "Q5_K_M, Q6_K, or Q8_0"
        gpu_layers = 20 if ram_gb > 24 else 15
        note = "Can run larger models: Llama 2-13B, Mistral 7B without Q"

    else:
        tier = "rich"
        max_params = "34B-70B+"
        quant = "Q6_K, Q8_0, or full precision"
        gpu_layers = 40  # Offload most layers
        note = "Plenty of resources: Llama 2-70B, Code Llama, Mixtral"

    return {
        "tier": tier,
        "ram_gb": ram_gb,
        "cpu_cores": cpu_cores,
        "max_model_params": max_params,
        "recommended_quant": quant,
        "n_gpu_layers": gpu_layers,
        "note": note,
    }


# ============================================================================
# MAIN API
# ============================================================================


def get_hardware_profile(detailed: bool = False) -> Dict[str, Any]:
    """Get complete hardware profile for ZEN_RAG.

    Args:
        detailed: If True, include recommendation tier and extra info

    Returns:
        Comprehensive hardware dictionary:
        {
            "platform": "Windows/Linux/Darwin",
            "architecture": "x86_64/arm64/etc",
            "cpu": {...},
            "memory": {...},
            "gpu": {...} or None,
            "recommendation": {...} if detailed=True
        }
    """

    profile = {
        "platform": sys.platform,
        "architecture": platform.machine(),
        "cpu": detect_cpu(),
        "memory": detect_memory(),
        "gpu": detect_gpu(),
    }

    if detailed:
        profile["recommendation"] = get_recommendation_tier(
            profile["memory"]["total_gb"], profile["cpu"]["logical_cores"]
        )

    return profile


def get_hardware_summary() -> Dict[str, Any]:
    """Quick hardware summary for CLI tools (cached).

    Used by: api_server /health endpoint
    Returns minimal key info for status checks.
    """
    profile = get_hardware_profile()

    summary = {
        "ram_total_gb": profile["memory"]["total_gb"],
        "ram_available_gb": profile["memory"]["available_gb"],
        "cpu_count": profile["cpu"]["logical_cores"],
        "cpu_physical": profile["cpu"]["physical_cores"],
        "cpu_vendor": profile["cpu"]["vendor"],
    }

    if profile["gpu"]:
        summary["gpu_name"] = profile["gpu"]["name"]
        summary["gpu_vram_mb"] = profile["gpu"]["vram_mb"]

    return summary


# ============================================================================
# FOR BACKWARD COMPATIBILITY
# ============================================================================


class HardwareProfiler:
    """Backward-compatible wrapper for legacy utils.py code."""

    @staticmethod
    def get_profile() -> dict:
        """Legacy method - use get_hardware_profile() instead."""
        profile = get_hardware_profile(detailed=False)

        # Transform to legacy format
        return {
            "type": profile["cpu"]["vendor"],
            "ram_gb": profile["memory"]["total_gb"],
            "vram_mb": profile["gpu"]["vram_mb"] if profile["gpu"] else 0,
            "threads": profile["cpu"]["logical_cores"],
            "gpu": profile["gpu"]["name"] if profile["gpu"] else None,
        }


if __name__ == "__main__":
    # CLI test
    print("\n" + "=" * 70)
    print("ZEN_RAG HARDWARE PROFILE")
    print("=" * 70)

    hw = get_hardware_profile(detailed=True)

    print("\n🖥️  PLATFORM")
    print(f"   OS: {hw['platform']}")
    print(f"   Arch: {hw['architecture']}")
    print("\n💻 CPU")
    print(f"   {hw['cpu']['name']}")
    print(f"   Vendor: {hw['cpu']['vendor']}")
    print(f"   Logical Cores: {hw['cpu']['logical_cores']}")
    print(f"   Physical Cores: {hw['cpu']['physical_cores']}")
    if hw["cpu"]["freq_mhz"]:
        print(f"   Frequency: {hw['cpu']['freq_mhz']} MHz")
        pass
    print("\n🧠 MEMORY")
    print(f"   Total: {hw['memory']['total_gb']} GB")
    print(f"   Available: {hw['memory']['available_gb']} GB")
    print(f"   Used: {hw['memory']['used_percent']}%")
    if hw["gpu"]:
        print("\n🎮 GPU (Discrete)")
        print(f"   {hw['gpu']['name']}")
        print(f"   Vendor: {hw['gpu']['vendor']}")
        print(f"   VRAM: {hw['gpu']['vram_mb']} MB")
    else:
        print("\n🎮 GPU: None (CPU only)")

    if "recommendation" in hw:
        rec = hw["recommendation"]
        print("\n🎯 RECOMMENDATION")
        print(f"   Tier: {rec['tier'].upper()}")
        print(f"   Max Model: {rec['max_model_params']}")
        print(f"   Quantization: {rec['recommended_quant']}")
        print(f"   GPU Layers: {rec['n_gpu_layers']}")
        print(f"   Note: {rec['note']}")
    print("\n" + "=" * 70 + "\n")
