"""
Model management router.

Endpoints:
  GET  /v1/models
  GET  /v1/model/info
  POST /v1/models/switch
  POST /v1/models/reload
  GET  /v1/models/available
  GET  /v1/models/presets
  POST /v1/models/preset/{preset_name}
  POST /v1/models/pull
  GET  /v1/models/pull/{task_id}
  GET  /v1/models/downloads
  GET  /v1/models/profiles
  GET  /v1/models/performance
  GET  /v1/models/{model_id}        (catch-all — MUST be last)
"""

import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from server.helpers import get_state, get_llm, get_swap_tracker
from server.hardware import detect_hardware_summary, GPU_PRESETS
from server.routing import load_model_profiles
from server.schemas import ModelPullRequest

logger = logging.getLogger("api_server")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

router = APIRouter()

# Background download tracker
_download_tasks: Dict[str, Dict[str, Any]] = {}


@router.get("/v1/models")
async def list_models():
    """OpenAI-compatible model listing."""
    state = get_state()
    if not state or not state.ready:
        raise HTTPException(503, "Server not ready")
    return {"object": "list", "data": state.get_available_models()}


@router.get("/v1/model/info")
async def model_info():
    """Model metadata — architecture, vocab size, context length."""
    state = get_state()
    llm = get_llm()
    if not llm:
        raise HTTPException(503, detail="Model not loaded")
    try:
        info = {
            "model": state.model_id if state else "unknown",
            "model_path": getattr(state.get_inner_adapter(), "model_path", None) if state else None,
            "n_vocab": llm.n_vocab(),
            "n_ctx": llm.n_ctx(),
            "n_embd": llm.n_embd() if hasattr(llm, "n_embd") else None,
        }
        if hasattr(llm, "metadata") and llm.metadata:
            info["metadata"] = dict(llm.metadata)
        try:
            info["token_bos"] = llm.token_bos()
            info["token_eos"] = llm.token_eos()
        except Exception as exc:
            logger.debug("%s", exc)
        try:
            if hasattr(llm, "metadata") and llm.metadata:
                tpl = llm.metadata.get("tokenizer.chat_template")
                if tpl:
                    info["chat_template"] = tpl
        except Exception as exc:
            logger.debug("%s", exc)
        if state and state.active_lora:
            info["active_lora"] = state.active_lora
            info["lora_scale"] = state.lora_scale

        # MoE architecture detection
        if hasattr(llm, "metadata") and llm.metadata:
            meta = llm.metadata
            expert_count = None
            expert_used = None
            for key in (
                "llama.expert_count",
                "general.expert_count",
                "model.expert_count",
            ):
                val = meta.get(key)
                if val is not None:
                    expert_count = int(val)
                    break
            for key in (
                "llama.expert_used_count",
                "general.expert_used_count",
                "model.expert_used_count",
            ):
                val = meta.get(key)
                if val is not None:
                    expert_used = int(val)
                    break
            if expert_count and expert_count > 1:
                n_params_total = None
                for key in ("general.parameter_count", "llama.parameter_count"):
                    val = meta.get(key)
                    if val is not None:
                        n_params_total = int(val)
                        break
                active_ratio = expert_used / expert_count if expert_used else None
                active_params = int(n_params_total * active_ratio) if n_params_total and active_ratio else None
                info["architecture"] = "moe"
                info["moe"] = {
                    "expert_count": expert_count,
                    "expert_used_count": expert_used,
                    "active_ratio": round(active_ratio, 3) if active_ratio else None,
                    "total_params": n_params_total,
                    "active_params": active_params,
                    "active_params_human": (
                        f"{active_params / 1e9:.1f}B"
                        if active_params and active_params > 1e9
                        else f"{active_params / 1e6:.0f}M"
                        if active_params
                        else None
                    ),
                }
            else:
                info["architecture"] = "dense"

        return info
    except Exception as e:
        raise HTTPException(500, detail=f"Model info failed: {e}")


@router.post("/v1/models/switch")
async def switch_model(body: Dict[str, str]):
    """Hot-swap the loaded model. Clears response cache."""
    state = get_state()
    swap_tracker = get_swap_tracker()
    model_path = body.get("model_path")
    model_name = body.get("model_name")

    if not model_path and model_name:
        import api_server

        models_dir = api_server._PROJECT_ROOT / "models"
        candidates = []
        if models_dir.exists():
            for gguf in models_dir.rglob("*.gguf"):
                if model_name.lower() in gguf.stem.lower():
                    candidates.append(gguf)
        if len(candidates) == 1:
            model_path = str(candidates[0])
        elif len(candidates) > 1:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Ambiguous model_name '{model_name}'",
                    "matches": [c.name for c in candidates[:10]],
                    "hint": "Use model_path for exact match",
                },
            )
        else:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=404,
                content={
                    "error": f"No GGUF matching '{model_name}' found in models/",
                    "hint": "Use /v1/models/available to list discovered models",
                },
            )

    if not model_path:
        raise HTTPException(400, detail="model_path or model_name required")

    inner = state.get_inner_adapter()
    wrapper = state.adapter
    prev_model = state.model_id
    swap_start = time.perf_counter()

    switched = False
    for obj in (wrapper, inner):
        if hasattr(obj, "switch_model"):
            switched = obj.switch_model(model_path)
            if switched:
                break

    swap_ms = (time.perf_counter() - swap_start) * 1000

    if switched:
        p = Path(model_path)
        state.model_id = p.stem
        state.model_name = p.stem.replace("-", " ").replace("_", " ").title()
        state.cache.clear()
        state.active_lora = None
        state.lora_scale = 1.0
        swap_tracker.record(prev_model, state.model_id, swap_ms, trigger="manual")
        logger.info(f"Switched to model: {p.name} (cache cleared, swap={swap_ms:.0f}ms)")
        return {
            "status": "ok",
            "model": state.model_id,
            "swap_time_ms": round(swap_ms, 1),
        }
    else:
        raise HTTPException(500, detail="Model switch failed")


@router.post("/v1/models/reload")
async def reload_model(body: Dict[str, Any]):
    """Reload model with different GPU layer count."""
    state = get_state()
    n_gpu = body.get("n_gpu_layers")
    if n_gpu is None:
        raise HTTPException(400, detail="n_gpu_layers required")

    inner = state.get_inner_adapter()
    model_path = getattr(inner, "model_path", None)
    if not model_path:
        raise HTTPException(500, detail="No model path available")

    try:
        async with state.inference_semaphore:
            cls = inner.__class__
            with cls._shared_lock:
                if cls._shared_llm is not None:
                    del cls._shared_llm
                    cls._shared_llm = None
                    cls._shared_model_path = None

                from llama_cpp import Llama as _Llama

                llm = _Llama(
                    model_path=model_path,
                    n_gpu_layers=int(n_gpu),
                    n_ctx=4096,
                    n_threads=None,
                    verbose=False,
                )
                cls._shared_llm = llm
                cls._shared_model_path = model_path

        state.cache.clear()
        logger.info(f"Model reloaded with n_gpu_layers={n_gpu}")
        return {"status": "ok", "n_gpu_layers": n_gpu, "model": state.model_id}
    except Exception as e:
        raise HTTPException(500, detail=f"Reload failed: {e}")


@router.get("/v1/models/available")
async def available_models():
    """Discover GGUF models in the models/ directory."""
    state = get_state()
    models_dir = _PROJECT_ROOT / "models"
    discovered = []

    if models_dir.exists():
        for gguf in sorted(models_dir.rglob("*.gguf")):
            size_gb = gguf.stat().st_size / (1024**3)
            discovered.append(
                {
                    "name": gguf.stem,
                    "filename": gguf.name,
                    "path": str(gguf),
                    "size_gb": round(size_gb, 2),
                    "modified": gguf.stat().st_mtime,
                }
            )

    current = state.model_id if state else None
    return {
        "models": discovered,
        "count": len(discovered),
        "current_model": current,
        "models_dir": str(models_dir),
    }


@router.get("/v1/models/presets")
async def list_presets():
    """List available GPU/memory presets for model reload."""
    return {"presets": GPU_PRESETS}


@router.post("/v1/models/preset/{preset_name}")
async def apply_preset(preset_name: str):
    """Reload model with a GPU-poor preset configuration."""
    state = get_state()
    preset = GPU_PRESETS.get(preset_name)
    if not preset:
        raise HTTPException(
            404,
            detail=f"Unknown preset '{preset_name}'. Available: {list(GPU_PRESETS.keys())}",
        )

    inner = state.get_inner_adapter()
    model_path = getattr(inner, "model_path", None)
    if not model_path:
        raise HTTPException(500, detail="No model path available")

    n_gpu = preset["n_gpu_layers"]
    n_ctx = preset["n_ctx"]

    try:
        async with state.inference_semaphore:
            cls = inner.__class__
            with cls._shared_lock:
                if cls._shared_llm is not None:
                    del cls._shared_llm
                    cls._shared_llm = None
                    cls._shared_model_path = None

                from llama_cpp import Llama as _Llama

                llm = _Llama(
                    model_path=model_path,
                    n_gpu_layers=int(n_gpu),
                    n_ctx=int(n_ctx),
                    n_threads=None,
                    verbose=False,
                )
                cls._shared_llm = llm
                cls._shared_model_path = model_path

        # Clear cached hardware summary since config changed
        if hasattr(detect_hardware_summary, "_cached"):
            del detect_hardware_summary._cached  # type: ignore

        state.cache.clear()
        logger.info(f"Preset '{preset_name}' applied: n_gpu_layers={n_gpu}, n_ctx={n_ctx}")
        return {
            "status": "ok",
            "preset": preset_name,
            "n_gpu_layers": n_gpu,
            "n_ctx": n_ctx,
            "description": preset["description"],
            "model": state.model_id,
        }
    except Exception as e:
        raise HTTPException(500, detail=f"Preset apply failed: {e}")


@router.post("/v1/models/pull")
async def pull_model(req: ModelPullRequest):
    """Download a GGUF model from HuggingFace Hub."""
    task_id = f"pull-{uuid.uuid4().hex[:8]}"

    for tid, task in _download_tasks.items():
        if task["repo_id"] == req.repo_id and task["filename"] == req.filename:
            if task["status"] == "downloading":
                return {**task, "status": "already_downloading", "task_id": tid}

    _download_tasks[task_id] = {
        "repo_id": req.repo_id,
        "filename": req.filename,
        "status": "downloading",
        "started": time.time(),
        "completed": None,
        "error": None,
        "local_path": None,
    }

    def _do_download():
        try:
            from huggingface_hub import hf_hub_download

            local_path = hf_hub_download(
                repo_id=req.repo_id,
                filename=req.filename,
                cache_dir=str(_PROJECT_ROOT / "models"),
            )
            _download_tasks[task_id].update(
                {
                    "status": "completed",
                    "completed": time.time(),
                    "local_path": local_path,
                }
            )
            logger.info(f"Model downloaded: {req.repo_id}/{req.filename} -> {local_path}")
        except Exception as e:
            _download_tasks[task_id].update(
                {
                    "status": "failed",
                    "completed": time.time(),
                    "error": str(e),
                }
            )
            logger.error(f"Model download failed: {e}")

    thread = threading.Thread(target=_do_download, daemon=True, name=f"pull-{req.filename}")
    thread.start()

    return {
        "status": "downloading",
        "task_id": task_id,
        "repo_id": req.repo_id,
        "filename": req.filename,
        "message": f"Downloading {req.filename} from {req.repo_id}",
    }


@router.get("/v1/models/pull/{task_id}")
async def pull_status(task_id: str):
    """Check download progress for a model pull operation."""
    task = _download_tasks.get(task_id)
    if not task:
        raise HTTPException(404, detail=f"Download task not found: {task_id}")

    result = {"task_id": task_id, **task}
    if task["completed"]:
        result["elapsed_seconds"] = round(task["completed"] - task["started"], 1)
    else:
        result["elapsed_seconds"] = round(time.time() - task["started"], 1)
    return result


@router.get("/v1/models/downloads")
async def list_downloads():
    """List all model download tasks (active and completed)."""
    return {
        "downloads": [{"task_id": tid, **task} for tid, task in _download_tasks.items()],
        "active": sum(1 for t in _download_tasks.values() if t["status"] == "downloading"),
        "completed": sum(1 for t in _download_tasks.values() if t["status"] == "completed"),
    }


@router.get("/v1/models/profiles", dependencies=[])
async def get_model_profiles():
    """Return full model profiling data."""
    data = load_model_profiles()
    if not data:
        raise HTTPException(
            404,
            detail="No model_profiles.json found. Run 'python UI/model_profiler.py' first.",
        )
    return {
        "ranking": data.get("ranking", []),
        "domain_experts": data.get("domain_experts", {}),
        "routing_table": data.get("routing_table", {}),
        "routing_improvement": data.get("routing_improvement", {}),
        "classifications": data.get("classifications", {}),
        "meta": data.get("meta", {}),
        "hardware": data.get("hardware", {}),
    }


@router.get("/v1/models/performance", dependencies=[])
async def model_performance():
    """Performance profiling summary — speed, latency, memory per model."""
    data = load_model_profiles()
    if not data:
        raise HTTPException(
            404,
            detail="No model_profiles.json found. Run 'python UI/model_profiler.py' first.",
        )

    profiles = data.get("profiles", {})
    perf_summary = {}
    for model_name, profile in profiles.items():
        perf = profile.get("perf_stats", {})
        perf_summary[model_name] = {
            "rounds": profile.get("rounds", 0),
            "tokens_per_sec": perf.get("tokens_per_sec", {}),
            "chars_per_sec": perf.get("chars_per_sec", {}),
            "first_token_time": perf.get("first_token_time", {}),
            "total_time": perf.get("total_time", {}),
            "prompt_eval_tps": perf.get("prompt_eval_tps", {}),
            "load_speed_mb_s": perf.get("load_speed_mb_s", {}),
            "mem_delta_load_mb": perf.get("mem_delta_load_mb", {}),
            "mem_delta_infer_mb": perf.get("mem_delta_infer_mb", {}),
            "reliability": {
                "ok": profile.get("reliability_ok", 0),
                "warn": profile.get("reliability_warn", 0),
                "err": profile.get("reliability_err", 0),
            },
        }

    speed_board = sorted(
        [
            {
                "model": name,
                "mean_tps": stats.get("tokens_per_sec", {}).get("mean", 0),
                "p50_tps": stats.get("tokens_per_sec", {}).get("p50", 0),
                "mean_ttft": stats.get("first_token_time", {}).get("mean", 0),
                "p95_ttft": stats.get("first_token_time", {}).get("p95", 0),
            }
            for name, stats in perf_summary.items()
        ],
        key=lambda x: x["mean_tps"],
        reverse=True,
    )

    return {
        "performance": perf_summary,
        "speed_leaderboard": speed_board,
        "hardware": data.get("hardware", {}),
        "profiled_at": data.get("timestamp", ""),
    }


# =============================================================================
# MODEL MARKETPLACE — browse, search, recommend, download
# =============================================================================


@router.get("/v1/marketplace/hardware")
async def marketplace_hardware():
    """Detect hardware and return profile with tier classification."""
    try:
        from Core.model_marketplace import get_marketplace

        mp = get_marketplace()
        hw = mp.get_hardware(force_refresh=True)
        return hw.to_dict()
    except Exception as e:
        raise HTTPException(500, detail=f"Hardware detection failed: {e}")


@router.get("/v1/marketplace/curated")
async def marketplace_curated():
    """Return all 8 curated Staff Pick models."""
    try:
        from Core.model_marketplace import get_marketplace

        mp = get_marketplace()
        return {
            "models": mp.get_curated_models(),
            "count": len(mp.get_curated_models()),
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/v1/marketplace/recommended")
async def marketplace_recommended():
    """Return curated models filtered by detected hardware tier."""
    try:
        from Core.model_marketplace import get_marketplace

        mp = get_marketplace()
        hw = mp.get_hardware()
        recommended = mp.get_recommended_for_hardware()
        return {
            "models": recommended,
            "count": len(recommended),
            "hardware_tier": hw.tier,
            "hardware_tier_label": hw.tier_label,
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/v1/marketplace/trending")
async def marketplace_trending(limit: int = 6):
    """Fetch trending GGUF models from HuggingFace (cached 1h)."""
    try:
        from Core.model_marketplace import get_marketplace

        mp = get_marketplace()
        trending = mp.get_trending(limit=min(limit, 24))
        return {"models": trending, "count": len(trending)}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/v1/marketplace/search")
async def marketplace_search(query: str, limit: int = 12, sort: str = "downloads"):
    """Search HuggingFace for GGUF models (cached 24h)."""
    if not query or not query.strip():
        raise HTTPException(400, detail="Query is required")
    try:
        from Core.model_marketplace import get_marketplace

        mp = get_marketplace()
        results = mp.search(query, limit=min(limit, 50), sort=sort)
        return {"models": results, "count": len(results), "query": query}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/v1/marketplace/local")
async def marketplace_local():
    """Scan local directories for .gguf model files."""
    try:
        from Core.model_marketplace import get_marketplace

        mp = get_marketplace()
        local = mp.scan_local_models()
        total_gb = sum(m.get("size_gb", 0) for m in local)
        return {
            "models": local,
            "count": len(local),
            "total_size_gb": round(total_gb, 2),
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/v1/marketplace/summary")
async def marketplace_summary():
    """Complete marketplace status: hardware + local + recommended."""
    try:
        from Core.model_marketplace import get_marketplace

        mp = get_marketplace()
        return mp.get_marketplace_summary()
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# NOTE: This catch-all {model_id} route MUST be registered LAST
# to avoid shadowing more specific /v1/models/* routes.
@router.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    """OpenAI-compatible single model info."""
    state = get_state()
    if not state or not state.ready:
        raise HTTPException(503, "Server not ready")
    for m in state.get_available_models():
        if m["id"] == model_id:
            return m
    raise HTTPException(404, f"Model '{model_id}' not found")
