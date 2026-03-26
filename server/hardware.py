"""
Hardware detection and GPU presets.

Extracted from api_server.py.
"""

import sys
from typing import Any, Dict, Optional

from server.helpers import get_llm, get_state


def detect_hardware_summary() -> Optional[Dict[str, Any]]:
    """Quick hardware fingerprint for /health — cached after first call."""
    if hasattr(detect_hardware_summary, "_cached"):
        return detect_hardware_summary._cached  # type: ignore

    hw: Dict[str, Any] = {}
    try:
        import psutil

        vm = psutil.virtual_memory()
        hw["ram_total_gb"] = round(vm.total / (1024**3), 1)
        hw["ram_available_gb"] = round(vm.available / (1024**3), 1)
        hw["cpu_count"] = psutil.cpu_count(logical=True)
        hw["cpu_physical"] = psutil.cpu_count(logical=False)
    except ImportError as exc:
        _ = exc  # suppressed intentionally

    state = get_state()
    if state and state.ready:
        llm = get_llm()
        if llm and hasattr(llm, "metadata") and llm.metadata:
            n_gpu = llm.metadata.get("n_gpu_layers")
            if n_gpu is not None:
                hw["n_gpu_layers"] = int(n_gpu)

    detect_hardware_summary._cached = hw  # type: ignore
    return hw


def detect_hardware_full() -> Dict[str, Any]:
    """Full hardware report for /v1/system/hardware."""
    hw: Dict[str, Any] = {"platform": sys.platform}

    try:
        import platform as _platform

        hw["machine"] = _platform.machine()
        hw["processor"] = _platform.processor() or "unknown"
        hw["python_version"] = _platform.python_version()
    except Exception as exc:
        _ = exc  # suppressed intentionally

    try:
        import psutil

        vm = psutil.virtual_memory()
        hw["ram"] = {
            "total_gb": round(vm.total / (1024**3), 1),
            "available_gb": round(vm.available / (1024**3), 1),
            "used_percent": vm.percent,
        }
        hw["cpu"] = {
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "freq_mhz": (round(psutil.cpu_freq().current, 0) if psutil.cpu_freq() else None),
        }
        phys = psutil.cpu_count(logical=False) or 1
        logical = psutil.cpu_count(logical=True) or 1
        hw["cpu"]["hyperthreading"] = logical > phys
    except ImportError:
        hw["ram"] = {"note": "psutil not installed"}

    state = get_state()
    if state and state.ready:
        llm = get_llm()
        inner = state.get_inner_adapter() if state else None
        gpu_info: Dict[str, Any] = {"n_gpu_layers": 0}

        if inner and hasattr(inner, "model_path"):
            gpu_info["model_path"] = str(getattr(inner, "model_path", None))

        if llm:
            if hasattr(llm, "n_ctx"):
                gpu_info["context_length"] = llm.n_ctx()
            if hasattr(llm, "metadata") and llm.metadata:
                meta = llm.metadata
                for key in ("general.file_type", "general.quantization_version"):
                    val = meta.get(key)
                    if val is not None:
                        gpu_info[key.split(".")[-1]] = val
        hw["model_gpu"] = gpu_info

    try:
        import psutil

        ram_gb = psutil.virtual_memory().total / (1024**3)
        if ram_gb < 8:
            hw["recommendation"] = {
                "tier": "potato",
                "max_model_params": "3B dense / 7B MoE",
                "quant": "Q4_K_S or IQ4_XS",
                "n_gpu_layers": 0,
                "tip": "MoE models punch above their weight — try Qwen 30B-A3B",
            }
        elif ram_gb < 16:
            hw["recommendation"] = {
                "tier": "budget",
                "max_model_params": "7B dense / 16B MoE",
                "quant": "Q4_K_M",
                "n_gpu_layers": -1,
                "tip": "Dual-channel RAM is mandatory for CPU inference bandwidth",
            }
        elif ram_gb < 32:
            hw["recommendation"] = {
                "tier": "mid_range",
                "max_model_params": "14B dense / 30B MoE",
                "quant": "Q5_K_M or Q4_K_M",
                "n_gpu_layers": -1,
                "tip": "Sweet spot — try Qwen3-30B-A3B for best quality/speed",
            }
        elif ram_gb < 64:
            hw["recommendation"] = {
                "tier": "comfortable",
                "max_model_params": "30B dense / 70B MoE",
                "quant": "Q5_K_M or Q6_K",
                "n_gpu_layers": -1,
                "tip": "Can run most models — quality quants recommended",
            }
        else:
            hw["recommendation"] = {
                "tier": "rich",
                "max_model_params": "70B+ dense / 120B+ MoE",
                "quant": "Q6_K or Q8_0",
                "n_gpu_layers": -1,
                "tip": "No limits — try GPT-OSS-120B MXFP4 for maximum quality",
            }
    except ImportError as exc:
        _ = exc  # suppressed intentionally

    return hw


GPU_PRESETS = {
    "potato": {
        "n_gpu_layers": 0,
        "n_ctx": 2048,
        "description": "CPU only, minimal context — for 4-8GB RAM systems",
    },
    "budget": {
        "n_gpu_layers": 0,
        "n_ctx": 4096,
        "description": "CPU only, standard context — for 8-16GB RAM systems",
    },
    "balanced": {
        "n_gpu_layers": 20,
        "n_ctx": 4096,
        "description": "Partial GPU offload — for 8GB VRAM + 16GB RAM",
    },
    "full_gpu": {
        "n_gpu_layers": -1,
        "n_ctx": 8192,
        "description": "Full GPU offload — for 16GB+ VRAM",
    },
    "max_context": {
        "n_gpu_layers": -1,
        "n_ctx": 32768,
        "description": "Maximum context — for 24GB+ VRAM (RTX 3090/4090)",
    },
}
