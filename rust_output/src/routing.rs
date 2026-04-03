/// Domain/difficulty classification, compound strategies, RAG-aware routing.
/// 
/// Extracted from api_server::py.

use anyhow::{Result, Context};
use crate::helpers::{get_state};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const _PROJECT_ROOT: &str = "Path(file!()).resolve().parent.parent";

pub static _MODEL_PROFILES: std::sync::LazyLock<Option<HashMap<String, Box<dyn std::any::Any>>>> = std::sync::LazyLock::new(|| None);

pub const _MODEL_PROFILES_MTIME: f64 = 0.0;

pub static DOMAIN_KEYWORDS: std::sync::LazyLock<HashMap<String, Vec<String>>> = std::sync::LazyLock::new(|| HashMap::new());

pub static DIFFICULTY_HARD_SIGNALS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static DIFFICULTY_EASY_SIGNALS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub static BUILTIN_STRATEGIES: std::sync::LazyLock<HashMap<String, HashMap<String, Box<dyn std::any::Any>>>> = std::sync::LazyLock::new(|| HashMap::new());

pub static CUSTOM_STRATEGIES: std::sync::LazyLock<HashMap<String, HashMap<String, Box<dyn std::any::Any>>>> = std::sync::LazyLock::new(|| HashMap::new());

pub static DEFAULT_RAG_WEIGHTS: std::sync::LazyLock<HashMap<String, f64>> = std::sync::LazyLock::new(|| HashMap::new());

/// Load model_profiles.json, auto-reload if file changed.
pub fn load_model_profiles() -> Result<Option<HashMap<String, Box<dyn std::any::Any>>>> {
    // Load model_profiles.json, auto-reload if file changed.
    // global/nonlocal _model_profiles, _model_profiles_mtime
    let mut profiles_path = (_PROJECT_ROOT / "model_profiles.json".to_string());
    if !profiles_path.exists() {
        _model_profiles
    }
    // try:
    {
        let mut mtime = profiles_path.stat().st_mtime;
        if mtime != _model_profiles_mtime {
            let mut f = File::open(profiles_path)?;
            {
                let mut _model_profiles = json::load(f);
            }
            let mut _model_profiles_mtime = mtime;
            logger.info("Loaded model profiles (%d models, %d domains)".to_string(), _model_profiles.get(&"profiles".to_string()).cloned().unwrap_or(HashMap::new()).len(), _model_profiles.get(&"domain_experts".to_string()).cloned().unwrap_or(HashMap::new()).len());
        }
    }
    // except Exception as e:
    Ok(_model_profiles)
}

/// Classify a query into its best-matching domain category.
pub fn classify_query_domain(query: String) -> (Option<String>, f64) {
    // Classify a query into its best-matching domain category.
    let mut query_lower = query.to_lowercase();
    let mut scores = HashMap::new();
    for (domain, keywords) in DOMAIN_KEYWORDS.iter().iter() {
        let mut score = keywords.iter().filter(|kw| query_lower.contains(&kw)).map(|kw| 1).collect::<Vec<_>>().iter().sum::<i64>();
        if score > 0 {
            scores[domain] = score;
        }
    }
    if !scores {
        (None, 0.0_f64)
    }
    let mut best_domain = scores.max(/* key= */ scores.get);
    let mut max_possible = DOMAIN_KEYWORDS[&best_domain].len();
    let mut confidence = 1.0_f64.min((scores[&best_domain] / (max_possible * 0.3_f64).max(1)));
    (best_domain, ((confidence as f64) * 10f64.powi(2)).round() / 10f64.powi(2))
}

/// Estimate query difficulty: 'easy', 'medium', or 'hard'.
pub fn classify_query_difficulty(query: String) -> String {
    // Estimate query difficulty: 'easy', 'medium', or 'hard'.
    let mut q = query.trim().to_string();
    let mut q_lower = q.to_lowercase();
    let mut length = q.len();
    let mut hard_hits = DIFFICULTY_HARD_SIGNALS.iter().filter(|s| q_lower.contains(&s)).map(|s| 1).collect::<Vec<_>>().iter().sum::<i64>();
    let mut easy_hits = DIFFICULTY_EASY_SIGNALS.iter().filter(|s| q_lower.contains(&s)).map(|s| 1).collect::<Vec<_>>().iter().sum::<i64>();
    let mut has_code = (q.contains(&"```".to_string()) || q.iter().filter(|v| **v == "\n".to_string()).count() > 10);
    let mut sentences = q.split(".".to_string()).map(|s| s.to_string()).collect::<Vec<String>>().iter().filter(|s| s.trim().to_string().len() > 10).map(|s| s).collect::<Vec<_>>().len();
    if (hard_hits >= 2 || (length > 300 && hard_hits >= 1)) {
        "hard".to_string()
    }
    if (has_code && length > 200) {
        "hard".to_string()
    }
    if (sentences >= 4 && hard_hits >= 1) {
        "hard".to_string()
    }
    if (easy_hits >= 1 && length < 80 && hard_hits == 0) {
        "easy".to_string()
    }
    if (length < 40 && hard_hits == 0) {
        "easy".to_string()
    }
    "medium".to_string()
}

/// Resolve a single strategy step to a model recommendation.
pub fn resolve_strategy_step(method: String, query: String, data: HashMap<String, Box<dyn std::any::Any>>, domain: Option<String>, domain_confidence: f64, difficulty: String) -> Option<HashMap<String, Box<dyn std::any::Any>>> {
    // Resolve a single strategy step to a model recommendation.
    let mut state = get_state();
    let mut profiles = data.get(&"profiles".to_string()).cloned().unwrap_or(HashMap::new());
    let mut experts = data.get(&"domain_experts".to_string()).cloned().unwrap_or(HashMap::new());
    let mut diff_experts = data.get(&"difficulty_experts".to_string()).cloned().unwrap_or(HashMap::new());
    let mut routing_table = data.get(&"routing_table".to_string()).cloned().unwrap_or(HashMap::new());
    let mut diff_routing = data.get(&"difficulty_routing_table".to_string()).cloned().unwrap_or(HashMap::new());
    let mut ranking = data.get(&"ranking".to_string()).cloned().unwrap_or(vec![]);
    if method == "domain_expert".to_string() {
        if (domain && experts.contains(&domain)) {
            let mut expert = experts[&domain];
            HashMap::from([("model".to_string(), expert["model".to_string()]), ("path".to_string(), routing_table.get(&domain).cloned()), ("reason".to_string(), format!("domain expert for {}", domain)), ("score".to_string(), expert.get(&"avg_score".to_string()).cloned().unwrap_or(0))])
        }
        None
    }
    if method == "difficulty_expert".to_string() {
        if diff_experts.contains(&difficulty) {
            let mut info = diff_experts[&difficulty];
            let mut model = if difficulty == "easy".to_string() { info.get(&"speed_pick".to_string()).cloned().unwrap_or(info["model".to_string()]) } else { info["model".to_string()] };
            HashMap::from([("model".to_string(), model), ("path".to_string(), diff_routing.get(&difficulty).cloned()), ("reason".to_string(), format!("difficulty expert for {}", difficulty)), ("score".to_string(), info.get(&"avg_score".to_string()).cloned().unwrap_or(0))])
        }
        None
    }
    if method == "overall_best".to_string() {
        if ranking {
            let mut best = ranking[0];
            let mut model_name = best["model".to_string()];
            let mut path = None;
            for p in routing_table.values().iter() {
                if p.to_string().contains(&model_name) {
                    let mut path = p;
                    break;
                }
            }
            HashMap::from([("model".to_string(), model_name), ("path".to_string(), path), ("reason".to_string(), "overall best ranked model".to_string()), ("score".to_string(), best.get(&"avg_overall".to_string()).cloned().unwrap_or(0))])
        }
        None
    }
    if method == "fastest".to_string() {
        let mut fastest_model = None;
        let mut fastest_tps = 0.0_f64;
        for (name, profile) in profiles.iter().iter() {
            let mut tps = profile.get(&"avg_tokens_per_sec".to_string()).cloned().unwrap_or(0);
            if tps > fastest_tps {
                let mut fastest_tps = tps;
                let mut fastest_model = name;
            }
        }
        if fastest_model {
            let mut path = None;
            for p in routing_table.values().iter() {
                if p.to_string().contains(&fastest_model) {
                    let mut path = p;
                    break;
                }
            }
            HashMap::from([("model".to_string(), fastest_model), ("path".to_string(), path), ("reason".to_string(), format!("fastest model ({:.1} tok/s)", fastest_tps)), ("score".to_string(), profiles[&fastest_model].get(&"avg_overall".to_string()).cloned().unwrap_or(0))])
        }
        None
    }
    if method == "current".to_string() {
        let mut current = if state { state::model_id } else { None };
        if current {
            let mut score = profiles.get(&current).cloned().unwrap_or(HashMap::new()).get(&"avg_overall".to_string()).cloned().unwrap_or(0);
            HashMap::from([("model".to_string(), current), ("path".to_string(), None), ("reason".to_string(), "keep current model (zero swap cost)".to_string()), ("score".to_string(), score)])
        }
        None
    }
    None
}

/// Walk a strategy's fallback chain and return the first viable pick.
pub fn evaluate_strategy(strategy_name: String, steps: Vec<HashMap<String, Box<dyn std::any::Any>>>, query: String, data: HashMap<String, Box<dyn std::any::Any>>) -> HashMap<String, Box<dyn std::any::Any>> {
    // Walk a strategy's fallback chain and return the first viable pick.
    let mut state = get_state();
    let (mut domain, mut domain_confidence) = classify_query_domain(query);
    let mut difficulty = classify_query_difficulty(query);
    let mut chain_log = vec![];
    let mut selected = None;
    for (i, step) in steps.iter().enumerate().iter() {
        let mut method = step.get(&"method".to_string()).cloned().unwrap_or("unknown".to_string());
        let mut min_conf = step.get(&"min_confidence".to_string()).cloned().unwrap_or(0.0_f64);
        let mut result = resolve_strategy_step(method, query, data, domain, domain_confidence, difficulty);
        let mut entry = HashMap::from([("step".to_string(), (i + 1)), ("method".to_string(), method), ("min_confidence".to_string(), min_conf), ("result".to_string(), None), ("accepted".to_string(), false)]);
        if result {
            entry["result".to_string()] = HashMap::from([("model".to_string(), result["model".to_string()]), ("score".to_string(), result["score".to_string()]), ("reason".to_string(), result["reason".to_string()])]);
            if method == "domain_expert".to_string() {
                if domain_confidence >= min_conf {
                    entry["accepted".to_string()] = true;
                    if !selected {
                        let mut selected = result;
                    }
                } else {
                    entry["skipped_reason".to_string()] = format!("confidence {:.2} < threshold {}", domain_confidence, min_conf);
                }
            } else {
                entry["accepted".to_string()] = true;
                if !selected {
                    let mut selected = result;
                }
            }
        }
        chain_log.push(entry);
    }
    if !selected {
        let mut ranking = data.get(&"ranking".to_string()).cloned().unwrap_or(vec![]);
        if ranking {
            let mut selected = HashMap::from([("model".to_string(), ranking[0]["model".to_string()]), ("path".to_string(), None), ("reason".to_string(), "fallback: no strategy step matched".to_string()), ("score".to_string(), ranking[0].get(&"avg_overall".to_string()).cloned().unwrap_or(0))]);
        }
    }
    let mut current_model = if state { state::model_id } else { None };
    HashMap::from([("strategy".to_string(), strategy_name), ("recommended_model".to_string(), if selected { selected["model".to_string()] } else { current_model }), ("reason".to_string(), if selected { selected["reason".to_string()] } else { "no recommendation".to_string() }), ("model_score".to_string(), if selected { selected["score".to_string()] } else { 0 }), ("model_path".to_string(), if selected { selected.get(&"path".to_string()).cloned() } else { None }), ("domain".to_string(), domain), ("domain_confidence".to_string(), domain_confidence), ("difficulty".to_string(), difficulty), ("current_model".to_string(), current_model), ("needs_switch".to_string(), if selected { selected["model".to_string()] != current_model } else { false }), ("chain".to_string(), chain_log), ("steps_evaluated".to_string(), chain_log.len()), ("winning_step".to_string(), next(chain_log.iter().filter(|e| (e["accepted".to_string()] && e.get(&"result".to_string()).cloned().unwrap_or(HashMap::new()).get(&"model".to_string()).cloned() == if selected { selected["model".to_string()] } else { None })).map(|e| e["step".to_string()]).collect::<Vec<_>>(), None))])
}

/// Estimate RAG context characteristics.
pub fn estimate_rag_context(rag_stats: HashMap<String, Box<dyn std::any::Any>>, chunk_count: i64, avg_chunk_tokens: i64) -> HashMap<String, Box<dyn std::any::Any>> {
    // Estimate RAG context characteristics.
    let mut docs = rag_stats.get(&"documents_uploaded".to_string()).cloned().unwrap_or(0);
    let mut collections = rag_stats.get(&"collections".to_string()).cloned().unwrap_or(HashMap::new());
    let mut total_size = rag_stats.get(&"total_collection_size".to_string()).cloned().unwrap_or(0);
    let mut n_collections = if /* /* isinstance(collections, dict) */ */ true { collections::len() } else { 0 };
    if chunk_count > 0 {
        let mut est_tokens = (chunk_count * avg_chunk_tokens);
    } else if total_size > 0 {
        let mut est_tokens = (total_size / 4);
    } else {
        let mut est_tokens = 0;
    }
    HashMap::from([("active".to_string(), (docs > 0 || est_tokens > 0)), ("estimated_tokens".to_string(), est_tokens), ("documents".to_string(), docs), ("collections".to_string(), n_collections)])
}

/// Score a single model for RAG-augmented routing.
pub fn score_model_for_rag(model_name: String, profile: HashMap<String, Box<dyn std::any::Any>>, context_tokens: i64, weights: Option<HashMap<String, f64>>) -> HashMap<String, Box<dyn std::any::Any>> {
    // Score a single model for RAG-augmented routing.
    let mut w = (weights || DEFAULT_RAG_WEIGHTS);
    let mut n_ctx = profile.get(&"n_ctx".to_string()).cloned().unwrap_or(0);
    if (n_ctx > 0 && context_tokens > n_ctx) {
        HashMap::from([("model".to_string(), model_name), ("rag_score".to_string(), 0.0_f64), ("fits_context".to_string(), false), ("disqualified_reason".to_string(), format!("context {} tokens > model n_ctx {}", context_tokens, n_ctx)), ("breakdown".to_string(), HashMap::new())])
    }
    let mut quality_raw = profile.get(&"avg_overall".to_string()).cloned().unwrap_or(50.0_f64);
    let mut quality_norm = (quality_raw / 100.0_f64).min(1.0_f64);
    let mut perf = profile.get(&"perf_stats".to_string()).cloned().unwrap_or(HashMap::new());
    let mut pe_data = perf.get(&"prompt_eval_tps".to_string()).cloned().unwrap_or(HashMap::new());
    let mut pe_tps = if /* /* isinstance(pe_data, dict) */ */ true { pe_data.get(&"mean".to_string()).cloned().unwrap_or(0.0_f64) } else { 0.0_f64 };
    let mut ctx_speed_norm = (pe_tps / 500.0_f64).min(1.0_f64);
    let mut gen_tps = profile.get(&"avg_tokens_per_sec".to_string()).cloned().unwrap_or(0.0_f64);
    let mut gen_speed_norm = (gen_tps / 100.0_f64).min(1.0_f64);
    let mut wq = w.get(&"quality".to_string()).cloned().unwrap_or(0.5_f64);
    let mut wc = w.get(&"context_speed".to_string()).cloned().unwrap_or(0.3_f64);
    let mut wg = w.get(&"generation_speed".to_string()).cloned().unwrap_or(0.2_f64);
    let mut rag_score = (((((wq * quality_norm) + (wc * ctx_speed_norm)) + (wg * gen_speed_norm)) as f64) * 10f64.powi(4)).round() / 10f64.powi(4);
    HashMap::from([("model".to_string(), model_name), ("rag_score".to_string(), rag_score), ("fits_context".to_string(), true), ("disqualified_reason".to_string(), None), ("breakdown".to_string(), HashMap::from([("quality".to_string(), ((quality_norm as f64) * 10f64.powi(4)).round() / 10f64.powi(4)), ("quality_weight".to_string(), wq), ("context_speed".to_string(), ((ctx_speed_norm as f64) * 10f64.powi(4)).round() / 10f64.powi(4)), ("context_speed_weight".to_string(), wc), ("generation_speed".to_string(), ((gen_speed_norm as f64) * 10f64.powi(4)).round() / 10f64.powi(4)), ("generation_speed_weight".to_string(), wg), ("prompt_eval_tps".to_string(), pe_tps), ("avg_tokens_per_sec".to_string(), gen_tps)]))])
}

/// Rank all profiled models for a RAG-augmented query.
pub fn rank_models_for_rag(profiles_data: HashMap<String, Box<dyn std::any::Any>>, context_tokens: i64, weights: Option<HashMap<String, f64>>) -> HashMap<String, Box<dyn std::any::Any>> {
    // Rank all profiled models for a RAG-augmented query.
    let mut profiles = profiles_data.get(&"profiles".to_string()).cloned().unwrap_or(HashMap::new());
    let mut scored = vec![];
    let mut excluded = vec![];
    for (model_name, profile) in profiles.iter().iter() {
        let mut result = score_model_for_rag(model_name, profile, context_tokens, weights);
        if result["fits_context".to_string()] {
            scored.push(result);
        } else {
            excluded.push(result);
        }
    }
    scored.sort(/* key= */ |x| x["rag_score".to_string()], /* reverse= */ true);
    let mut recommended = if scored { scored[0]["model".to_string()] } else { None };
    HashMap::from([("recommended".to_string(), recommended), ("rankings".to_string(), scored), ("excluded".to_string(), excluded), ("context_tokens".to_string(), context_tokens), ("weights_used".to_string(), (weights || DEFAULT_RAG_WEIGHTS))])
}
