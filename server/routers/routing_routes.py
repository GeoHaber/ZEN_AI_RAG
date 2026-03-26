"""
Routing router — domain routing, difficulty, strategies, RAG-aware routing, swap cost.

Endpoints:
  POST /v1/models/route
  GET  /v1/models/domains
  GET  /v1/models/difficulty
  POST /v1/models/classify-difficulty
  GET  /v1/models/swap-history
  GET  /v1/models/swap-cost
  GET  /v1/models/strategies
  POST /v1/models/route/strategy
  POST /v1/models/strategies/custom
  DELETE /v1/models/strategies/custom/{strategy_name}
  POST /v1/models/route/rag
  GET  /v1/models/rag/status
  GET  /v1/models/rag/rankings
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from server.helpers import get_state, get_swap_tracker
from server.routing import (
    load_model_profiles,
    classify_query_domain,
    classify_query_difficulty,
    DOMAIN_KEYWORDS,
    DIFFICULTY_HARD_SIGNALS,
    DIFFICULTY_EASY_SIGNALS,
    BUILTIN_STRATEGIES,
    custom_strategies,
    evaluate_strategy,
    estimate_rag_context,
    rank_models_for_rag,
    DEFAULT_RAG_WEIGHTS,
)

logger = logging.getLogger("api_server")

router = APIRouter()


@router.post("/v1/models/route")
async def route_query(body: Dict[str, Any]):
    """Route a query to the best model for its domain."""
    state = get_state()
    swap_tracker = get_swap_tracker()
    data = load_model_profiles()
    if not data:
        raise HTTPException(
            404,
            detail="No model profiles available. Run 'python UI/model_profiler.py' to generate.",
        )

    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(400, detail="'query' field is required")

    auto_switch = body.get("auto_switch", False)
    domain_override = body.get("domain")
    difficulty_override = body.get("difficulty")

    difficulty = (
        difficulty_override if difficulty_override in ("easy", "medium", "hard") else classify_query_difficulty(query)
    )

    if domain_override:
        domain = None
        for d in data.get("domain_experts", {}):
            if domain_override.lower() in d.lower():
                domain = d
                break
        confidence = 1.0 if domain else 0.0
        if not domain:
            raise HTTPException(
                400,
                detail=f"Unknown domain '{domain_override}'. Available: {list(data.get('domain_experts', {}).keys())}",
            )
    else:
        domain, confidence = classify_query_domain(query)

    experts = data.get("domain_experts", {})

    if domain and domain in experts:
        expert = experts[domain]
        rec_model = expert["model"]
        rec_path = data.get("routing_table", {}).get(domain)
        alt_model = expert.get("runner_up", "—")
        domain_scores = expert.get("all_ranked", [])
    else:
        ranking = data.get("ranking", [])
        if ranking:
            rec_model = ranking[0]["model"]
        else:
            rec_model = state.model_id if state else "unknown"
        rec_path = None
        alt_model = ranking[1]["model"] if len(ranking) > 1 else "—"
        domain = "general"
        domain_scores = ranking[:5]

    difficulty_experts = data.get("difficulty_experts", {})
    difficulty_rec = None
    if difficulty in difficulty_experts:
        diff_info = difficulty_experts[difficulty]
        if difficulty == "easy":
            difficulty_rec = diff_info.get("speed_pick", diff_info["model"])
        else:
            difficulty_rec = diff_info["model"]

    response = {
        "recommended_model": rec_model,
        "domain": domain,
        "difficulty": difficulty,
        "difficulty_recommendation": difficulty_rec,
        "confidence": confidence,
        "current_model": state.model_id if state else None,
        "needs_switch": rec_model != (state.model_id if state else None),
        "alternative": alt_model,
        "domain_scores": domain_scores,
        "auto_switched": False,
    }

    if response["needs_switch"]:
        response["swap_cost_estimate_ms"] = swap_tracker.estimate_swap_cost_ms()

    if auto_switch and response["needs_switch"] and rec_path:
        try:
            prev_model = state.model_id if state else "unknown"
            swap_start = time.perf_counter()

            inner = state.get_inner_adapter()
            wrapper = state.adapter
            switched = False
            for obj in (wrapper, inner):
                if hasattr(obj, "switch_model"):
                    switched = obj.switch_model(rec_path)
                    if switched:
                        break

            swap_ms = (time.perf_counter() - swap_start) * 1000

            if switched:
                p = Path(rec_path)
                state.model_id = p.stem
                state.model_name = p.stem.replace("-", " ").replace("_", " ").title()
                state.cache.clear()
                state.active_lora = None
                state.lora_scale = 1.0
                swap_tracker.record(prev_model, state.model_id, swap_ms, trigger="route_auto")
                response["auto_switched"] = True
                response["needs_switch"] = False
                response["swap_time_ms"] = round(swap_ms, 1)
                logger.info(f"Auto-routed to domain expert: {rec_model} for [{domain}] (swap={swap_ms:.0f}ms)")
        except Exception as e:
            response["switch_error"] = str(e)
            logger.warning(f"Auto-switch failed: {e}")

    return response


@router.get("/v1/models/domains", dependencies=[])
async def list_domains():
    """List all domain categories and their expert models."""
    data = load_model_profiles()
    if not data:
        return {
            "domains": list(DOMAIN_KEYWORDS.keys()),
            "experts": {},
            "note": "No profiles yet. Run 'python UI/model_profiler.py' to populate.",
        }

    experts = data.get("domain_experts", {})
    return {
        "domains": list(DOMAIN_KEYWORDS.keys()),
        "experts": {
            cat: {
                "model": info["model"],
                "score": info["avg_score"],
                "margin": info["margin"],
            }
            for cat, info in experts.items()
        },
        "routing_improvement": data.get("routing_improvement", {}),
    }


@router.get("/v1/models/difficulty", dependencies=[])
async def difficulty_scores():
    """Per-difficulty routing data."""
    data = load_model_profiles()
    if not data:
        raise HTTPException(
            404,
            detail="No model_profiles.json found. Run 'python UI/model_profiler.py' first.",
        )

    diff_experts = data.get("difficulty_experts", {})
    profiles = data.get("profiles", {})

    model_difficulty = {}
    for model_name, profile in profiles.items():
        ds = profile.get("difficulty_scores", {})
        model_difficulty[model_name] = {
            level: {
                "mean": ds.get(level, {}).get("mean", 0),
                "count": ds.get(level, {}).get("count", 0),
            }
            for level in ("easy", "medium", "hard")
        }

    return {
        "difficulty_experts": {
            level: {
                "model": info["model"],
                "speed_pick": info.get("speed_pick", info["model"]),
                "avg_score": info["avg_score"],
                "margin": info["margin"],
            }
            for level, info in diff_experts.items()
        },
        "model_difficulty_breakdown": model_difficulty,
        "classify_hint": "POST /v1/models/route with 'difficulty' field to use difficulty routing",
    }


@router.post("/v1/models/classify-difficulty", dependencies=[])
async def classify_difficulty(body: Dict[str, Any]):
    """Classify a query's difficulty level without routing."""
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(400, detail="'query' field is required")

    difficulty = classify_query_difficulty(query)

    q_lower = query.lower()
    signals = {
        "length": len(query),
        "hard_signals": [s for s in DIFFICULTY_HARD_SIGNALS if s in q_lower],
        "easy_signals": [s for s in DIFFICULTY_EASY_SIGNALS if s in q_lower],
        "has_code_block": "```" in query,
        "sentence_count": len([s for s in query.split(".") if len(s.strip()) > 10]),
    }

    return {"difficulty": difficulty, "signals": signals}


# ── Swap Cost Tracking ────────────────────────────────────────────────


@router.get("/v1/models/swap-history", dependencies=[])
async def swap_history(last_n: int = 20):
    """Recent model swap events with timing."""
    swap_tracker = get_swap_tracker()
    n = min(max(1, last_n), 100)
    events = swap_tracker.history(n)
    return {
        "events": events,
        "count": len(events),
        "stats": swap_tracker.stats(),
    }


@router.get("/v1/models/swap-cost", dependencies=[])
async def swap_cost_analysis():
    """Aggregate swap cost analysis."""
    swap_tracker = get_swap_tracker()
    stats = swap_tracker.stats()
    data = load_model_profiles()

    cost_benefit = None
    if stats["total_swaps"] > 0 and data:
        routing_imp = data.get("routing_improvement", {})
        improvement_pts = routing_imp.get("improvement_points", 0)
        single_avg = routing_imp.get("single_model_avg", 0)

        (improvement_pts / stats["total_swaps"] if improvement_pts > 0 else 0)
        cost_benefit = {
            "quality_gain_points": improvement_pts,
            "quality_gain_pct": (round((improvement_pts / single_avg) * 100, 1) if single_avg > 0 else 0),
            "avg_swap_overhead_ms": stats["avg_swap_ms"],
            "overhead_per_quality_point_ms": (
                round(stats["avg_swap_ms"] / improvement_pts, 1) if improvement_pts > 0 else 0
            ),
            "total_downtime_seconds": round(stats["total_downtime_ms"] / 1000, 2),
            "recommendation": (
                "beneficial" if improvement_pts >= 2 else "marginal" if improvement_pts > 0 else "no_gain"
            ),
        }

    return {
        "stats": stats,
        "cost_benefit": cost_benefit,
        "estimate_next_swap_ms": swap_tracker.estimate_swap_cost_ms(),
    }


# ── Compound Strategies ──────────────────────────────────────────────


@router.get("/v1/models/strategies", dependencies=[])
async def list_strategies():
    """List all available routing strategies (built-in + custom)."""
    all_strategies = {**BUILTIN_STRATEGIES, **custom_strategies}
    return {
        "strategies": {
            name: {
                "description": s["description"],
                "steps": s["steps"],
                "builtin": name in BUILTIN_STRATEGIES,
            }
            for name, s in all_strategies.items()
        },
        "count": len(all_strategies),
        "hint": "POST /v1/models/route/strategy with strategy + query",
    }


@router.post("/v1/models/route/strategy")
async def route_with_strategy(body: Dict[str, Any]):
    """Route a query using a named compound strategy with fallback chain."""
    state = get_state()
    swap_tracker = get_swap_tracker()
    data = load_model_profiles()
    if not data:
        raise HTTPException(
            404,
            detail="No model profiles available. Run 'python UI/model_profiler.py' first.",
        )

    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(400, detail="'query' field is required")

    strategy_name = body.get("strategy", "cascade")
    auto_switch = body.get("auto_switch", False)
    inline_steps = body.get("steps")

    if inline_steps and isinstance(inline_steps, list):
        steps = inline_steps
        strategy_name = "custom"
    else:
        all_strategies = {**BUILTIN_STRATEGIES, **custom_strategies}
        strat = all_strategies.get(strategy_name)
        if not strat:
            raise HTTPException(
                400,
                detail=f"Unknown strategy '{strategy_name}'. Available: {list(all_strategies.keys())}",
            )
        steps = strat["steps"]

    result = evaluate_strategy(strategy_name, steps, query, data)
    result["auto_switched"] = False

    if result["needs_switch"]:
        result["swap_cost_estimate_ms"] = swap_tracker.estimate_swap_cost_ms()

    if auto_switch and result["needs_switch"] and result.get("model_path"):
        try:
            prev_model = state.model_id if state else "unknown"
            swap_start = time.perf_counter()

            inner = state.get_inner_adapter()
            wrapper = state.adapter
            switched = False
            for obj in (wrapper, inner):
                if hasattr(obj, "switch_model"):
                    switched = obj.switch_model(result["model_path"])
                    if switched:
                        break

            swap_ms = (time.perf_counter() - swap_start) * 1000

            if switched:
                p = Path(result["model_path"])
                state.model_id = p.stem
                state.model_name = p.stem.replace("-", " ").replace("_", " ").title()
                state.cache.clear()
                state.active_lora = None
                state.lora_scale = 1.0
                swap_tracker.record(prev_model, state.model_id, swap_ms, trigger="strategy_auto")
                result["auto_switched"] = True
                result["needs_switch"] = False
                result["swap_time_ms"] = round(swap_ms, 1)
                logger.info(
                    f"Strategy '{strategy_name}' auto-switched to {result['recommended_model']} (swap={swap_ms:.0f}ms)"
                )
        except Exception as e:
            result["switch_error"] = str(e)
            logger.warning(f"Strategy auto-switch failed: {e}")

    return result


@router.post("/v1/models/strategies/custom")
async def create_custom_strategy(body: Dict[str, Any]):
    """Create or update a custom routing strategy."""
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(400, detail="'name' is required")
    if name in BUILTIN_STRATEGIES:
        raise HTTPException(
            400,
            detail=f"Cannot overwrite built-in strategy '{name}'. Built-in: {list(BUILTIN_STRATEGIES.keys())}",
        )

    desc = body.get("description", "Custom strategy")
    steps = body.get("steps", [])
    if not steps or not isinstance(steps, list):
        raise HTTPException(400, detail="'steps' must be a non-empty list")

    valid_methods = {
        "domain_expert",
        "difficulty_expert",
        "overall_best",
        "fastest",
        "current",
    }
    for i, step in enumerate(steps):
        m = step.get("method", "")
        if m not in valid_methods:
            raise HTTPException(
                400,
                detail=f"Step {i + 1}: unknown method '{m}'. Valid: {sorted(valid_methods)}",
            )

    custom_strategies[name] = {
        "description": desc,
        "steps": steps,
    }
    logger.info(f"Custom strategy created: '{name}' ({len(steps)} steps)")
    return {
        "status": "ok",
        "name": name,
        "steps": len(steps),
        "total_strategies": len(BUILTIN_STRATEGIES) + len(custom_strategies),
    }


@router.delete("/v1/models/strategies/custom/{strategy_name}")
async def delete_custom_strategy(strategy_name: str):
    """Delete a custom routing strategy."""
    if strategy_name not in custom_strategies:
        raise HTTPException(404, detail=f"Custom strategy '{strategy_name}' not found")
    del custom_strategies[strategy_name]
    return {"status": "ok", "deleted": strategy_name}


# ── RAG-Aware Routing ────────────────────────────────────────────────


@router.post("/v1/models/route/rag", dependencies=[])
async def route_for_rag(body: Dict[str, Any]):
    """Route model selection factoring in RAG context."""
    state = get_state()
    swap_tracker = get_swap_tracker()
    query = (body.get("query") or "").strip()
    if not query:
        raise HTTPException(400, detail="'query' is required")

    data = load_model_profiles()
    if not data:
        raise HTTPException(404, detail="No model profiles found")

    context_tokens = body.get("context_tokens", 0)
    chunk_count = body.get("chunk_count", 0)
    avg_chunk_tokens = body.get("avg_chunk_tokens", 256)

    rag_stats: Dict[str, Any] = {}
    try:
        from rag_integration import _rag_integration

        if _rag_integration and _rag_integration.initialized:
            rag_stats = _rag_integration.get_stats()
    except Exception as exc:
        logger.debug("%s", exc)

    ctx_info = estimate_rag_context(rag_stats, chunk_count, avg_chunk_tokens)
    if context_tokens <= 0:
        context_tokens = ctx_info["estimated_tokens"]

    weights = body.get("weights", None)
    ranking = rank_models_for_rag(data, context_tokens, weights)

    current_model = state.model_id if state else None
    needs_switch = ranking["recommended"] is not None and ranking["recommended"] != current_model

    result = {
        "query": query,
        "recommended_model": ranking["recommended"],
        "current_model": current_model,
        "needs_switch": needs_switch,
        "rag_context": ctx_info,
        "context_tokens": context_tokens,
        "rankings": ranking["rankings"],
        "excluded": ranking["excluded"],
        "weights_used": ranking["weights_used"],
    }

    if needs_switch and swap_tracker:
        est = swap_tracker.estimate_swap_cost_ms()
        if est:
            result["swap_cost_estimate_ms"] = est

    if body.get("auto_switch") and needs_switch and ranking["recommended"]:
        recommended = ranking["recommended"]
        routing_table = data.get("routing_table", {})
        model_path = None
        for _domain, path in routing_table.items():
            if recommended in path:
                model_path = path
                break
        if model_path:
            from server.routers.models import switch_model as _switch

            t0 = time.perf_counter()
            await _switch({"model_path": model_path})
            elapsed = (time.perf_counter() - t0) * 1000
            result["switched"] = True
            result["switch_time_ms"] = round(elapsed, 1)
            if swap_tracker:
                swap_tracker.record(
                    current_model or "unknown",
                    recommended,
                    elapsed,
                    trigger="rag_route",
                )

    return result


@router.get("/v1/models/rag/status", dependencies=[])
async def rag_routing_status():
    """Return current RAG context status for routing decisions."""
    rag_stats: Dict[str, Any] = {}
    try:
        from rag_integration import _rag_integration

        if _rag_integration and _rag_integration.initialized:
            rag_stats = _rag_integration.get_stats()
    except Exception as exc:
        logger.debug("%s", exc)

    ctx_info = estimate_rag_context(rag_stats)
    return {
        "rag_initialized": bool(rag_stats.get("initialized", False)),
        "rag_active": ctx_info["active"],
        "documents": ctx_info["documents"],
        "collections": ctx_info["collections"],
        "estimated_context_tokens": ctx_info["estimated_tokens"],
        "default_weights": DEFAULT_RAG_WEIGHTS,
    }


@router.get("/v1/models/rag/rankings", dependencies=[])
async def rag_model_rankings(
    context_tokens: int = 0,
    quality_weight: float = 0.5,
    context_speed_weight: float = 0.3,
    generation_speed_weight: float = 0.2,
):
    """Preview RAG-aware model rankings without routing."""
    data = load_model_profiles()
    if not data:
        raise HTTPException(404, detail="No model profiles found")

    weights = {
        "quality": quality_weight,
        "context_speed": context_speed_weight,
        "generation_speed": generation_speed_weight,
    }
    ranking = rank_models_for_rag(data, context_tokens, weights)
    return ranking
