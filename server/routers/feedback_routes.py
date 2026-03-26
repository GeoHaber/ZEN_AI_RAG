"""
Feedback & profiling history router.

Endpoints:
  POST /v1/feedback
  GET  /v1/feedback/stats
  GET  /v1/feedback/history
  GET  /v1/feedback/model/{model_name}
  GET  /v1/feedback/adjustments
  GET  /v1/models/history
  GET  /v1/models/history/compare
  GET  /v1/models/history/trend
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger("api_server")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_PROFILING_RUNS_DIR = _PROJECT_ROOT / "profiling_runs"

router = APIRouter()


def _get_feedback_collector():
    """Get the global FeedbackCollector."""
    import api_server

    return api_server._feedback_collector


# ── Feedback ──────────────────────────────────────────────────────────


@router.post("/v1/feedback")
async def submit_feedback(body: Dict[str, Any]):
    """Submit quality feedback for a model response."""
    from server.feedback import FeedbackCollector

    collector = _get_feedback_collector()
    model = (body.get("model") or "").strip()
    if not model:
        raise HTTPException(400, detail="'model' is required")

    thumbs = body.get("thumbs")
    if thumbs is not None and thumbs not in ("up", "down"):
        raise HTTPException(400, detail="'thumbs' must be 'up' or 'down'")

    rating = body.get("rating")
    if rating is not None:
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            raise HTTPException(400, detail="'rating' must be integer 1-5")

    tags = body.get("tags", [])
    if tags:
        invalid = [t for t in tags if t not in FeedbackCollector.VALID_TAGS]
        if invalid:
            raise HTTPException(
                400,
                detail=f"Invalid tags: {invalid}. Valid: {sorted(FeedbackCollector.VALID_TAGS)}",
            )

    entry = collector.submit(
        model=model,
        thumbs=thumbs,
        rating=rating,
        tags=tags,
        response_id=body.get("response_id"),
        comment=body.get("comment"),
    )
    return {"status": "ok", "feedback": entry}


@router.get("/v1/feedback/stats", dependencies=[])
async def feedback_stats():
    """Global feedback statistics."""
    return _get_feedback_collector().stats()


@router.get("/v1/feedback/history", dependencies=[])
async def feedback_history(
    last_n: int = 20,
    model: Optional[str] = None,
):
    """Recent feedback entries (newest first)."""
    entries = _get_feedback_collector().history(last_n=last_n, model=model)
    return {"count": len(entries), "entries": entries}


@router.get("/v1/feedback/model/{model_name}", dependencies=[])
async def feedback_model_summary(model_name: str):
    """Aggregated feedback summary for a specific model."""
    summary = _get_feedback_collector().model_summary(model_name)
    if not summary:
        raise HTTPException(404, detail=f"No feedback found for model '{model_name}'")
    return summary


@router.get("/v1/feedback/adjustments", dependencies=[])
async def feedback_routing_adjustments():
    """Per-model routing score adjustments derived from user feedback."""
    collector = _get_feedback_collector()
    adjustments = collector.routing_adjustments()
    summaries = collector.all_summaries()
    return {
        "adjustments": adjustments,
        "model_summaries": summaries,
        "min_feedback_threshold": 3,
        "adjustment_range": "-10 to +10 points",
    }


# ── Profiling Run History ────────────────────────────────────────────


@router.get("/v1/models/history", dependencies=[])
async def profiling_history():
    """List all archived profiling runs, newest first."""
    if not _PROFILING_RUNS_DIR.exists():
        return {"runs": [], "count": 0}

    runs = []
    for fp in sorted(_PROFILING_RUNS_DIR.glob("profile_*.json"), reverse=True):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            runs.append(
                {
                    "run_id": data.get("run_id", fp.stem.replace("profile_", "")),
                    "timestamp": data.get("timestamp", ""),
                    "model_count": len(data.get("profiles", {})),
                    "categories": data.get("meta", {}).get("categories_tested", []),
                    "elapsed": data.get("meta", {}).get("elapsed_human", ""),
                    "profiler_version": data.get("profiler_version", "unknown"),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue

    return {"runs": runs, "count": len(runs)}


def _load_archived_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Load an archived profiling run by run_id."""
    if not _PROFILING_RUNS_DIR.exists():
        return None
    candidate = _PROFILING_RUNS_DIR / f"profile_{run_id}.json"
    if candidate.exists():
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    for fp in _PROFILING_RUNS_DIR.glob("profile_*.json"):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("run_id") == run_id:
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return None


@router.get("/v1/models/history/compare", dependencies=[])
async def compare_profiling_runs(run1: str, run2: str):
    """Compare two archived profiling runs."""
    r1_data = _load_archived_run(run1)
    if not r1_data:
        raise HTTPException(404, detail=f"Run '{run1}' not found in profiling_runs/")
    r2_data = _load_archived_run(run2)
    if not r2_data:
        raise HTTPException(404, detail=f"Run '{run2}' not found in profiling_runs/")

    r1_profiles = r1_data.get("profiles", {})
    r2_profiles = r2_data.get("profiles", {})
    r1_models = set(r1_profiles.keys())
    r2_models = set(r2_profiles.keys())
    common = sorted(r1_models & r2_models)

    r1_rank = {r["model"]: r["rank"] for r in r1_data.get("ranking", [])}
    r2_rank = {r["model"]: r["rank"] for r in r2_data.get("ranking", [])}
    ranking_changes = [
        {
            "model": m,
            "old_rank": r1_rank.get(m, 0),
            "new_rank": r2_rank.get(m, 0),
            "direction": "improved" if r2_rank.get(m, 0) < r1_rank.get(m, 0) else "declined",
        }
        for m in common
        if r1_rank.get(m) != r2_rank.get(m)
    ]

    r1_exp = r1_data.get("domain_experts", {})
    r2_exp = r2_data.get("domain_experts", {})
    all_domains = sorted(set(list(r1_exp.keys()) + list(r2_exp.keys())))
    domain_expert_changes = [
        {
            "domain": d,
            "old_expert": r1_exp.get(d, {}).get("model", ""),
            "new_expert": r2_exp.get(d, {}).get("model", ""),
            "old_score": r1_exp.get(d, {}).get("avg_score", 0),
            "new_score": r2_exp.get(d, {}).get("avg_score", 0),
        }
        for d in all_domains
        if r1_exp.get(d, {}).get("model") != r2_exp.get(d, {}).get("model")
    ]

    perf_keys = [
        "tokens_per_sec",
        "first_token_time",
        "total_time",
        "chars_per_sec",
        "prompt_eval_tps",
        "load_speed_mb_s",
    ]
    metric_deltas = {}
    for m in common:
        p1 = r1_profiles[m].get("perf_stats", {})
        p2 = r2_profiles[m].get("perf_stats", {})
        deltas = {}
        for pk in perf_keys:
            old_mean = p1.get(pk, {}).get("mean", 0)
            new_mean = p2.get(pk, {}).get("mean", 0)
            if old_mean or new_mean:
                deltas[pk] = {
                    "old": round(old_mean, 3),
                    "new": round(new_mean, 3),
                    "delta": round(new_mean - old_mean, 3),
                    "pct_change": round(((new_mean - old_mean) / old_mean) * 100, 1) if old_mean else None,
                }
        old_avg = r1_profiles[m].get("avg_overall", 0)
        new_avg = r2_profiles[m].get("avg_overall", 0)
        deltas["avg_overall"] = {
            "old": round(old_avg, 1),
            "new": round(new_avg, 1),
            "delta": round(new_avg - old_avg, 1),
        }
        metric_deltas[m] = deltas

    r1_ri = r1_data.get("routing_improvement", {})
    r2_ri = r2_data.get("routing_improvement", {})

    return {
        "run1": {"run_id": run1, "timestamp": r1_data.get("timestamp", "")},
        "run2": {"run_id": run2, "timestamp": r2_data.get("timestamp", "")},
        "new_models": sorted(r2_models - r1_models),
        "removed_models": sorted(r1_models - r2_models),
        "ranking_changes": ranking_changes,
        "domain_expert_changes": domain_expert_changes,
        "metric_deltas": metric_deltas,
        "routing_improvement_delta": {
            "old_routed_avg": r1_ri.get("routed_avg", 0),
            "new_routed_avg": r2_ri.get("routed_avg", 0),
            "old_improvement": r1_ri.get("improvement_points", 0),
            "new_improvement": r2_ri.get("improvement_points", 0),
        },
    }


@router.get("/v1/models/history/trend", dependencies=[])
async def profiling_trend(metric: str = "avg_overall"):
    """Get trend data for a metric across all archived runs."""
    if not _PROFILING_RUNS_DIR.exists():
        return {"metric": metric, "trend": {}, "run_count": 0}

    run_files = sorted(_PROFILING_RUNS_DIR.glob("profile_*.json"))
    trend: Dict[str, list] = {}
    run_count = 0

    for fp in run_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        run_count += 1
        profiles = data.get("profiles", {})
        for model_name, profile in profiles.items():
            if metric == "avg_overall":
                value = profile.get("avg_overall", 0)
            else:
                value = profile.get("perf_stats", {}).get(metric, {}).get("mean", 0)
            if model_name not in trend:
                trend[model_name] = []
            trend[model_name].append(
                {
                    "run_id": data.get("run_id", ""),
                    "timestamp": data.get("timestamp", ""),
                    "value": round(value, 3),
                }
            )

    return {"metric": metric, "trend": trend, "run_count": run_count}
