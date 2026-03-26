"""
Core/model_marketplace.py — Model Marketplace for ZEN_RAG

Discover, browse, recommend, and download GGUF models from HuggingFace.
Hardware-aware recommendations filter models by your machine's capabilities.

Features:
    - 8 curated "Staff Picks" with specialty tags & strength badges
    - HuggingFace live search (cached 24h) — zero heavy deps (stdlib only)
    - Trending models feed (cached 1h)
    - Zero-dependency hardware detection (CPU, RAM, GPU, AVX2, NEON)
    - Auto-tier classification: high/medium/low/minimal
    - Smart recommendations: filters curated list by hardware tier
    - Download from HuggingFace with progress callback
    - Parse model filenames → params, quantization, RAM estimate, specialty

Ported from: C:\\Users\\Yo930\\Desktop\\_Python\\Local_LLM
    - Core/analysis/model_discovery.py  (search, trending, curated catalog)
    - Core/services/hardware_detection.py (CPU, RAM, GPU profiling)
    - Core/models.py  (HardwareProfile, ModelCapabilities, tiers)

Author : ZEN_RAG v4.8 — Model Marketplace
License: MIT
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import subprocess
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("ZEN_RAG.ModelMarketplace")


# ═══════════════════════════════════════════════════════════════════════════
#  DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class HardwareProfile:
    """System hardware profile for LLM capacity planning.

    Detected automatically by ``detect_hardware()``.
    The ``tier`` property classifies the machine so we can
    recommend compatible models without manual configuration.
    """

    os_name: str = ""
    os_version: str = ""
    arch: str = ""
    cpu_brand: str = ""
    cpu_cores: int = 1
    ram_gb: float = 0.0
    available_ram_gb: float = 0.0
    gpu_name: str = "none"
    gpu_vram_gb: float = 0.0
    avx2: bool = False
    avx512: bool = False
    neon: bool = False

    @property
    def tier(self) -> str:
        """Capability tier: minimal | low | medium | high.

        - high   : ≥8 GB VRAM  (GPU offload for 7B-13B+)
        - medium : <8 GB VRAM but ≥16 GB RAM + AVX2  (CPU-only up to 13B)
        - low    : 8-15 GB RAM + AVX2  (small quants only)
        - minimal: everything else  (tiny models only)
        """
        if self.gpu_vram_gb >= 8:
            return "high"
        if self.ram_gb >= 16 and self.avx2:
            return "medium"
        if self.ram_gb >= 8 and self.avx2:
            return "low"
        return "minimal"

    @property
    def tier_label(self) -> str:
        labels = {
            "high": "🟢 High — GPU offload, 7B-13B+ models",
            "medium": "🟡 Medium — 7B-13B models on CPU",
            "low": "🟠 Low — small quants (Q2-Q4), ≤7B",
            "minimal": "🔴 Minimal — tiny models only (≤1B)",
        }
        return labels.get(self.tier, self.tier)

    @property
    def tier_emoji(self) -> str:
        return {"high": "🟢", "medium": "🟡", "low": "🟠", "minimal": "🔴"}.get(self.tier, "⚪")

    @property
    def recommended_gpu_layers(self) -> int:
        gpu = self.gpu_name.lower()
        if any(k in gpu for k in ("nvidia", "geforce", "rtx", "gtx", "quadro", "tesla")):
            return -1
        if any(k in gpu for k in ("radeon rx", "radeon pro", "rocm")):
            return -1
        if "metal" in gpu or self.neon:
            return -1
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "os_name": self.os_name,
            "os_version": self.os_version,
            "arch": self.arch,
            "cpu_brand": self.cpu_brand,
            "cpu_cores": self.cpu_cores,
            "ram_gb": round(self.ram_gb, 2),
            "available_ram_gb": round(self.available_ram_gb, 2),
            "gpu_name": self.gpu_name,
            "gpu_vram_gb": round(self.gpu_vram_gb, 2),
            "avx2": self.avx2,
            "avx512": self.avx512,
            "neon": self.neon,
            "tier": self.tier,
            "tier_label": self.tier_label,
            "recommended_gpu_layers": self.recommended_gpu_layers,
        }


# ═══════════════════════════════════════════════════════════════════════════
#  HARDWARE DETECTION  (zero external deps — uses stdlib only)
# ═══════════════════════════════════════════════════════════════════════════


def _detect_cpu_brand() -> str:
    system = platform.system()
    try:
        if system == "Windows":
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            return name.strip()
        elif system == "Linux":
            with open("/proc/cpuinfo", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        elif system == "Darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                text=True,
                timeout=5,
            ).strip()
            if out:
                return out
    except Exception as exc:
        logger.debug("CPU brand detection failed: %s", exc)
    return platform.processor() or "Unknown CPU"


def _detect_ram_gb() -> float:
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            return mem.ullTotalPhys / (1024**3)
        elif system == "Linux":
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        kb = int(re.search(r"\d+", line).group())
                        return kb / (1024**2)
        elif system == "Darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"],
                text=True,
                timeout=5,
            ).strip()
            return int(out) / (1024**3)
    except Exception as exc:
        logger.debug("RAM detection failed: %s", exc)
    return 8.0


def _detect_available_ram_gb() -> float:
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            return mem.ullAvailPhys / (1024**3)
        elif system == "Linux":
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemAvailable"):
                        kb = int(re.search(r"\d+", line).group())
                        return kb / (1024**2)
        elif system == "Darwin":
            total = _detect_ram_gb()
            return total * 0.5
    except Exception as exc:
        logger.debug("Available RAM detection failed: %s", exc)
    return _detect_ram_gb() * 0.5


def _detect_gpu() -> Tuple[str, float]:
    """Detect GPU name and VRAM.  Checks: NVIDIA → AMD → Apple Metal → WMI."""
    # 1. NVIDIA
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=10,
            stderr=subprocess.DEVNULL,
        ).strip()
        if out:
            parts = out.split(",")
            name = parts[0].strip()
            vram_mb = float(parts[1].strip()) if len(parts) > 1 else 0
            return (f"NVIDIA {name}", vram_mb / 1024)
    except Exception as exc:
        logger.debug("%s", exc)

    # 2. AMD ROCm
    try:
        out = subprocess.check_output(
            ["rocm-smi", "--showmeminfo", "vram"],
            text=True,
            timeout=10,
            stderr=subprocess.DEVNULL,
        )
        if "Total" in out:
            m = re.search(r"Total Memory.*?(\d+)", out)
            vram = int(m.group(1)) / (1024**2) if m else 0
            return ("AMD GPU (ROCm)", vram)
    except Exception as exc:
        logger.debug("%s", exc)

    # 3. Apple Metal
    if platform.system() == "Darwin" and "arm" in platform.machine().lower():
        ram = _detect_ram_gb()
        return (f"Apple {platform.machine()} (Metal)", ram * 0.75)

    # 4. Windows WMI fallback
    if platform.system() == "Windows":
        try:
            out = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-CimInstance Win32_VideoController).Name",
                ],
                text=True,
                timeout=10,
                stderr=subprocess.DEVNULL,
                encoding="utf-8",
                errors="replace",
            ).strip()
            if out:
                names = [n.strip() for n in out.splitlines() if n.strip()]
                discrete = [
                    n for n in names if not any(x in n.lower() for x in ("microsoft basic", "virtual", "remote"))
                ]
                gpu_name = discrete[0] if discrete else names[0]
                return (gpu_name, 0.0)
        except Exception as exc:
            logger.debug("%s", exc)

    return ("none", 0.0)


def _detect_avx() -> Tuple[bool, bool]:
    system = platform.system()
    avx2, avx512 = False, False
    try:
        if system == "Windows":
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            ident, _ = winreg.QueryValueEx(key, "Identifier")
            winreg.CloseKey(key)
            m = re.search(r"Model\s+(\d+)", ident)
            if m:
                model = int(m.group(1))
                if model >= 60:
                    avx2 = True
                if model >= 85:
                    avx512 = True
        elif system == "Linux":
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                text = f.read()
            avx2 = "avx2" in text
            avx512 = "avx512" in text
        elif system == "Darwin":
            out = subprocess.check_output(
                ["sysctl", "-a"],
                text=True,
                timeout=5,
                stderr=subprocess.DEVNULL,
            )
            avx2 = "hw.optional.avx2_0: 1" in out
            avx512 = "hw.optional.avx512" in out and ": 1" in out
    except Exception as exc:
        logger.debug("AVX detection failed: %s", exc)
    return avx2, avx512


def detect_hardware() -> HardwareProfile:
    """Auto-detect the full hardware profile of this machine.  Never raises."""
    os_name = platform.system()
    os_version = platform.release()
    arch = platform.machine()
    cpu_brand = _detect_cpu_brand()
    cpu_cores = os.cpu_count() or 1
    ram_gb = _detect_ram_gb()
    available_ram_gb = _detect_available_ram_gb()
    gpu_name, gpu_vram = _detect_gpu()
    avx2, avx512 = _detect_avx()
    neon = "aarch64" in arch.lower() or "arm64" in arch.lower()

    hw = HardwareProfile(
        os_name=os_name,
        os_version=os_version,
        arch=arch,
        cpu_brand=cpu_brand,
        cpu_cores=cpu_cores,
        ram_gb=ram_gb,
        available_ram_gb=available_ram_gb,
        gpu_name=gpu_name,
        gpu_vram_gb=gpu_vram,
        avx2=avx2,
        avx512=avx512,
        neon=neon,
    )
    logger.info(
        "Hardware: %s, %d cores, %.1f GB RAM, GPU=%s (%.1f GB), AVX2=%s, tier=%s",
        cpu_brand,
        cpu_cores,
        ram_gb,
        gpu_name,
        gpu_vram,
        avx2,
        hw.tier,
    )
    return hw


# ═══════════════════════════════════════════════════════════════════════════
#  FILENAME PARSER  — extract params / quant / RAM / specialty
# ═══════════════════════════════════════════════════════════════════════════


def parse_model_info(model_name: str, file_size_gb: float = 0) -> Dict[str, Any]:
    """Parse a GGUF filename and return human-readable metadata."""
    info: Dict[str, Any] = {
        "parameters": "Unknown",
        "quantization": "",
        "ram_estimate": "Unknown",
        "speed_rating": "⚡",
        "quality_rating": "⭐⭐⭐",
        "best_for": "General chat",
    }

    # Parameter count
    pm = re.search(r"(\d+\.?\d*)\s*[BbMm](?![a-z])", model_name)
    if pm:
        num = float(pm.group(1))
        unit = pm.group(0)[-1].upper()
        billions = num / 1000 if unit == "M" else num
        info["parameters"] = f"{num}{unit}"
        est_ram = billions * 0.7 + 0.5
        if est_ram < 4:
            info["ram_estimate"] = f"~{max(1, int(est_ram))} GB"
            info["speed_rating"] = "⚡⚡⚡ Fast"
        elif est_ram < 8:
            info["ram_estimate"] = f"~{int(est_ram)} GB"
            info["speed_rating"] = "⚡⚡ Balanced"
        elif est_ram < 16:
            info["ram_estimate"] = f"~{int(est_ram)} GB"
            info["speed_rating"] = "⚡ Moderate"
        else:
            info["ram_estimate"] = ">16 GB"
            info["speed_rating"] = "🐢 Heavy"

    # Quantization
    qm = re.search(r"[Qq](\d+)(?:_K_[MSL]|_\d)?", model_name)
    if qm:
        q = int(qm.group(1))
        info["quantization"] = qm.group(0).upper()
        if q <= 3:
            info["quality_rating"] = "⭐⭐"
        elif q == 4:
            info["quality_rating"] = "⭐⭐⭐⭐ Recommended"
        elif q >= 5:
            info["quality_rating"] = "⭐⭐⭐⭐⭐"

    # Specialty
    nl = model_name.lower()
    if "coder" in nl or "code" in nl:
        info["best_for"] = "💻 Coding & programming"
    elif "instruct" in nl:
        info["best_for"] = "💬 Instruction following"
    elif "chat" in nl:
        info["best_for"] = "💬 Conversation"
    elif "math" in nl:
        info["best_for"] = "🔢 Mathematics"

    info["explanation"] = f"{info['parameters']} params • {info['quantization'] or '?'} • {info['ram_estimate']}"
    return info


# ═══════════════════════════════════════════════════════════════════════════
#  CURATED CATALOG — Staff Picks
# ═══════════════════════════════════════════════════════════════════════════

CURATED_MODELS: List[Dict[str, Any]] = [
    {
        "name": "Qwen 2.5 Coder 7B",
        "repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        "file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        "size_gb": 4.4,
        "description": "🏆 Top coding model — beats GPT-4 on HumanEval",
        "downloads": "2.5M+",
        "likes": "12K+",
        "released": "Dec 2024",
        "context_window": "32K",
        "strengths": ["Code generation", "Debugging", "Multi-language"],
        "license": "Apache 2.0",
        "category": "coding",
        "min_ram_gb": 6,
    },
    {
        "name": "Llama 3.2 3B",
        "repo": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "size_gb": 2.0,
        "description": "⚡ Lightning fast, 128K context",
        "downloads": "1.8M+",
        "likes": "8K+",
        "released": "Sep 2024",
        "context_window": "128K",
        "strengths": ["Speed", "Long docs", "Reasoning"],
        "license": "Llama 3.2",
        "category": "fast",
        "min_ram_gb": 4,
    },
    {
        "name": "Mistral 7B v0.3",
        "repo": "MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF",
        "file": "Mistral-7B-Instruct-v0.3.Q4_K_M.gguf",
        "size_gb": 4.1,
        "description": "🎯 Jack of all trades — solid at everything",
        "downloads": "3.2M+",
        "likes": "15K+",
        "released": "May 2024",
        "context_window": "32K",
        "strengths": ["Balanced", "Reasoning", "Math", "Writing"],
        "license": "Apache 2.0",
        "category": "balanced",
        "min_ram_gb": 6,
    },
    {
        "name": "Phi-3 Mini 4K",
        "repo": "microsoft/Phi-3-mini-4k-instruct-gguf",
        "file": "Phi-3-mini-4k-instruct-q4.gguf",
        "size_gb": 2.4,
        "description": "🚀 Microsoft's tiny powerhouse — great for STEM",
        "downloads": "850K+",
        "likes": "6K+",
        "released": "Apr 2024",
        "context_window": "4K",
        "strengths": ["Efficiency", "Math", "STEM", "Low RAM"],
        "license": "MIT",
        "category": "fast",
        "min_ram_gb": 4,
    },
    {
        "name": "DeepSeek Coder 6.7B",
        "repo": "bartowski/deepseek-coder-6.7b-instruct-GGUF",
        "file": "deepseek-coder-6.7b-instruct-Q4_K_M.gguf",
        "size_gb": 4.0,
        "description": "💻 Code specialist — algorithms & debugging",
        "downloads": "620K+",
        "likes": "4.5K+",
        "released": "Nov 2023",
        "context_window": "16K",
        "strengths": ["Code completion", "Bug fixing", "Algorithms"],
        "license": "DeepSeek (Commercial OK)",
        "category": "coding",
        "min_ram_gb": 6,
    },
    {
        "name": "Gemma 2 9B",
        "repo": "bartowski/gemma-2-9b-it-GGUF",
        "file": "gemma-2-9b-it-Q4_K_M.gguf",
        "size_gb": 5.5,
        "description": "🧠 Google's powerful model — great reasoning",
        "downloads": "410K+",
        "likes": "3.8K+",
        "released": "Jun 2024",
        "context_window": "8K",
        "strengths": ["Safety", "Reasoning", "Instruction following"],
        "license": "Gemma",
        "category": "balanced",
        "min_ram_gb": 8,
    },
    {
        "name": "Llama 3.1 8B",
        "repo": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "file": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "size_gb": 4.9,
        "description": "🦙 Meta's versatile model — 128K context",
        "downloads": "2.1M+",
        "likes": "11K+",
        "released": "Jul 2024",
        "context_window": "128K",
        "strengths": ["Long context", "Reasoning", "Multilingual"],
        "license": "Llama 3.1",
        "category": "balanced",
        "min_ram_gb": 8,
    },
    {
        "name": "Qwen 2.5 14B",
        "repo": "bartowski/Qwen2.5-14B-Instruct-GGUF",
        "file": "Qwen2.5-14B-Instruct-Q4_K_M.gguf",
        "size_gb": 8.5,
        "description": "⚡ Flagship Qwen — exceptional quality across all tasks",
        "downloads": "520K+",
        "likes": "5.2K+",
        "released": "Sep 2024",
        "context_window": "128K",
        "strengths": ["Top quality", "Multilingual", "Math"],
        "license": "Apache 2.0",
        "category": "large",
        "min_ram_gb": 12,
    },
]

# Enrich each curated model with parsed info
for _m in CURATED_MODELS:
    _m.update(parse_model_info(_m["file"], _m["size_gb"]))


# ═══════════════════════════════════════════════════════════════════════════
#  HUGGINGFACE API  — search & trending  (stdlib only, cached)
# ═══════════════════════════════════════════════════════════════════════════

_CACHE_DIR = Path.home() / ".cache" / "rag_rat" / "hf_marketplace"
_CACHE_TTL = 86400  # 24h for searches
_TRENDING_TTL = 3600  # 1h for trending
_HF_API = "https://huggingface.co/api/models"
_UA = {"User-Agent": "ZEN_RAG/3.8"}


def _ensure_cache_dir():
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        logger.debug("%s", exc)


def _cache_path(key: str) -> Path:
    safe = re.sub(r"[^\w\-.]", "_", key)
    return _CACHE_DIR / f"{safe}.json"


def _read_cache(key: str, ttl: int = _CACHE_TTL) -> Optional[Any]:
    p = _cache_path(key)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if time.time() - data.get("_ts", 0) < ttl:
            return data.get("payload")
    except Exception as exc:
        logger.debug("%s", exc)
    return None


def _write_cache(key: str, payload: Any):
    _ensure_cache_dir()
    try:
        _cache_path(key).write_text(
            json.dumps({"_ts": time.time(), "payload": payload}),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.debug("%s", exc)


def _hf_get(params: Dict[str, Any], timeout: int = 12) -> List[Dict]:
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{_HF_API}?{qs}"
    req = urllib.request.Request(url, headers=_UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning("HuggingFace API request failed: %s", e)
        return []


def _local_only_skip_hf() -> bool:
    """True when RAG_LOCAL_ONLY=1: skip HuggingFace API calls (return cache only or [])."""
    try:
        from config_system import config

        return getattr(config.rag, "local_only", False)
    except Exception:
        return os.environ.get("RAG_LOCAL_ONLY", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )


def search_huggingface(
    query: str,
    limit: int = 12,
    *,
    sort: str = "downloads",
) -> List[Dict[str, Any]]:
    """Search HuggingFace for GGUF models. Cached 24h. When RAG_LOCAL_ONLY=1, no API call (cache or [])."""
    if not query or not query.strip():
        return []

    cache_key = f"hf_search_{query}_{limit}_{sort}"
    cached = _read_cache(cache_key)
    if cached is not None:
        return cached
    if _local_only_skip_hf():
        return []

    raw = _hf_get(
        {
            "search": query,
            "filter": "gguf",
            "sort": sort,
            "direction": "-1",
            "limit": str(limit),
        }
    )

    results = []
    for m in raw:
        mid = m.get("id", "")
        entry = {
            "id": mid,
            "repo": mid,
            "name": mid.split("/")[-1] if "/" in mid else mid,
            "author": mid.split("/")[0] if "/" in mid else "",
            "downloads": m.get("downloads", 0),
            "likes": m.get("likes", 0),
            "last_modified": (m.get("lastModified") or "")[:10],
            "pipeline_tag": m.get("pipeline_tag", ""),
            "tags": m.get("tags", [])[:12],
        }
        entry.update(parse_model_info(mid))
        results.append(entry)

    _write_cache(cache_key, results)
    return results


def get_trending_models(limit: int = 6) -> List[Dict[str, Any]]:
    """Fetch currently trending GGUF models.  Cached 1h."""
    cache_key = f"hf_trending_{limit}"
    cached = _read_cache(cache_key, ttl=_TRENDING_TTL)
    if cached is not None:
        return cached

    raw = _hf_get(
        {
            "search": "gguf",
            "sort": "trending",
            "direction": "-1",
            "limit": str(limit * 3),
            "filter": "gguf",
        }
    )

    results = []
    for m in raw:
        dl = m.get("downloads", 0)
        if dl < 500:
            continue
        mid = m.get("id", "")
        entry = {
            "id": mid,
            "repo": mid,
            "name": mid.split("/")[-1] if "/" in mid else mid,
            "author": mid.split("/")[0] if "/" in mid else "",
            "downloads": dl,
            "likes": m.get("likes", 0),
            "last_modified": (m.get("lastModified") or "")[:10],
            "pipeline_tag": m.get("pipeline_tag", ""),
            "tags": m.get("tags", [])[:12],
            "trending": True,
        }
        entry.update(parse_model_info(mid))
        results.append(entry)
        if len(results) >= limit:
            break

    _write_cache(cache_key, results)
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  POPULARITY / FRESHNESS ENRICHMENT
# ═══════════════════════════════════════════════════════════════════════════


def enrich_with_popularity(model: Dict[str, Any]) -> Dict[str, Any]:
    """Add popularity_tier and freshness to a model dict.  Mutates in place."""
    dl = model.get("downloads", 0)

    if isinstance(dl, str):
        model.setdefault("popularity_tier", "popular")
    elif dl > 500_000:
        model["popularity_tier"] = "trending"
    elif dl > 100_000:
        model["popularity_tier"] = "popular"
    elif dl > 10_000:
        model["popularity_tier"] = "established"
    else:
        model["popularity_tier"] = "niche"

    lm = model.get("last_modified", "")
    if lm:
        try:
            dt = datetime.fromisoformat(lm.replace("Z", "+00:00"))
            age = (datetime.now(dt.tzinfo) - dt).days
        except Exception:
            try:
                dt = datetime.strptime(lm[:10], "%Y-%m-%d")
                age = (datetime.now() - dt).days
            except Exception:
                age = 999
        if age < 30:
            model["freshness"] = "🔥 Hot"
        elif age < 90:
            model["freshness"] = "🆕 New"
        elif age < 365:
            model["freshness"] = "✅ Current"
        else:
            model["freshness"] = "📦 Stable"
    return model


# ═══════════════════════════════════════════════════════════════════════════
#  FORMAT HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def fmt_downloads(n) -> str:
    if isinstance(n, str):
        return n
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def fmt_likes(n) -> str:
    if isinstance(n, str):
        return n
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_size(gb: float) -> str:
    if gb < 1:
        return f"{gb * 1024:.0f} MB"
    return f"{gb:.1f} GB"


# ═══════════════════════════════════════════════════════════════════════════
#  MODEL MARKETPLACE  — Singleton orchestrator
# ═══════════════════════════════════════════════════════════════════════════


class ModelMarketplace:
    """Top-level orchestrator for the Model Marketplace.

    Combines hardware detection, curated catalog, HF search,
    and local model scanning into one unified interface.
    """

    _instance: Optional["ModelMarketplace"] = None
    _lock = RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._hardware: Optional[HardwareProfile] = None
        self._hardware_ts: float = 0.0
        self._local_models: List[Dict[str, Any]] = []
        self._local_scan_ts: float = 0.0
        self._download_tasks: Dict[str, Dict[str, Any]] = {}

    # ── Hardware ──

    def get_hardware(self, force_refresh: bool = False) -> HardwareProfile:
        """Get cached hardware profile (refreshes every 5 min)."""
        if self._hardware is None or force_refresh or (time.time() - self._hardware_ts > 300):
            self._hardware = detect_hardware()
            self._hardware_ts = time.time()
        return self._hardware

    # ── Curated / Recommended ──

    def get_curated_models(self) -> List[Dict[str, Any]]:
        """Return all 8 curated Staff Picks."""
        return list(CURATED_MODELS)

    def get_recommended_for_hardware(self) -> List[Dict[str, Any]]:
        """Filter curated models by hardware tier."""
        hw = self.get_hardware()
        tier = hw.tier

        if tier == "high":
            return list(CURATED_MODELS)
        elif tier == "medium":
            return [m for m in CURATED_MODELS if m.get("min_ram_gb", 0) <= hw.ram_gb]
        elif tier == "low":
            return [m for m in CURATED_MODELS if m.get("size_gb", 0) <= 4.5]
        else:  # minimal
            return [m for m in CURATED_MODELS if m.get("size_gb", 0) <= 2.5]

    def get_models_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Filter curated models by category: coding, fast, balanced, large."""
        return [m for m in CURATED_MODELS if m.get("category") == category]

    # ── Local Model Discovery ──

    def scan_local_models(self, model_dirs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Scan local directories for .gguf model files."""
        if model_dirs is None:
            model_dirs = self._default_model_dirs()

        models = []
        seen = set()
        for dir_str in model_dirs:
            d = Path(dir_str)
            if not d.exists():
                continue
            for f in d.rglob("*.gguf"):
                if f.name in seen:
                    continue
                seen.add(f.name)
                size_bytes = f.stat().st_size
                size_gb = size_bytes / (1024**3)
                info = parse_model_info(f.name, size_gb)
                models.append(
                    {
                        "name": f.stem,
                        "filename": f.name,
                        "path": str(f),
                        "size_gb": round(size_gb, 2),
                        "size_bytes": size_bytes,
                        **info,
                    }
                )

        self._local_models = models
        self._local_scan_ts = time.time()
        return models

    def get_local_models(self) -> List[Dict[str, Any]]:
        """Get last scan results (or scan if never done)."""
        if not self._local_models:
            self.scan_local_models()
        return self._local_models

    def _default_model_dirs(self) -> List[str]:
        """Platform-aware default directories to scan for models."""
        dirs = []
        # Common locations
        for candidate in [
            Path("C:/AI/Models"),
            Path.home() / "AI" / "Models",
            Path.home() / ".cache" / "lm-studio" / "models",
            Path.home() / ".ollama" / "models",
            Path.home() / "models",
        ]:
            if candidate.exists():
                dirs.append(str(candidate))
        return dirs

    # ── HuggingFace Search / Trending ──

    def search(self, query: str, limit: int = 12, sort: str = "downloads") -> List[Dict[str, Any]]:
        """Search HuggingFace for GGUF models."""
        return search_huggingface(query, limit, sort=sort)

    def get_trending(self, limit: int = 6) -> List[Dict[str, Any]]:
        """Get trending GGUF models from HuggingFace."""
        return get_trending_models(limit)

    # ── Download ──

    def download_model(
        self,
        repo_id: str,
        filename: str,
        target_dir: Optional[str] = None,
        on_progress: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Any]:
        """Download a model from HuggingFace.

        Uses direct urllib download (no huggingface_hub required).
        Progress callback receives percentage (0-100).

        Returns dict with: status, local_path, error.
        """
        if target_dir is None:
            target_dir = str(Path.home() / "AI" / "Models")

        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        dest = target / filename

        if dest.exists():
            return {
                "status": "exists",
                "local_path": str(dest),
                "error": None,
            }

        url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
        task_id = f"{repo_id}/{filename}"
        self._download_tasks[task_id] = {
            "status": "downloading",
            "progress": 0.0,
            "started": time.time(),
        }

        try:

            def _report(block_num, block_size, total_size):
                if total_size > 0:
                    pct = min(100.0, block_num * block_size * 100 / total_size)
                    self._download_tasks[task_id]["progress"] = pct
                    if on_progress:
                        on_progress(pct)

            urllib.request.urlretrieve(url, str(dest), reporthook=_report)

            self._download_tasks[task_id].update(
                {
                    "status": "completed",
                    "progress": 100.0,
                }
            )

            # Re-scan local models to include the new download
            self.scan_local_models()

            return {
                "status": "completed",
                "local_path": str(dest),
                "error": None,
            }
        except Exception as e:
            self._download_tasks[task_id].update(
                {
                    "status": "failed",
                    "error": str(e),
                }
            )
            # Clean up partial download
            if dest.exists():
                try:
                    dest.unlink()
                except Exception as exc:
                    logger.debug("%s", exc)
            return {
                "status": "failed",
                "local_path": None,
                "error": str(e),
            }

    def get_download_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all download tasks with their status."""
        return dict(self._download_tasks)

    # ── Summary ──

    def get_marketplace_summary(self) -> Dict[str, Any]:
        """Complete marketplace status for the UI."""
        hw = self.get_hardware()
        local = self.get_local_models()
        recommended = self.get_recommended_for_hardware()

        return {
            "hardware": hw.to_dict(),
            "local_models_count": len(local),
            "local_models": local,
            "curated_count": len(CURATED_MODELS),
            "recommended_count": len(recommended),
            "recommended_models": recommended,
            "active_downloads": sum(1 for t in self._download_tasks.values() if t.get("status") == "downloading"),
        }


# ═══════════════════════════════════════════════════════════════════════════
#  MODULE-LEVEL SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_marketplace: Optional[ModelMarketplace] = None
_marketplace_lock = RLock()


def get_marketplace() -> ModelMarketplace:
    """Get the singleton ModelMarketplace instance."""
    global _marketplace
    if _marketplace is None:
        with _marketplace_lock:
            if _marketplace is None:
                _marketplace = ModelMarketplace()
    return _marketplace
