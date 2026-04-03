/// Routing router — domain routing, difficulty, strategies, RAG-aware routing, swap cost.
/// 
/// Endpoints:
/// POST /v1/models/route
/// GET  /v1/models/domains
/// GET  /v1/models/difficulty
/// POST /v1/models/classify-difficulty
/// GET  /v1/models/swap-history
/// GET  /v1/models/swap-cost
/// GET  /v1/models/strategies
/// POST /v1/models/route/strategy
/// POST /v1/models/strategies/custom
/// DELETE /v1/models/strategies/custom/{strategy_name}
/// POST /v1/models/route/rag
/// GET  /v1/models/rag/status
/// GET  /v1/models/rag/rankings

use anyhow::{Result, Context};
use crate::helpers::{get_state, get_swap_tracker};
use crate::routing::{load_model_profiles, classify_query_domain, classify_query_difficulty, DOMAIN_KEYWORDS, DIFFICULTY_HARD_SIGNALS, DIFFICULTY_EASY_SIGNALS, BUILTIN_STRATEGIES, custom_strategies, evaluate_strategy, estimate_rag_context, rank_models_for_rag, DEFAULT_RAG_WEIGHTS};
use std::collections::HashMap;
use std::collections::HashSet;
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static ROUTER: std::sync::LazyLock<APIRouter> = std::sync::LazyLock::new(|| Default::default());

/// Route a query to the best model for its domain.
pub async fn route_query(body: HashMap<String, Box<dyn std::any::Any>>) -> Result<()> {
    // Route a query to the best model for its domain.
    let mut state = get_state();
    let mut swap_tracker = get_swap_tracker();
    let mut data = load_model_profiles();
    if !data {
        return Err(anyhow::anyhow!("HTTPException(404, detail=\"No model profiles available. Run 'python UI/model_profiler.py' to generate.\")"));
    }
    let mut query = body.get(&"query".to_string()).cloned().unwrap_or("".to_string()).trim().to_string();
    if !query {
        return Err(anyhow::anyhow!("HTTPException(400, detail=\"'query' field is required\")"));
    }
    let mut auto_switch = body.get(&"auto_switch".to_string()).cloned().unwrap_or(false);
    let mut domain_override = body.get(&"domain".to_string()).cloned();
    let mut difficulty_override = body.get(&"difficulty".to_string()).cloned();
    let mut difficulty = if ("easy".to_string(), "medium".to_string(), "hard".to_string()).contains(&difficulty_override) { difficulty_override } else { classify_query_difficulty(query) };
    if domain_override {
        let mut domain = None;
        for d in data.get(&"domain_experts".to_string()).cloned().unwrap_or(HashMap::new()).iter() {
            if d.to_lowercase().contains(&domain_override.to_lowercase()) {
                let mut domain = d;
                break;
            }
        }
        let mut confidence = if domain { 1.0_f64 } else { 0.0_f64 };
        if !domain {
            return Err(anyhow::anyhow!("HTTPException(400, detail=f\"Unknown domain '{domain_override}'. Available: {list(data.get('domain_experts', {}).keys())}\")"));
        }
    } else {
        let (mut domain, mut confidence) = classify_query_domain(query);
    }
    let mut experts = data.get(&"domain_experts".to_string()).cloned().unwrap_or(HashMap::new());
    if (domain && experts.contains(&domain)) {
        let mut expert = experts[&domain];
        let mut rec_model = expert["model".to_string()];
        let mut rec_path = data.get(&"routing_table".to_string()).cloned().unwrap_or(HashMap::new()).get(&domain).cloned();
        let mut alt_model = expert.get(&"runner_up".to_string()).cloned().unwrap_or("—".to_string());
        let mut domain_scores = expert.get(&"all_ranked".to_string()).cloned().unwrap_or(vec![]);
    } else {
        let mut ranking = data.get(&"ranking".to_string()).cloned().unwrap_or(vec![]);
        if ranking {
            let mut rec_model = ranking[0]["model".to_string()];
        } else {
            let mut rec_model = if state { state::model_id } else { "unknown".to_string() };
        }
        let mut rec_path = None;
        let mut alt_model = if ranking.len() > 1 { ranking[1]["model".to_string()] } else { "—".to_string() };
        let mut domain = "general".to_string();
        let mut domain_scores = ranking[..5];
    }
    let mut difficulty_experts = data.get(&"difficulty_experts".to_string()).cloned().unwrap_or(HashMap::new());
    let mut difficulty_rec = None;
    if difficulty_experts.contains(&difficulty) {
        let mut diff_info = difficulty_experts[&difficulty];
        if difficulty == "easy".to_string() {
            let mut difficulty_rec = diff_info.get(&"speed_pick".to_string()).cloned().unwrap_or(diff_info["model".to_string()]);
        } else {
            let mut difficulty_rec = diff_info["model".to_string()];
        }
    }
    let mut response = HashMap::from([("recommended_model".to_string(), rec_model), ("domain".to_string(), domain), ("difficulty".to_string(), difficulty), ("difficulty_recommendation".to_string(), difficulty_rec), ("confidence".to_string(), confidence), ("current_model".to_string(), if state { state::model_id } else { None }), ("needs_switch".to_string(), rec_model != if state { state::model_id } else { None }), ("alternative".to_string(), alt_model), ("domain_scores".to_string(), domain_scores), ("auto_switched".to_string(), false)]);
    if response["needs_switch".to_string()] {
        response["swap_cost_estimate_ms".to_string()] = swap_tracker.estimate_swap_cost_ms();
    }
    if (auto_switch && response["needs_switch".to_string()] && rec_path) {
        // try:
        {
            let mut prev_model = if state { state::model_id } else { "unknown".to_string() };
            let mut swap_start = time::perf_counter();
            let mut inner = state::get_inner_adapter();
            let mut wrapper = state::adapter;
            let mut switched = false;
            for obj in (wrapper, inner).iter() {
                if /* hasattr(obj, "switch_model".to_string()) */ true {
                    let mut switched = obj.switch_model(rec_path);
                    if switched {
                        break;
                    }
                }
            }
            let mut swap_ms = ((time::perf_counter() - swap_start) * 1000);
            if switched {
                let mut p = PathBuf::from(rec_path);
                state::model_id = p.file_stem().unwrap_or_default().to_str().unwrap_or("");
                state::model_name = /* title */ p.file_stem().unwrap_or_default().to_str().unwrap_or("").replace(&*"-".to_string(), &*" ".to_string()).replace(&*"_".to_string(), &*" ".to_string()).to_string();
                state::cache::clear();
                state::active_lora = None;
                state::lora_scale = 1.0_f64;
                swap_tracker.record(prev_model, state::model_id, swap_ms, /* trigger= */ "route_auto".to_string());
                response["auto_switched".to_string()] = true;
                response["needs_switch".to_string()] = false;
                response["swap_time_ms".to_string()] = ((swap_ms as f64) * 10f64.powi(1)).round() / 10f64.powi(1);
                logger.info(format!("Auto-routed to domain expert: {} for [{}] (swap={:.0}ms)", rec_model, domain, swap_ms));
            }
        }
        // except Exception as e:
    }
    Ok(response)
}

/// List all domain categories and their expert models.
pub async fn list_domains() -> () {
    // List all domain categories and their expert models.
    let mut data = load_model_profiles();
    if !data {
        HashMap::from([("domains".to_string(), DOMAIN_KEYWORDS.keys().into_iter().collect::<Vec<_>>()), ("experts".to_string(), HashMap::new()), ("note".to_string(), "No profiles yet. Run 'python UI/model_profiler.py' to populate.".to_string())])
    }
    let mut experts = data.get(&"domain_experts".to_string()).cloned().unwrap_or(HashMap::new());
    HashMap::from([("domains".to_string(), DOMAIN_KEYWORDS.keys().into_iter().collect::<Vec<_>>()), ("experts".to_string(), experts.iter().iter().map(|(cat, info)| (cat, HashMap::from([("model".to_string(), info["model".to_string()]), ("score".to_string(), info["avg_score".to_string()]), ("margin".to_string(), info["margin".to_string()])]))).collect::<HashMap<_, _>>()), ("routing_improvement".to_string(), data.get(&"routing_improvement".to_string()).cloned().unwrap_or(HashMap::new()))])
}

/// Per-difficulty routing data.
pub async fn difficulty_scores() -> Result<()> {
    // Per-difficulty routing data.
    let mut data = load_model_profiles();
    if !data {
        return Err(anyhow::anyhow!("HTTPException(404, detail=\"No model_profiles.json found. Run 'python UI/model_profiler.py' first.\")"));
    }
    let mut diff_experts = data.get(&"difficulty_experts".to_string()).cloned().unwrap_or(HashMap::new());
    let mut profiles = data.get(&"profiles".to_string()).cloned().unwrap_or(HashMap::new());
    let mut model_difficulty = HashMap::new();
    for (model_name, profile) in profiles.iter().iter() {
        let mut ds = profile.get(&"difficulty_scores".to_string()).cloned().unwrap_or(HashMap::new());
        model_difficulty[model_name] = ("easy".to_string(), "medium".to_string(), "hard".to_string()).iter().map(|level| (level, HashMap::from([("mean".to_string(), ds.get(&level).cloned().unwrap_or(HashMap::new()).get(&"mean".to_string()).cloned().unwrap_or(0)), ("count".to_string(), ds.get(&level).cloned().unwrap_or(HashMap::new()).get(&"count".to_string()).cloned().unwrap_or(0))]))).collect::<HashMap<_, _>>();
    }
    Ok(HashMap::from([("difficulty_experts".to_string(), diff_experts.iter().iter().map(|(level, info)| (level, HashMap::from([("model".to_string(), info["model".to_string()]), ("speed_pick".to_string(), info.get(&"speed_pick".to_string()).cloned().unwrap_or(info["model".to_string()])), ("avg_score".to_string(), info["avg_score".to_string()]), ("margin".to_string(), info["margin".to_string()])]))).collect::<HashMap<_, _>>()), ("model_difficulty_breakdown".to_string(), model_difficulty), ("classify_hint".to_string(), "POST /v1/models/route with 'difficulty' field to use difficulty routing".to_string())]))
}

/// Classify a query's difficulty level without routing.
pub async fn classify_difficulty(body: HashMap<String, Box<dyn std::any::Any>>) -> Result<()> {
    // Classify a query's difficulty level without routing.
    let mut query = body.get(&"query".to_string()).cloned().unwrap_or("".to_string()).trim().to_string();
    if !query {
        return Err(anyhow::anyhow!("HTTPException(400, detail=\"'query' field is required\")"));
    }
    let mut difficulty = classify_query_difficulty(query);
    let mut q_lower = query.to_lowercase();
    let mut signals = HashMap::from([("length".to_string(), query.len()), ("hard_signals".to_string(), DIFFICULTY_HARD_SIGNALS.iter().filter(|s| q_lower.contains(&s)).map(|s| s).collect::<Vec<_>>()), ("easy_signals".to_string(), DIFFICULTY_EASY_SIGNALS.iter().filter(|s| q_lower.contains(&s)).map(|s| s).collect::<Vec<_>>()), ("has_code_block".to_string(), query.contains(&"```".to_string())), ("sentence_count".to_string(), query.split(".".to_string()).map(|s| s.to_string()).collect::<Vec<String>>().iter().filter(|s| s.trim().to_string().len() > 10).map(|s| s).collect::<Vec<_>>().len())]);
    Ok(HashMap::from([("difficulty".to_string(), difficulty), ("signals".to_string(), signals)]))
}

/// Recent model swap events with timing.
pub async fn swap_history(last_n: i64) -> () {
    // Recent model swap events with timing.
    let mut swap_tracker = get_swap_tracker();
    let mut n = 1.max(last_n).min(100);
    let mut events = swap_tracker.history(n);
    HashMap::from([("events".to_string(), events), ("count".to_string(), events.len()), ("stats".to_string(), swap_tracker.stats())])
}

/// Aggregate swap cost analysis.
pub async fn swap_cost_analysis() -> () {
    // Aggregate swap cost analysis.
    let mut swap_tracker = get_swap_tracker();
    let mut stats = swap_tracker.stats();
    let mut data = load_model_profiles();
    let mut cost_benefit = None;
    if (stats["total_swaps".to_string()] > 0 && data) {
        let mut routing_imp = data.get(&"routing_improvement".to_string()).cloned().unwrap_or(HashMap::new());
        let mut improvement_pts = routing_imp.get(&"improvement_points".to_string()).cloned().unwrap_or(0);
        let mut single_avg = routing_imp.get(&"single_model_avg".to_string()).cloned().unwrap_or(0);
        if improvement_pts > 0 { (improvement_pts / stats["total_swaps".to_string()]) } else { 0 };
        let mut cost_benefit = HashMap::from([("quality_gain_points".to_string(), improvement_pts), ("quality_gain_pct".to_string(), if single_avg > 0 { ((((improvement_pts / single_avg) * 100) as f64) * 10f64.powi(1)).round() / 10f64.powi(1) } else { 0 }), ("avg_swap_overhead_ms".to_string(), stats["avg_swap_ms".to_string()]), ("overhead_per_quality_point_ms".to_string(), if improvement_pts > 0 { (((stats["avg_swap_ms".to_string()] / improvement_pts) as f64) * 10f64.powi(1)).round() / 10f64.powi(1) } else { 0 }), ("total_downtime_seconds".to_string(), (((stats["total_downtime_ms".to_string()] / 1000) as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("recommendation".to_string(), if improvement_pts >= 2 { "beneficial".to_string() } else { if improvement_pts > 0 { "marginal".to_string() } else { "no_gain".to_string() } })]);
    }
    HashMap::from([("stats".to_string(), stats), ("cost_benefit".to_string(), cost_benefit), ("estimate_next_swap_ms".to_string(), swap_tracker.estimate_swap_cost_ms())])
}

/// List all available routing strategies (built-in + custom).
pub async fn list_strategies() -> () {
    // List all available routing strategies (built-in + custom).
    let mut all_strategies = HashMap::new();
    HashMap::from([("strategies".to_string(), all_strategies.iter().iter().map(|(name, s)| (name, HashMap::from([("description".to_string(), s["description".to_string()]), ("steps".to_string(), s["steps".to_string()]), ("builtin".to_string(), BUILTIN_STRATEGIES.contains(&name))]))).collect::<HashMap<_, _>>()), ("count".to_string(), all_strategies.len()), ("hint".to_string(), "POST /v1/models/route/strategy with strategy + query".to_string())])
}

/// Route a query using a named compound strategy with fallback chain.
pub async fn route_with_strategy(body: HashMap<String, Box<dyn std::any::Any>>) -> Result<()> {
    // Route a query using a named compound strategy with fallback chain.
    let mut state = get_state();
    let mut swap_tracker = get_swap_tracker();
    let mut data = load_model_profiles();
    if !data {
        return Err(anyhow::anyhow!("HTTPException(404, detail=\"No model profiles available. Run 'python UI/model_profiler.py' first.\")"));
    }
    let mut query = body.get(&"query".to_string()).cloned().unwrap_or("".to_string()).trim().to_string();
    if !query {
        return Err(anyhow::anyhow!("HTTPException(400, detail=\"'query' field is required\")"));
    }
    let mut strategy_name = body.get(&"strategy".to_string()).cloned().unwrap_or("cascade".to_string());
    let mut auto_switch = body.get(&"auto_switch".to_string()).cloned().unwrap_or(false);
    let mut inline_steps = body.get(&"steps".to_string()).cloned();
    if (inline_steps && /* /* isinstance(inline_steps, list) */ */ true) {
        let mut steps = inline_steps;
        let mut strategy_name = "custom".to_string();
    } else {
        let mut all_strategies = HashMap::new();
        let mut strat = all_strategies.get(&strategy_name).cloned();
        if !strat {
            return Err(anyhow::anyhow!("HTTPException(400, detail=f\"Unknown strategy '{strategy_name}'. Available: {list(all_strategies.keys())}\")"));
        }
        let mut steps = strat["steps".to_string()];
    }
    let mut result = evaluate_strategy(strategy_name, steps, query, data);
    result["auto_switched".to_string()] = false;
    if result["needs_switch".to_string()] {
        result["swap_cost_estimate_ms".to_string()] = swap_tracker.estimate_swap_cost_ms();
    }
    if (auto_switch && result["needs_switch".to_string()] && result.get(&"model_path".to_string()).cloned()) {
        // try:
        {
            let mut prev_model = if state { state::model_id } else { "unknown".to_string() };
            let mut swap_start = time::perf_counter();
            let mut inner = state::get_inner_adapter();
            let mut wrapper = state::adapter;
            let mut switched = false;
            for obj in (wrapper, inner).iter() {
                if /* hasattr(obj, "switch_model".to_string()) */ true {
                    let mut switched = obj.switch_model(result["model_path".to_string()]);
                    if switched {
                        break;
                    }
                }
            }
            let mut swap_ms = ((time::perf_counter() - swap_start) * 1000);
            if switched {
                let mut p = PathBuf::from(result["model_path".to_string()]);
                state::model_id = p.file_stem().unwrap_or_default().to_str().unwrap_or("");
                state::model_name = /* title */ p.file_stem().unwrap_or_default().to_str().unwrap_or("").replace(&*"-".to_string(), &*" ".to_string()).replace(&*"_".to_string(), &*" ".to_string()).to_string();
                state::cache::clear();
                state::active_lora = None;
                state::lora_scale = 1.0_f64;
                swap_tracker.record(prev_model, state::model_id, swap_ms, /* trigger= */ "strategy_auto".to_string());
                result["auto_switched".to_string()] = true;
                result["needs_switch".to_string()] = false;
                result["swap_time_ms".to_string()] = ((swap_ms as f64) * 10f64.powi(1)).round() / 10f64.powi(1);
                logger.info(format!("Strategy '{}' auto-switched to {} (swap={:.0}ms)", strategy_name, result["recommended_model".to_string()], swap_ms));
            }
        }
        // except Exception as e:
    }
    Ok(result)
}

/// Create or update a custom routing strategy.
pub async fn create_custom_strategy(body: HashMap<String, Box<dyn std::any::Any>>) -> Result<()> {
    // Create or update a custom routing strategy.
    let mut name = body.get(&"name".to_string()).cloned().unwrap_or("".to_string()).trim().to_string();
    if !name {
        return Err(anyhow::anyhow!("HTTPException(400, detail=\"'name' is required\")"));
    }
    if BUILTIN_STRATEGIES.contains(&name) {
        return Err(anyhow::anyhow!("HTTPException(400, detail=f\"Cannot overwrite built-in strategy '{name}'. Built-in: {list(BUILTIN_STRATEGIES.keys())}\")"));
    }
    let mut desc = body.get(&"description".to_string()).cloned().unwrap_or("Custom strategy".to_string());
    let mut steps = body.get(&"steps".to_string()).cloned().unwrap_or(vec![]);
    if (!steps || !/* /* isinstance(steps, list) */ */ true) {
        return Err(anyhow::anyhow!("HTTPException(400, detail=\"'steps' must be a non-empty list\")"));
    }
    let mut valid_methods = HashSet::from(["domain_expert".to_string(), "difficulty_expert".to_string(), "overall_best".to_string(), "fastest".to_string(), "current".to_string()]);
    for (i, step) in steps.iter().enumerate().iter() {
        let mut m = step.get(&"method".to_string()).cloned().unwrap_or("".to_string());
        if !valid_methods.contains(&m) {
            return Err(anyhow::anyhow!("HTTPException(400, detail=f\"Step {i + 1}: unknown method '{m}'. Valid: {sorted(valid_methods)}\")"));
        }
    }
    custom_strategies[name] = HashMap::from([("description".to_string(), desc), ("steps".to_string(), steps)]);
    logger.info(format!("Custom strategy created: '{}' ({} steps)", name, steps.len()));
    Ok(HashMap::from([("status".to_string(), "ok".to_string()), ("name".to_string(), name), ("steps".to_string(), steps.len()), ("total_strategies".to_string(), (BUILTIN_STRATEGIES.len() + custom_strategies.len()))]))
}

/// Delete a custom routing strategy.
pub async fn delete_custom_strategy(strategy_name: String) -> Result<()> {
    // Delete a custom routing strategy.
    if !custom_strategies.contains(&strategy_name) {
        return Err(anyhow::anyhow!("HTTPException(404, detail=f\"Custom strategy '{strategy_name}' not found\")"));
    }
    drop(custom_strategies[strategy_name]);
    Ok(HashMap::from([("status".to_string(), "ok".to_string()), ("deleted".to_string(), strategy_name)]))
}

/// Route model selection factoring in RAG context.
pub async fn route_for_rag(body: HashMap<String, Box<dyn std::any::Any>>) -> Result<()> {
    // Route model selection factoring in RAG context.
    let mut state = get_state();
    let mut swap_tracker = get_swap_tracker();
    let mut query = (body.get(&"query".to_string()).cloned() || "".to_string()).trim().to_string();
    if !query {
        return Err(anyhow::anyhow!("HTTPException(400, detail=\"'query' is required\")"));
    }
    let mut data = load_model_profiles();
    if !data {
        return Err(anyhow::anyhow!("HTTPException(404, detail='No model profiles found')"));
    }
    let mut context_tokens = body.get(&"context_tokens".to_string()).cloned().unwrap_or(0);
    let mut chunk_count = body.get(&"chunk_count".to_string()).cloned().unwrap_or(0);
    let mut avg_chunk_tokens = body.get(&"avg_chunk_tokens".to_string()).cloned().unwrap_or(256);
    let mut rag_stats = HashMap::new();
    // try:
    {
        // TODO: from rag_integration import _rag_integration
        if (_rag_integration && _rag_integration.initialized) {
            let mut rag_stats = _rag_integration.get_stats();
        }
    }
    // except Exception as exc:
    let mut ctx_info = estimate_rag_context(rag_stats, chunk_count, avg_chunk_tokens);
    if context_tokens <= 0 {
        let mut context_tokens = ctx_info["estimated_tokens".to_string()];
    }
    let mut weights = body.get(&"weights".to_string()).cloned().unwrap_or(None);
    let mut ranking = rank_models_for_rag(data, context_tokens, weights);
    let mut current_model = if state { state::model_id } else { None };
    let mut needs_switch = (ranking["recommended".to_string()].is_some() && ranking["recommended".to_string()] != current_model);
    let mut result = HashMap::from([("query".to_string(), query), ("recommended_model".to_string(), ranking["recommended".to_string()]), ("current_model".to_string(), current_model), ("needs_switch".to_string(), needs_switch), ("rag_context".to_string(), ctx_info), ("context_tokens".to_string(), context_tokens), ("rankings".to_string(), ranking["rankings".to_string()]), ("excluded".to_string(), ranking["excluded".to_string()]), ("weights_used".to_string(), ranking["weights_used".to_string()])]);
    if (needs_switch && swap_tracker) {
        let mut est = swap_tracker.estimate_swap_cost_ms();
        if est {
            result["swap_cost_estimate_ms".to_string()] = est;
        }
    }
    if (body.get(&"auto_switch".to_string()).cloned() && needs_switch && ranking["recommended".to_string()]) {
        let mut recommended = ranking["recommended".to_string()];
        let mut routing_table = data.get(&"routing_table".to_string()).cloned().unwrap_or(HashMap::new());
        let mut model_path = None;
        for (_domain, path) in routing_table.iter().iter() {
            if path.contains(&recommended) {
                let mut model_path = path;
                break;
            }
        }
        if model_path {
            // TODO: from server::routers.models import switch_model as _switch
            let mut t0 = time::perf_counter();
            _switch(HashMap::from([("model_path".to_string(), model_path)])).await;
            let mut elapsed = ((time::perf_counter() - t0) * 1000);
            result["switched".to_string()] = true;
            result["switch_time_ms".to_string()] = ((elapsed as f64) * 10f64.powi(1)).round() / 10f64.powi(1);
            if swap_tracker {
                swap_tracker.record((current_model || "unknown".to_string()), recommended, elapsed, /* trigger= */ "rag_route".to_string());
            }
        }
    }
    Ok(result)
}

/// Return current RAG context status for routing decisions.
pub async fn rag_routing_status() -> Result<()> {
    // Return current RAG context status for routing decisions.
    let mut rag_stats = HashMap::new();
    // try:
    {
        // TODO: from rag_integration import _rag_integration
        if (_rag_integration && _rag_integration.initialized) {
            let mut rag_stats = _rag_integration.get_stats();
        }
    }
    // except Exception as exc:
    let mut ctx_info = estimate_rag_context(rag_stats);
    Ok(HashMap::from([("rag_initialized".to_string(), (rag_stats.get(&"initialized".to_string()).cloned().unwrap_or(false) != 0)), ("rag_active".to_string(), ctx_info["active".to_string()]), ("documents".to_string(), ctx_info["documents".to_string()]), ("collections".to_string(), ctx_info["collections".to_string()]), ("estimated_context_tokens".to_string(), ctx_info["estimated_tokens".to_string()]), ("default_weights".to_string(), DEFAULT_RAG_WEIGHTS)]))
}

/// Preview RAG-aware model rankings without routing.
pub async fn rag_model_rankings(context_tokens: i64, quality_weight: f64, context_speed_weight: f64, generation_speed_weight: f64) -> Result<()> {
    // Preview RAG-aware model rankings without routing.
    let mut data = load_model_profiles();
    if !data {
        return Err(anyhow::anyhow!("HTTPException(404, detail='No model profiles found')"));
    }
    let mut weights = HashMap::from([("quality".to_string(), quality_weight), ("context_speed".to_string(), context_speed_weight), ("generation_speed".to_string(), generation_speed_weight)]);
    let mut ranking = rank_models_for_rag(data, context_tokens, weights);
    Ok(ranking)
}
