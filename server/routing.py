"""
Domain/difficulty classification, compound strategies, RAG-aware routing.

Extracted from api_server.py.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from server.helpers import get_state

logger = logging.getLogger("api_server")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Model profiles cache ─────────────────────────────────────────────────

_model_profiles: Optional[Dict[str, Any]] = None
_model_profiles_mtime: float = 0.0


def load_model_profiles() -> Optional[Dict[str, Any]]:
    """Load model_profiles.json, auto-reload if file changed."""
    global _model_profiles, _model_profiles_mtime
    profiles_path = _PROJECT_ROOT / "model_profiles.json"
    if not profiles_path.exists():
        return _model_profiles

    try:
        mtime = profiles_path.stat().st_mtime
        if mtime != _model_profiles_mtime:
            with open(profiles_path, "r", encoding="utf-8") as f:
                _model_profiles = json.load(f)
            _model_profiles_mtime = mtime
            logger.info(
                "Loaded model profiles (%d models, %d domains)",
                len(_model_profiles.get("profiles", {})),
                len(_model_profiles.get("domain_experts", {})),
            )
    except Exception as e:
        logger.warning("Failed to load model_profiles.json: %s", e)

    return _model_profiles


# ── Domain classification ────────────────────────────────────────────────

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "\U0001f9e0 Reasoning": [
        "logic",
        "puzzle",
        "reason",
        "deduc",
        "syllogism",
        "fallacy",
        "think step",
    ],
    "\U0001f40d Python": [
        "python",
        "def ",
        "class ",
        "import ",
        "pip",
        "django",
        "flask",
        "pandas",
        "numpy",
    ],
    "\U0001f4bb Coding": [
        "code",
        "program",
        "function",
        "algorithm",
        "debug",
        "syntax",
        "compile",
        "refactor",
        "javascript",
        "typescript",
        "rust",
        "golang",
        "java",
        "c++",
        "sql",
    ],
    "\U0001f3e5 Medical": [
        "medical",
        "diagnos",
        "symptom",
        "patient",
        "treatment",
        "disease",
        "clinical",
        "pharma",
        "drug",
        "therapy",
        "health",
    ],
    "\U0001f52c Science": [
        "physics",
        "chemistry",
        "biology",
        "quantum",
        "molecular",
        "evolution",
        "experiment",
        "hypothesis",
        "scientific",
    ],
    "\U0001f9d1\u200d\U0001f3eb Math": [
        "math",
        "calcul",
        "equation",
        "proof",
        "algebra",
        "geometry",
        "integral",
        "derivative",
        "statistic",
        "probability",
    ],
    "\u270d\ufe0f Writing": [
        "write",
        "essay",
        "article",
        "paragraph",
        "summarize",
        "rephrase",
        "grammar",
        "proofread",
        "edit text",
    ],
    "\U0001f4ca Analysis": [
        "analy",
        "compare",
        "evaluate",
        "assess",
        "review",
        "metric",
        "data",
        "trend",
        "insight",
        "business",
    ],
    "\U0001f30d Translation": [
        "translat",
        "language",
        "spanish",
        "french",
        "german",
        "chinese",
        "japanese",
        "korean",
        "multilingual",
        "locali",
    ],
    "\U0001f3a8 Creative": [
        "creative",
        "story",
        "poem",
        "fiction",
        "imagin",
        "invent",
        "metaphor",
        "narrative",
    ],
    "\u2696\ufe0f Ethics": [
        "ethic",
        "moral",
        "dilemma",
        "right wrong",
        "bias",
        "fair",
        "responsibility",
        "privacy",
    ],
    "\U0001f50d Truthfulness": [
        "true",
        "false",
        "myth",
        "fact check",
        "misinformation",
        "debunk",
    ],
    "\U0001f4a1 Common Sense": [
        "common sense",
        "everyday",
        "practical",
        "obvious",
        "basic knowledge",
    ],
    "\U0001f4cb Instructions": [
        "instruction",
        "follow",
        "format",
        "exactly",
        "step by step",
        "list",
        "numbered",
        "bullet",
    ],
}


def classify_query_domain(query: str) -> Tuple[Optional[str], float]:
    """Classify a query into its best-matching domain category."""
    query_lower = query.lower()
    scores: Dict[str, int] = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > 0:
            scores[domain] = score

    if not scores:
        return None, 0.0

    best_domain = max(scores, key=scores.get)
    max_possible = len(DOMAIN_KEYWORDS[best_domain])
    confidence = min(1.0, scores[best_domain] / max(max_possible * 0.3, 1))

    return best_domain, round(confidence, 2)


# ── Difficulty classification ────────────────────────────────────────────

DIFFICULTY_HARD_SIGNALS = [
    "step by step",
    "explain in detail",
    "compare and contrast",
    "analyze",
    "multi-step",
    "complex",
    "advanced",
    "prove",
    "derive",
    "optimize",
    "trade-off",
    "tradeoff",
    "architecture",
    "design pattern",
    "refactor",
    "concurrent",
    "async",
    "distributed",
    "scalab",
    "security vulnerabilit",
    "differential equation",
    "integral",
    "theorem",
    "proof",
    "implement from scratch",
    "write a full",
    "build a complete",
    "evaluate the implications",
    "critique",
    "synthesize",
]

DIFFICULTY_EASY_SIGNALS = [
    "what is",
    "define ",
    "who is",
    "when was",
    "where is",
    "how many",
    "true or false",
    "yes or no",
    "name the",
    "list ",
    "simple",
    "basic",
    "beginner",
    "trivial",
    "quick question",
    "hello",
    "hi ",
    "hey ",
    "thanks",
    "thank you",
    "translate this word",
    "spell ",
    "capitalize",
    "what does",
    "meaning of",
]


def classify_query_difficulty(query: str) -> str:
    """Estimate query difficulty: 'easy', 'medium', or 'hard'."""
    q = query.strip()
    q_lower = q.lower()
    length = len(q)

    hard_hits = sum(1 for s in DIFFICULTY_HARD_SIGNALS if s in q_lower)
    easy_hits = sum(1 for s in DIFFICULTY_EASY_SIGNALS if s in q_lower)

    has_code = "```" in q or q.count("\n") > 10
    sentences = len([s for s in q.split(".") if len(s.strip()) > 10])

    if hard_hits >= 2 or (length > 300 and hard_hits >= 1):
        return "hard"
    if has_code and length > 200:
        return "hard"
    if sentences >= 4 and hard_hits >= 1:
        return "hard"

    if easy_hits >= 1 and length < 80 and hard_hits == 0:
        return "easy"
    if length < 40 and hard_hits == 0:
        return "easy"

    return "medium"


# ── Compound Strategies ──────────────────────────────────────────────────

BUILTIN_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "quality_first": {
        "description": "Maximum quality — domain expert with fallback to overall best",
        "steps": [
            {"method": "domain_expert", "min_confidence": 0.4},
            {"method": "difficulty_expert", "min_confidence": 0.0},
            {"method": "overall_best", "min_confidence": 0.0},
        ],
    },
    "speed_first": {
        "description": "Minimum latency — keep current model, or pick the fastest",
        "steps": [
            {"method": "current", "min_confidence": 0.0},
            {"method": "fastest", "min_confidence": 0.0},
        ],
    },
    "balanced": {
        "description": "Balance quality and speed — domain expert only if confident, else fastest",
        "steps": [
            {"method": "domain_expert", "min_confidence": 0.6},
            {"method": "difficulty_expert", "min_confidence": 0.0},
            {"method": "fastest", "min_confidence": 0.0},
        ],
    },
    "cascade": {
        "description": "Full cascade — domain → difficulty → best → current",
        "steps": [
            {"method": "domain_expert", "min_confidence": 0.3},
            {"method": "difficulty_expert", "min_confidence": 0.0},
            {"method": "overall_best", "min_confidence": 0.0},
            {"method": "current", "min_confidence": 0.0},
        ],
    },
}

custom_strategies: Dict[str, Dict[str, Any]] = {}


def resolve_strategy_step(
    method: str,
    query: str,
    data: Dict[str, Any],
    domain: Optional[str],
    domain_confidence: float,
    difficulty: str,
) -> Optional[Dict[str, Any]]:
    """Resolve a single strategy step to a model recommendation."""
    state = get_state()
    profiles = data.get("profiles", {})
    experts = data.get("domain_experts", {})
    diff_experts = data.get("difficulty_experts", {})
    routing_table = data.get("routing_table", {})
    diff_routing = data.get("difficulty_routing_table", {})
    ranking = data.get("ranking", [])

    if method == "domain_expert":
        if domain and domain in experts:
            expert = experts[domain]
            return {
                "model": expert["model"],
                "path": routing_table.get(domain),
                "reason": f"domain expert for {domain}",
                "score": expert.get("avg_score", 0),
            }
        return None

    if method == "difficulty_expert":
        if difficulty in diff_experts:
            info = diff_experts[difficulty]
            model = info.get("speed_pick", info["model"]) if difficulty == "easy" else info["model"]
            return {
                "model": model,
                "path": diff_routing.get(difficulty),
                "reason": f"difficulty expert for {difficulty}",
                "score": info.get("avg_score", 0),
            }
        return None

    if method == "overall_best":
        if ranking:
            best = ranking[0]
            model_name = best["model"]
            path = None
            for p in routing_table.values():
                if model_name in str(p):
                    path = p
                    break
            return {
                "model": model_name,
                "path": path,
                "reason": "overall best ranked model",
                "score": best.get("avg_overall", 0),
            }
        return None

    if method == "fastest":
        fastest_model = None
        fastest_tps = 0.0
        for name, profile in profiles.items():
            tps = profile.get("avg_tokens_per_sec", 0)
            if tps > fastest_tps:
                fastest_tps = tps
                fastest_model = name
        if fastest_model:
            path = None
            for p in routing_table.values():
                if fastest_model in str(p):
                    path = p
                    break
            return {
                "model": fastest_model,
                "path": path,
                "reason": f"fastest model ({fastest_tps:.1f} tok/s)",
                "score": profiles[fastest_model].get("avg_overall", 0),
            }
        return None

    if method == "current":
        current = state.model_id if state else None
        if current:
            score = profiles.get(current, {}).get("avg_overall", 0)
            return {
                "model": current,
                "path": None,
                "reason": "keep current model (zero swap cost)",
                "score": score,
            }
        return None

    return None


def evaluate_strategy(
    strategy_name: str,
    steps: List[Dict[str, Any]],
    query: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Walk a strategy's fallback chain and return the first viable pick."""
    state = get_state()
    domain, domain_confidence = classify_query_domain(query)
    difficulty = classify_query_difficulty(query)

    chain_log: List[Dict[str, Any]] = []
    selected = None

    for i, step in enumerate(steps):
        method = step.get("method", "unknown")
        min_conf = step.get("min_confidence", 0.0)

        result = resolve_strategy_step(method, query, data, domain, domain_confidence, difficulty)

        entry = {
            "step": i + 1,
            "method": method,
            "min_confidence": min_conf,
            "result": None,
            "accepted": False,
        }

        if result:
            entry["result"] = {
                "model": result["model"],
                "score": result["score"],
                "reason": result["reason"],
            }
            if method == "domain_expert":
                if domain_confidence >= min_conf:
                    entry["accepted"] = True
                    if not selected:
                        selected = result
                else:
                    entry["skipped_reason"] = f"confidence {domain_confidence:.2f} < threshold {min_conf}"
            else:
                entry["accepted"] = True
                if not selected:
                    selected = result

        chain_log.append(entry)

    if not selected:
        ranking = data.get("ranking", [])
        if ranking:
            selected = {
                "model": ranking[0]["model"],
                "path": None,
                "reason": "fallback: no strategy step matched",
                "score": ranking[0].get("avg_overall", 0),
            }

    current_model = state.model_id if state else None
    return {
        "strategy": strategy_name,
        "recommended_model": selected["model"] if selected else current_model,
        "reason": selected["reason"] if selected else "no recommendation",
        "model_score": selected["score"] if selected else 0,
        "model_path": selected.get("path") if selected else None,
        "domain": domain,
        "domain_confidence": domain_confidence,
        "difficulty": difficulty,
        "current_model": current_model,
        "needs_switch": (selected["model"] != current_model if selected else False),
        "chain": chain_log,
        "steps_evaluated": len(chain_log),
        "winning_step": next(
            (
                e["step"]
                for e in chain_log
                if e["accepted"] and e.get("result", {}).get("model") == (selected["model"] if selected else None)
            ),
            None,
        ),
    }


# ── RAG-Aware Routing ────────────────────────────────────────────────────

DEFAULT_RAG_WEIGHTS: Dict[str, float] = {
    "quality": 0.5,
    "context_speed": 0.3,
    "generation_speed": 0.2,
}


def estimate_rag_context(
    rag_stats: Dict[str, Any],
    chunk_count: int = 0,
    avg_chunk_tokens: int = 256,
) -> Dict[str, Any]:
    """Estimate RAG context characteristics."""
    docs = rag_stats.get("documents_uploaded", 0)
    collections = rag_stats.get("collections", {})
    total_size = rag_stats.get("total_collection_size", 0)
    n_collections = len(collections) if isinstance(collections, dict) else 0

    if chunk_count > 0:
        est_tokens = chunk_count * avg_chunk_tokens
    elif total_size > 0:
        est_tokens = total_size // 4
    else:
        est_tokens = 0

    return {
        "active": docs > 0 or est_tokens > 0,
        "estimated_tokens": est_tokens,
        "documents": docs,
        "collections": n_collections,
    }


def score_model_for_rag(
    model_name: str,
    profile: Dict[str, Any],
    context_tokens: int,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Score a single model for RAG-augmented routing."""
    w = weights or DEFAULT_RAG_WEIGHTS

    n_ctx = profile.get("n_ctx", 0)
    if n_ctx > 0 and context_tokens > n_ctx:
        return {
            "model": model_name,
            "rag_score": 0.0,
            "fits_context": False,
            "disqualified_reason": f"context {context_tokens} tokens > model n_ctx {n_ctx}",
            "breakdown": {},
        }

    quality_raw = profile.get("avg_overall", 50.0)
    quality_norm = min(quality_raw / 100.0, 1.0)

    perf = profile.get("perf_stats", {})
    pe_data = perf.get("prompt_eval_tps", {})
    pe_tps = pe_data.get("mean", 0.0) if isinstance(pe_data, dict) else 0.0
    ctx_speed_norm = min(pe_tps / 500.0, 1.0)

    gen_tps = profile.get("avg_tokens_per_sec", 0.0)
    gen_speed_norm = min(gen_tps / 100.0, 1.0)

    wq = w.get("quality", 0.5)
    wc = w.get("context_speed", 0.3)
    wg = w.get("generation_speed", 0.2)

    rag_score = round(wq * quality_norm + wc * ctx_speed_norm + wg * gen_speed_norm, 4)

    return {
        "model": model_name,
        "rag_score": rag_score,
        "fits_context": True,
        "disqualified_reason": None,
        "breakdown": {
            "quality": round(quality_norm, 4),
            "quality_weight": wq,
            "context_speed": round(ctx_speed_norm, 4),
            "context_speed_weight": wc,
            "generation_speed": round(gen_speed_norm, 4),
            "generation_speed_weight": wg,
            "prompt_eval_tps": pe_tps,
            "avg_tokens_per_sec": gen_tps,
        },
    }


def rank_models_for_rag(
    profiles_data: Dict[str, Any],
    context_tokens: int,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Rank all profiled models for a RAG-augmented query."""
    profiles = profiles_data.get("profiles", {})
    scored = []
    excluded = []

    for model_name, profile in profiles.items():
        result = score_model_for_rag(model_name, profile, context_tokens, weights)
        if result["fits_context"]:
            scored.append(result)
        else:
            excluded.append(result)

    scored.sort(key=lambda x: x["rag_score"], reverse=True)

    recommended = scored[0]["model"] if scored else None

    return {
        "recommended": recommended,
        "rankings": scored,
        "excluded": excluded,
        "context_tokens": context_tokens,
        "weights_used": weights or DEFAULT_RAG_WEIGHTS,
    }
