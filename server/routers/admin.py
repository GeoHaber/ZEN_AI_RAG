"""
Admin router — health, metrics, stats, diagnostics, LoRA, state, compact, version.

Endpoints:
  GET  /health
  GET  /metrics, /v1/metrics
  GET  /v1/stats
  GET  /v1/diagnostics
  GET  /v1/diagnostics/crashes
  GET  /v1/diagnostics/profiles
  POST /v1/cache/clear
  POST /v1/compact
  POST /v1/lora/load
  DELETE /v1/lora/unload
  GET  /v1/lora/status
  POST /v1/state/save
  POST /v1/state/load
  GET  /v1/state/slots
  DELETE /v1/state/{slot_name}
  GET  /v1/system/hardware
  GET  /api/version
"""

import logging
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from server.schemas import (
    CompactRequest,
    LoRALoadRequest,
    StateSaveRequest,
    StateLoadRequest,
)
from server.helpers import get_state, get_llm, get_token_streamer
from server.hardware import detect_hardware_summary, detect_hardware_full

from inference_guard import (
    get_guard_stats,
    get_crash_history,
    get_request_profiles,
    get_memory_snapshot,
)
from compact_tokens import compact_messages, CompactConfig

logger = logging.getLogger("api_server")

router = APIRouter()


@router.get("/health", dependencies=[])
async def health():
    """Health check — public, no auth required."""
    state = get_state()
    result = {
        "status": "ok" if state and state.ready else "initializing",
        "version": "3.5.0",
        "provider": state.provider if state else None,
        "model": state.model_id if state else None,
        "uptime_seconds": int(time.time() - state.start_time) if state else 0,
        "requests_served": state.request_count if state else 0,
        "cache": state.cache.stats() if state else None,
        "streaming": "true_token_level" if get_token_streamer() else "batched",
    }
    try:
        hw = detect_hardware_summary()
        if hw:
            result["hardware"] = hw
    except Exception as exc:
        logger.debug("%s", exc)
    return result


@router.get("/metrics", dependencies=[])
@router.get("/v1/metrics", dependencies=[])
async def prometheus_metrics():
    """Prometheus-compatible text exposition."""
    state = get_state()
    lines = []

    def _counter(name, help_text, value):
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {value}")

    def _gauge(name, help_text, value):
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {value}")

    if state:
        _counter("ragrat_requests_total", "Total requests served", state.request_count)
        _counter(
            "ragrat_cache_served_total",
            "Requests served from cache",
            state.cache_served,
        )
        _counter(
            "ragrat_tokens_generated_total",
            "Approximate tokens generated",
            state.total_tokens_approx,
        )
        cs = state.cache.stats()
        _gauge("ragrat_cache_size", "Current cache entries", cs["size"])
        _counter("ragrat_cache_hits_total", "Cache hits", cs["hits"])
        _counter("ragrat_cache_misses_total", "Cache misses", cs["misses"])
        _gauge(
            "ragrat_uptime_seconds",
            "Server uptime",
            int(time.time() - state.start_time),
        )

    gs = get_guard_stats()
    _counter(
        "ragrat_inference_calls_total",
        "Total guarded inference calls",
        gs.get("total_guarded_calls", 0),
    )
    _counter("ragrat_crashes_total", "Total inference crashes", gs.get("total_crashes", 0))

    timing = gs.get("timing", {})
    _gauge(
        "ragrat_inference_avg_ms",
        "Average inference time (ms)",
        f"{timing.get('avg_ms', 0):.1f}",
    )
    _gauge(
        "ragrat_inference_fastest_ms",
        "Fastest inference (ms)",
        f"{timing.get('fastest_ms', 0):.1f}" if timing.get("fastest_ms") else "0",
    )
    _gauge(
        "ragrat_inference_slowest_ms",
        "Slowest inference (ms)",
        f"{timing.get('slowest_ms', 0):.1f}",
    )

    mem = get_memory_snapshot()
    if mem:
        _gauge(
            "ragrat_process_rss_mb",
            "Process RSS (MB)",
            f"{mem.get('process_rss_mb', 0):.1f}",
        )
        _gauge(
            "ragrat_system_memory_percent",
            "System memory usage (%)",
            f"{mem.get('system_percent', 0):.1f}",
        )

    return PlainTextResponse(
        "\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/v1/stats")
async def stats():
    """Server statistics."""
    state = get_state()
    if not state:
        return {"status": "not initialized"}

    guard_stats = get_guard_stats()
    timing = guard_stats.get("timing", {})

    avg_tps = state.total_tokens_approx / (timing.get("total_ms", 0) / 1000) if timing.get("total_ms", 0) > 0 else 0

    info = {
        "version": "3.5.0",
        "uptime_seconds": int(time.time() - state.start_time),
        "provider": state.provider,
        "model": state.model_id,
        "requests_served": state.request_count,
        "cache_served": state.cache_served,
        "approx_tokens_generated": state.total_tokens_approx,
        "timing": {
            "avg_inference_ms": timing.get("avg_ms", 0),
            "fastest_ms": timing.get("fastest_ms"),
            "slowest_ms": timing.get("slowest_ms", 0),
            "avg_tokens_per_sec": round(avg_tps, 1),
        },
        "cache": state.cache.stats(),
        "streaming": ("true_token_level" if get_token_streamer() else "batched_fallback"),
    }

    inner = state.get_inner_adapter()
    if hasattr(inner, "get_stats"):
        info["fifo"] = inner.get_stats()

    return info


@router.post("/v1/cache/clear")
async def clear_cache():
    """Clear the response cache."""
    state = get_state()
    if not state:
        raise HTTPException(503, "Server not initialized")
    old_stats = state.cache.stats()
    state.cache.clear()
    return {"status": "ok", "cleared_entries": old_stats["size"]}


@router.post("/v1/compact")
async def compact_endpoint(req: CompactRequest):
    """Compact a conversation to reduce token count."""
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    if not messages:
        raise HTTPException(400, "messages required")

    config = CompactConfig(
        keep_last_n=req.keep_last_n,
        summarize_older=req.summarize_older,
        compress_text=req.compress_text,
        target_ctx_tokens=req.target_tokens,
    )

    compacted, stats_data = compact_messages(messages, config)
    return {"messages": compacted, "stats": stats_data}


@router.get("/v1/diagnostics")
async def diagnostics():
    """Inference diagnostics — memory, crash data, FIFO state."""
    state = get_state()
    result = {
        "guard_stats": get_guard_stats(),
        "memory": get_memory_snapshot(),
        "recent_crashes": get_crash_history()[:10],
    }

    if state and state.adapter:
        inner = state.get_inner_adapter()
        if hasattr(inner, "get_stats"):
            result["fifo"] = inner.get_stats()

    return result


@router.get("/v1/diagnostics/crashes")
async def crash_history_endpoint():
    """Full crash history (last 50 crashes)."""
    return {
        "stats": get_guard_stats(),
        "crashes": get_crash_history(),
    }


@router.get("/v1/diagnostics/profiles")
async def profiles_endpoint(last_n: int = 20):
    """Per-request profiling."""
    profiles = get_request_profiles(last_n=min(last_n, 100))
    return {
        "stats": get_guard_stats(),
        "profile_count": len(profiles),
        "profiles": profiles,
    }


# ── LoRA ──────────────────────────────────────────────────────────────


@router.post("/v1/lora/load")
async def load_lora(req: LoRALoadRequest):
    """Load a LoRA adapter at runtime."""
    state = get_state()
    llm = get_llm()
    if not llm:
        raise HTTPException(503, detail="Model not loaded")

    lora_path = Path(req.lora_path)
    if not lora_path.exists():
        raise HTTPException(404, detail=f"LoRA file not found: {req.lora_path}")

    try:
        async with state.inference_semaphore:
            if hasattr(llm, "load_lora_adapter"):
                llm.load_lora_adapter(str(lora_path), scale=req.scale)
            elif hasattr(llm, "set_lora"):
                llm.set_lora(str(lora_path), scale=req.scale)
            else:
                raise HTTPException(
                    501,
                    detail="LoRA API not available in this llama-cpp-python version",
                )

        state.active_lora = str(lora_path)
        state.lora_scale = req.scale
        state.cache.clear()
        logger.info(f"LoRA loaded: {lora_path.name} (scale={req.scale})")
        return {
            "status": "ok",
            "lora_path": str(lora_path),
            "lora_name": lora_path.stem,
            "scale": req.scale,
            "model": state.model_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=f"LoRA load failed: {e}")


@router.delete("/v1/lora/unload")
async def unload_lora():
    """Remove the currently loaded LoRA adapter."""
    state = get_state()
    llm = get_llm()
    if not llm:
        raise HTTPException(503, detail="Model not loaded")

    if not state.active_lora:
        return {"status": "ok", "message": "No LoRA adapter loaded"}

    try:
        async with state.inference_semaphore:
            if hasattr(llm, "unload_lora_adapter"):
                llm.unload_lora_adapter()
            elif hasattr(llm, "set_lora"):
                llm.set_lora(None)

        prev = state.active_lora
        state.active_lora = None
        state.lora_scale = 1.0
        state.cache.clear()
        logger.info(f"LoRA unloaded: {prev}")
        return {"status": "ok", "unloaded": prev}
    except Exception as e:
        raise HTTPException(500, detail=f"LoRA unload failed: {e}")


@router.get("/v1/lora/status")
async def lora_status():
    """Check current LoRA adapter status."""
    state = get_state()
    return {
        "active": state.active_lora is not None if state else False,
        "lora_path": state.active_lora if state else None,
        "scale": state.lora_scale if state else 1.0,
        "model": state.model_id if state else None,
    }


# ── State Save/Load ──────────────────────────────────────────────────


@router.post("/v1/state/save")
async def save_state(req: StateSaveRequest):
    """Save the model's KV-cache state to disk."""
    state = get_state()
    llm = get_llm()
    if not llm:
        raise HTTPException(503, detail="Model not loaded")

    slot_file = state._states_dir / f"{req.slot_name}.bin"

    try:
        async with state.inference_semaphore:
            if hasattr(llm, "save_state"):
                llm_state = llm.save_state()
                slot_file.write_bytes(llm_state)
            else:
                raise HTTPException(
                    501,
                    detail="State save not supported in this llama-cpp-python version",
                )

        size_mb = slot_file.stat().st_size / (1024 * 1024)
        logger.info(f"State saved: {req.slot_name} ({size_mb:.1f} MB)")
        return {
            "status": "ok",
            "slot_name": req.slot_name,
            "path": str(slot_file),
            "size_mb": round(size_mb, 2),
            "model": state.model_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=f"State save failed: {e}")


@router.post("/v1/state/load")
async def load_state(req: StateLoadRequest):
    """Load a previously saved KV-cache state from disk."""
    state = get_state()
    llm = get_llm()
    if not llm:
        raise HTTPException(503, detail="Model not loaded")

    slot_file = state._states_dir / f"{req.slot_name}.bin"
    if not slot_file.exists():
        available = [f.stem for f in state._states_dir.glob("*.bin")]
        raise HTTPException(
            404,
            detail=f"State slot '{req.slot_name}' not found. Available: {available}",
        )

    try:
        async with state.inference_semaphore:
            if hasattr(llm, "load_state"):
                state_data = slot_file.read_bytes()
                llm.load_state(state_data)
            else:
                raise HTTPException(
                    501,
                    detail="State load not supported in this llama-cpp-python version",
                )

        size_mb = slot_file.stat().st_size / (1024 * 1024)
        logger.info(f"State loaded: {req.slot_name} ({size_mb:.1f} MB)")
        return {
            "status": "ok",
            "slot_name": req.slot_name,
            "size_mb": round(size_mb, 2),
            "model": state.model_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=f"State load failed: {e}")


@router.get("/v1/state/slots")
async def list_state_slots():
    """List all saved state slots with metadata."""
    state = get_state()
    slots = []
    if state and state._states_dir.exists():
        for f in state._states_dir.glob("*.bin"):
            slots.append(
                {
                    "slot_name": f.stem,
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    "created": f.stat().st_mtime,
                }
            )
    return {"slots": slots, "count": len(slots)}


@router.delete("/v1/state/{slot_name}")
async def delete_state_slot(slot_name: str):
    """Delete a saved state slot."""
    state = get_state()
    if not state:
        raise HTTPException(503, detail="Server not initialized")
    slot_file = state._states_dir / f"{slot_name}.bin"
    if not slot_file.exists():
        raise HTTPException(404, detail=f"State slot '{slot_name}' not found")
    slot_file.unlink()
    logger.info(f"State slot deleted: {slot_name}")
    return {"status": "ok", "deleted": slot_name}


# ── Hardware ──────────────────────────────────────────────────────────


@router.get("/v1/system/hardware", dependencies=[])
async def system_hardware():
    """Full hardware report with model recommendations."""
    return detect_hardware_full()


# ── Version ───────────────────────────────────────────────────────────


@router.get("/api/version", dependencies=[])
async def api_version():
    """Simple version endpoint — compatible with Ollama's /api/version."""
    return {
        "version": "3.5.0",
        "name": "RAG_RAT API Server",
        "api_compatibility": "OpenAI",
        "features": [
            "chat_completions",
            "completions",
            "embeddings",
            "tool_calling",
            "fim_infill",
            "structured_output",
            "lora_hot_swap",
            "model_pull",
            "state_save_load",
            "tokenize",
            "detokenize",
            "metrics",
            "diagnostics",
            "moe_detection",
            "hardware_detection",
            "model_router",
            "gpu_presets",
            "model_discovery",
            "domain_routing",
            "performance_profiling",
            "run_history",
            "difficulty_routing",
            "swap_cost_tracking",
            "compound_strategies",
            "rag_aware_routing",
            "live_feedback_loop",
        ],
    }
