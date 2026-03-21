"""
Core/inference_guard.py — Inference crash diagnostics & performance profiling.

Wraps every LLM inference call with:
  - Memory snapshots (RSS, VMS, GPU, system) before + after
  - Wall-clock + per-phase timing with named checkpoints
  - Crash classification (MEMORY, FIFO, THREAD, TIMEOUT, LLAMA_CPP, etc.)
  - Request profiling ring buffer (last N successful calls)
  - Crash history ring buffer (last N failures)
  - Aggregate stats (timing, memory deltas)

Architecture:
  GuardMetrics     — all counters/aggregates in one class
  MemorySnapshot   — one-shot RSS/VMS/GPU/system capture
  CrashReport      — structured diagnostic with auto-classify
  InferenceGuard   — async context manager wrapping any inference call
  Decorators       — inference_guard(), inference_guard_generator()

This module is the ONLY place that tracks timing, memory, and crash data.
Ported from ZEN_RAG.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import sys
import threading
import time
import traceback
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional

import psutil

logger = logging.getLogger("inference_guard")


# =========================================================================
# GUARD METRICS
# =========================================================================

class GuardMetrics:
    """Thread-safe aggregate metrics for all guarded inference calls."""

    def __init__(self, max_crashes: int = 50, max_profiles: int = 100):
        self._lock = threading.Lock()
        self.total_guarded_calls: int = 0
        self.total_crashes: int = 0
        self.total_inference_ms: float = 0.0
        self.fastest_ms: float = float("inf")
        self.slowest_ms: float = 0.0
        self.total_rss_delta_mb: float = 0.0
        self.max_rss_delta_mb: float = 0.0
        self._crash_history: Deque[Dict[str, Any]] = deque(maxlen=max_crashes)
        self._request_profiles: Deque[Dict[str, Any]] = deque(maxlen=max_profiles)

    def record_call(self):
        with self._lock:
            self.total_guarded_calls += 1

    def record_success(self, elapsed_ms: float, rss_delta_mb: float, profile: Dict[str, Any]):
        with self._lock:
            self.total_inference_ms += elapsed_ms
            if elapsed_ms < self.fastest_ms:
                self.fastest_ms = elapsed_ms
            if elapsed_ms > self.slowest_ms:
                self.slowest_ms = elapsed_ms
            self.total_rss_delta_mb += abs(rss_delta_mb)
            if abs(rss_delta_mb) > self.max_rss_delta_mb:
                self.max_rss_delta_mb = abs(rss_delta_mb)
            self._request_profiles.append(profile)

    def record_crash(self, report_dict: Dict[str, Any]):
        with self._lock:
            self.total_crashes += 1
            self._crash_history.append(report_dict)

    def get_crash_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(self._crash_history))

    def get_request_profiles(self, last_n: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(reversed(self._request_profiles))
            return items[:last_n]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            n = self.total_guarded_calls
            avg_ms = self.total_inference_ms / n if n > 0 else 0
            return {
                "total_guarded_calls": n,
                "total_crashes": self.total_crashes,
                "crash_rate": (f"{self.total_crashes / n * 100:.2f}%" if n > 0 else "0%"),
                "crashes_in_history": len(self._crash_history),
                "profiles_in_history": len(self._request_profiles),
                "timing": {
                    "avg_ms": round(avg_ms, 1),
                    "fastest_ms": round(self.fastest_ms, 1) if self.fastest_ms != float("inf") else None,
                    "slowest_ms": round(self.slowest_ms, 1),
                    "total_ms": round(self.total_inference_ms, 1),
                },
                "memory": {
                    "total_rss_delta_mb": round(self.total_rss_delta_mb, 1),
                    "max_rss_delta_mb": round(self.max_rss_delta_mb, 1),
                },
            }


# Module-level singleton
_metrics = GuardMetrics()


# =========================================================================
# PUBLIC API
# =========================================================================

def get_crash_history() -> List[Dict[str, Any]]:
    """Return the last N crash reports (newest first)."""
    return _metrics.get_crash_history()


def get_request_profiles(last_n: int = 20) -> List[Dict[str, Any]]:
    """Return the last N successful request profiles (newest first)."""
    return _metrics.get_request_profiles(last_n)


def get_guard_stats() -> Dict[str, Any]:
    """Global inference guard statistics with timing + memory aggregates."""
    return _metrics.get_stats()


# =========================================================================
# MEMORY SNAPSHOT
# =========================================================================

class MemorySnapshot:
    """Capture process + system memory at a point in time."""

    __slots__ = (
        "rss_mb", "vms_mb", "percent",
        "sys_total_mb", "sys_available_mb", "sys_percent",
        "gpu_mb", "timestamp",
    )

    def __init__(self):
        self.timestamp = time.time()
        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        self.rss_mb = round(mem.rss / (1024**2), 1)
        self.vms_mb = round(mem.vms / (1024**2), 1)
        self.percent = round(proc.memory_percent(), 2)

        sysmem = psutil.virtual_memory()
        self.sys_total_mb = round(sysmem.total / (1024**2), 1)
        self.sys_available_mb = round(sysmem.available / (1024**2), 1)
        self.sys_percent = sysmem.percent

        self.gpu_mb = _get_gpu_memory_mb()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rss_mb": self.rss_mb,
            "vms_mb": self.vms_mb,
            "process_percent": self.percent,
            "system_total_mb": self.sys_total_mb,
            "system_available_mb": self.sys_available_mb,
            "system_percent": self.sys_percent,
            "gpu_allocated_mb": self.gpu_mb,
        }

    def delta(self, other: "MemorySnapshot") -> Dict[str, float]:
        return {
            "rss_delta_mb": round(self.rss_mb - other.rss_mb, 1),
            "vms_delta_mb": round(self.vms_mb - other.vms_mb, 1),
            "sys_available_delta_mb": round(self.sys_available_mb - other.sys_available_mb, 1),
            "gpu_delta_mb": (
                round(self.gpu_mb - other.gpu_mb, 1)
                if self.gpu_mb is not None and other.gpu_mb is not None
                else None
            ),
        }


def _get_gpu_memory_mb() -> Optional[float]:
    """Try to get GPU memory usage (PyTorch CUDA -> nvidia-smi fallback)."""
    try:
        import torch
        if torch.cuda.is_available():
            return round(torch.cuda.memory_allocated() / (1024**2), 1)
    except Exception:
        pass

    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"],
            capture_output=True, text=True, timeout=3, shell=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip().split("\n")[0])
    except Exception:
        pass

    return None


def get_memory_snapshot() -> Dict[str, Any]:
    """Quick process+system memory dict for use by endpoints."""
    proc = psutil.Process(os.getpid())
    mem = proc.memory_info()
    sysmem = psutil.virtual_memory()
    return {
        "process_rss_mb": round(mem.rss / (1024**2), 1),
        "process_vms_mb": round(mem.vms / (1024**2), 1),
        "process_percent": round(proc.memory_percent(), 2),
        "system_total_mb": round(sysmem.total / (1024**2), 1),
        "system_available_mb": round(sysmem.available / (1024**2), 1),
        "system_percent": sysmem.percent,
    }


# =========================================================================
# ADAPTER STATE SNAPSHOTS
# =========================================================================

def _get_fifo_state(adapter) -> Optional[Dict[str, Any]]:
    try:
        inner = getattr(adapter, "adapter", adapter)
        if hasattr(inner, "get_stats"):
            return inner.get_stats()
        result = {}
        for attr_name in ("request_buffer", "response_buffer"):
            buf = getattr(inner, attr_name, None)
            if buf and hasattr(buf, "stats"):
                result[attr_name] = buf.stats()
        return result if result else None
    except Exception as e:
        return {"error": str(e)}


def _get_llm_state(adapter) -> Optional[Dict[str, Any]]:
    try:
        inner = getattr(adapter, "adapter", adapter)
        llm = getattr(type(inner), "_shared_llm", getattr(inner, "_shared_llm", None))
        if llm is None:
            return {"model_loaded": False}

        info: Dict[str, Any] = {"model_loaded": True}
        if hasattr(llm, "n_ctx"):
            info["n_ctx"] = llm.n_ctx()
        if hasattr(llm, "n_tokens"):
            info["n_tokens_used"] = llm.n_tokens()

        model_path = getattr(type(inner), "_shared_model_path", getattr(inner, "model_path", None))
        if model_path:
            p = Path(model_path)
            info["model_file"] = p.name
            if p.exists():
                info["model_size_gb"] = round(p.stat().st_size / (1024**3), 2)
        return info
    except Exception as e:
        return {"error": str(e)}


def _get_thread_state() -> Dict[str, Any]:
    threads = threading.enumerate()
    return {
        "active_count": len(threads),
        "names": [t.name for t in threads[:20]],
        "daemon_count": sum(1 for t in threads if t.daemon),
    }


# =========================================================================
# CRASH REPORT
# =========================================================================

@dataclass
class CrashReport:
    """Full diagnostic report when inference fails."""
    operation: str
    error_type: str
    error_message: str
    traceback: str
    timestamp: float = field(default_factory=time.time)
    phase: str = "unknown"
    elapsed_seconds: float = 0.0
    checkpoints: Dict[str, float] = field(default_factory=dict)
    memory_before: Optional[Dict] = None
    memory_after: Optional[Dict] = None
    memory_delta: Optional[Dict] = None
    fifo_state: Optional[Dict] = None
    llm_state: Optional[Dict] = None
    thread_state: Optional[Dict] = None
    request_info: Optional[Dict] = None
    likely_cause: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def classify(self):
        """Auto-classify the likely cause based on error text + memory evidence."""
        err = self.error_message.lower()
        etype = self.error_type.lower()

        if any(w in err for w in ("memory", "oom", "alloc", "mmap", "out of memory", "cuda_error")):
            self.likely_cause = "MEMORY: Out of memory (RAM or GPU)"
            return
        if self.memory_after:
            sys_pct = self.memory_after.get("system_percent", 0)
            if sys_pct > 95:
                self.likely_cause = f"MEMORY: System memory at {sys_pct}% — OS may have killed the process"
                return
        if self.memory_delta:
            rss_delta = self.memory_delta.get("rss_delta_mb", 0)
            if rss_delta and rss_delta > 2000:
                self.likely_cause = (
                    f"MEMORY: RSS grew {rss_delta:.0f} MB during inference — "
                    "likely context overflow or repeated allocation"
                )
                return
        if any(w in err for w in ("fifo", "buffer", "queue", "timeout", "backpressure")):
            self.likely_cause = "FIFO: Buffer overflow or timeout"
            return
        if any(w in err for w in ("deadlock", "lock", "semaphore", "thread")):
            self.likely_cause = "THREAD: Deadlock or lock contention"
            return
        if "timeout" in err or "timed out" in err:
            self.likely_cause = (
                f"TIMEOUT: Inference took {self.elapsed_seconds:.1f}s"
                if self.elapsed_seconds > 30
                else "TIMEOUT: Operation timed out"
            )
            return
        if any(w in err for w in ("llama", "gguf", "ggml", "segfault", "access violation")):
            self.likely_cause = "LLAMA_CPP: Internal engine error"
            return
        if any(w in err for w in ("connection", "broken pipe", "reset", "refused")):
            self.likely_cause = "CRASH: Server process died during inference"
            return
        if any(w in err for w in ("context", "n_ctx", "too many tokens", "exceeds")):
            self.likely_cause = "CONTEXT: Prompt exceeds model context window"
            return
        if self.elapsed_seconds > 60:
            self.likely_cause = (
                f"SLOW: Inference took {self.elapsed_seconds:.1f}s — may need smaller max_tokens or model"
            )
        else:
            self.likely_cause = f"UNKNOWN: {etype}"


def _sanitize_request_info(info: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive data, truncate prompts for storage."""
    sanitized = {}
    for k, v in info.items():
        if k in ("prompt", "content", "messages"):
            if isinstance(v, str):
                sanitized[k] = v[:200] + "..." if len(v) > 200 else v
                sanitized[f"{k}_length"] = len(v)
            elif isinstance(v, list):
                sanitized[f"{k}_count"] = len(v)
                sanitized[k] = [
                    {"role": m.get("role", "?"), "content_len": len(m.get("content", ""))}
                    for m in v[:10]
                ]
            else:
                sanitized[k] = str(v)[:100]
        else:
            sanitized[k] = v
    return sanitized


# =========================================================================
# INFERENCE GUARD — async context manager
# =========================================================================

class InferenceGuard:
    """Wrap inference with full crash diagnostics and performance profiling.

    Usage:
        async with InferenceGuard("streaming", adapter=adapter) as guard:
            guard.mark("tokens_started")
            async for token in stream_tokens(...):
                yield token
            guard.mark("tokens_done")
    """

    def __init__(self, operation: str, *, adapter=None, request_info=None):
        self.operation = operation
        self.adapter = adapter
        self.request_info = request_info or {}
        self.start_time: Optional[float] = None
        self.mem_before: Optional[MemorySnapshot] = None
        self.checkpoints: Dict[str, float] = {}
        self._phase = "pre_inference"

    def set_request_info(self, info: Dict[str, Any]):
        self.request_info = info

    def mark(self, name: str):
        if self.start_time:
            self.checkpoints[name] = round(time.time() - self.start_time, 4)

    def phase(self, name: str):
        self._phase = name

    async def __aenter__(self):
        _metrics.record_call()
        self.start_time = time.time()
        self.mem_before = MemorySnapshot()
        self._phase = "inference"
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time if self.start_time else 0
        if exc_type is None:
            self._handle_success(elapsed)
        else:
            self._handle_crash(elapsed, exc_type, exc_val)
        return False

    def _handle_success(self, elapsed: float):
        mem_after = MemorySnapshot()
        delta = mem_after.delta(self.mem_before)
        rss_delta = delta.get("rss_delta_mb", 0)
        elapsed_ms = elapsed * 1000

        profile = {
            "operation": self.operation,
            "status": "ok",
            "elapsed_ms": round(elapsed_ms, 1),
            "checkpoints": self.checkpoints.copy(),
            "memory_before": {"rss_mb": self.mem_before.rss_mb, "sys_percent": self.mem_before.sys_percent},
            "memory_after": {"rss_mb": mem_after.rss_mb, "sys_percent": mem_after.sys_percent, "gpu_mb": mem_after.gpu_mb},
            "memory_delta": delta,
            "request_info": _sanitize_request_info(self.request_info),
            "timestamp": time.time(),
        }
        if self.adapter:
            fifo = _get_fifo_state(self.adapter)
            if fifo:
                profile["fifo_state"] = fifo
            llm = _get_llm_state(self.adapter)
            if llm:
                profile["llm_state"] = llm

        _metrics.record_success(elapsed_ms, rss_delta, profile)

        if abs(rss_delta) > 100:
            logger.warning(
                "[InferenceGuard] %s OK in %.2fs but RSS changed %+.0f MB (now %.0f MB)",
                self.operation, elapsed, rss_delta, mem_after.rss_mb,
            )
        else:
            logger.info(
                "[InferenceGuard] %s OK in %.2fs RSS: %.0f -> %.0f MB (d%+.0f) | sys: %s%%",
                self.operation, elapsed, self.mem_before.rss_mb, mem_after.rss_mb, rss_delta, mem_after.sys_percent,
            )

    def _handle_crash(self, elapsed: float, exc_type, exc_val):
        mem_after = MemorySnapshot()
        report = CrashReport(
            operation=self.operation,
            error_type=exc_type.__name__,
            error_message=str(exc_val),
            traceback=traceback.format_exc(),
            phase=self._phase,
            elapsed_seconds=round(elapsed, 3),
            checkpoints=self.checkpoints.copy(),
            memory_before=self.mem_before.to_dict(),
            memory_after=mem_after.to_dict(),
            memory_delta=mem_after.delta(self.mem_before),
            fifo_state=_get_fifo_state(self.adapter) if self.adapter else None,
            llm_state=_get_llm_state(self.adapter) if self.adapter else None,
            thread_state=_get_thread_state(),
            request_info=_sanitize_request_info(self.request_info),
        )
        report.classify()
        _metrics.record_crash(report.to_dict())

        logger.error(
            "\n%s\nINFERENCE CRASH — %s\n%s\n"
            "  Operation:  %s\n  Phase:      %s\n"
            "  Error:      %s: %s\n  Elapsed:    %.3fs\n"
            "  Memory:     RSS %.0f -> %.0f MB (d%+.0f MB)\n"
            "  System:     %s%% used (%.0f MB free)\n"
            "  GPU:        %s MB\n  Threads:    %s active\n%s",
            "=" * 70, report.likely_cause, "=" * 70,
            report.operation, report.phase,
            report.error_type, report.error_message, report.elapsed_seconds,
            self.mem_before.rss_mb, mem_after.rss_mb, report.memory_delta["rss_delta_mb"],
            mem_after.sys_percent, mem_after.sys_available_mb,
            mem_after.gpu_mb or "N/A", report.thread_state["active_count"],
            "=" * 70,
        )


# =========================================================================
# DECORATORS
# =========================================================================

def inference_guard(operation: str = "inference", *, get_adapter=None):
    """Decorator wrapping an async function with crash diagnostics."""
    def decorator(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            adapter = get_adapter() if get_adapter else None
            async with InferenceGuard(operation, adapter=adapter):
                return await fn(*args, **kwargs)
        return wrapper
    return decorator


def inference_guard_generator(operation: str = "inference", *, get_adapter=None):
    """Decorator for async generators (streaming endpoints)."""
    def decorator(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            adapter = get_adapter() if get_adapter else None
            guard = InferenceGuard(operation, adapter=adapter)
            await guard.__aenter__()
            try:
                async for item in fn(*args, **kwargs):
                    yield item
                await guard.__aexit__(None, None, None)
            except BaseException:
                await guard.__aexit__(*sys.exc_info())
                raise
        return wrapper
    return decorator
