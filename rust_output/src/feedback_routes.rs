/// Feedback & profiling history router.
/// 
/// Endpoints:
/// POST /v1/feedback
/// GET  /v1/feedback/stats
/// GET  /v1/feedback/history
/// GET  /v1/feedback/model/{model_name}
/// GET  /v1/feedback/adjustments
/// GET  /v1/models/history
/// GET  /v1/models/history/compare
/// GET  /v1/models/history/trend

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub const _PROJECT_ROOT: &str = "Path(file!()).resolve().parent.parent.parent";

pub const _PROFILING_RUNS_DIR: &str = "_PROJECT_ROOT / 'profiling_runs";

pub static ROUTER: std::sync::LazyLock<APIRouter> = std::sync::LazyLock::new(|| Default::default());

/// Get the global FeedbackCollector.
pub fn _get_feedback_collector() -> () {
    // Get the global FeedbackCollector.
    // TODO: import api_server
    api_server::_feedback_collector
}

/// Submit quality feedback for a model response.
pub async fn submit_feedback(body: HashMap<String, Box<dyn std::any::Any>>) -> Result<()> {
    // Submit quality feedback for a model response.
    // TODO: from server::feedback import FeedbackCollector
    let mut collector = _get_feedback_collector();
    let mut model = (body.get(&"model".to_string()).cloned() || "".to_string()).trim().to_string();
    if !model {
        return Err(anyhow::anyhow!("HTTPException(400, detail=\"'model' is required\")"));
    }
    let mut thumbs = body.get(&"thumbs".to_string()).cloned();
    if (thumbs.is_some() && !("up".to_string(), "down".to_string()).contains(&thumbs)) {
        return Err(anyhow::anyhow!("HTTPException(400, detail=\"'thumbs' must be 'up' or 'down'\")"));
    }
    let mut rating = body.get(&"rating".to_string()).cloned();
    if rating.is_some() {
        if (!/* /* isinstance(rating, int) */ */ true || !(1 <= rating) && (rating <= 5)) {
            return Err(anyhow::anyhow!("HTTPException(400, detail=\"'rating' must be integer 1-5\")"));
        }
    }
    let mut tags = body.get(&"tags".to_string()).cloned().unwrap_or(vec![]);
    if tags {
        let mut invalid = tags.iter().filter(|t| !FeedbackCollector.VALID_TAGS.contains(&t)).map(|t| t).collect::<Vec<_>>();
        if invalid {
            return Err(anyhow::anyhow!("HTTPException(400, detail=f'Invalid tags: {invali}. Valid: {sorted(FeedbackCollector.VALID_TAGS)}')"));
        }
    }
    let mut entry = collector.submit(/* model= */ model, /* thumbs= */ thumbs, /* rating= */ rating, /* tags= */ tags, /* response_id= */ body.get(&"response_id".to_string()).cloned(), /* comment= */ body.get(&"comment".to_string()).cloned());
    Ok(HashMap::from([("status".to_string(), "ok".to_string()), ("feedback".to_string(), entry)]))
}

/// Global feedback statistics.
pub async fn feedback_stats() -> () {
    // Global feedback statistics.
    _get_feedback_collector().stats()
}

/// Recent feedback entries (newest first).
pub async fn feedback_history(last_n: i64, model: Option<String>) -> () {
    // Recent feedback entries (newest first).
    let mut entries = _get_feedback_collector().history(/* last_n= */ last_n, /* model= */ model);
    HashMap::from([("count".to_string(), entries.len()), ("entries".to_string(), entries)])
}

/// Aggregated feedback summary for a specific model.
pub async fn feedback_model_summary(model_name: String) -> Result<()> {
    // Aggregated feedback summary for a specific model.
    let mut summary = _get_feedback_collector().model_summary(model_name);
    if !summary {
        return Err(anyhow::anyhow!("HTTPException(404, detail=f\"No feedback found for model '{model_name}'\")"));
    }
    Ok(summary)
}

/// Per-model routing score adjustments derived from user feedback.
pub async fn feedback_routing_adjustments() -> () {
    // Per-model routing score adjustments derived from user feedback.
    let mut collector = _get_feedback_collector();
    let mut adjustments = collector.routing_adjustments();
    let mut summaries = collector.all_summaries();
    HashMap::from([("adjustments".to_string(), adjustments), ("model_summaries".to_string(), summaries), ("min_feedback_threshold".to_string(), 3), ("adjustment_range".to_string(), "-10 to +10 points".to_string())])
}

/// List all archived profiling runs, newest first.
pub async fn profiling_history() -> Result<()> {
    // List all archived profiling runs, newest first.
    if !_PROFILING_RUNS_DIR.exists() {
        HashMap::from([("runs".to_string(), vec![]), ("count".to_string(), 0)])
    }
    let mut runs = vec![];
    for fp in { let mut v = _PROFILING_RUNS_DIR.glob("profile_*.json".to_string()).clone(); v.sort(); v }.iter() {
        // try:
        {
            let mut f = File::open(fp)?;
            {
                let mut data = json::load(f);
            }
            runs.push(HashMap::from([("run_id".to_string(), data.get(&"run_id".to_string()).cloned().unwrap_or(fp.file_stem().unwrap_or_default().to_str().unwrap_or("").replace(&*"profile_".to_string(), &*"".to_string()))), ("timestamp".to_string(), data.get(&"timestamp".to_string()).cloned().unwrap_or("".to_string())), ("model_count".to_string(), data.get(&"profiles".to_string()).cloned().unwrap_or(HashMap::new()).len()), ("categories".to_string(), data.get(&"meta".to_string()).cloned().unwrap_or(HashMap::new()).get(&"categories_tested".to_string()).cloned().unwrap_or(vec![])), ("elapsed".to_string(), data.get(&"meta".to_string()).cloned().unwrap_or(HashMap::new()).get(&"elapsed_human".to_string()).cloned().unwrap_or("".to_string())), ("profiler_version".to_string(), data.get(&"profiler_version".to_string()).cloned().unwrap_or("unknown".to_string()))]));
        }
        // except (json::JSONDecodeError, OSError) as _e:
    }
    Ok(HashMap::from([("runs".to_string(), runs), ("count".to_string(), runs.len())]))
}

/// Load an archived profiling run by run_id.
pub fn _load_archived_run(run_id: String) -> Result<Option<HashMap<String, Box<dyn std::any::Any>>>> {
    // Load an archived profiling run by run_id.
    if !_PROFILING_RUNS_DIR.exists() {
        None
    }
    let mut candidate = (_PROFILING_RUNS_DIR / format!("profile_{}.json", run_id));
    if candidate.exists() {
        // try:
        {
            let mut f = File::open(candidate)?;
            {
                json::load(f)
            }
        }
        // except (json::JSONDecodeError, OSError) as _e:
    }
    for fp in _PROFILING_RUNS_DIR.glob("profile_*.json".to_string()).iter() {
        // try:
        {
            let mut f = File::open(fp)?;
            {
                let mut data = json::load(f);
            }
            if data.get(&"run_id".to_string()).cloned() == run_id {
                data
            }
        }
        // except (json::JSONDecodeError, OSError) as _e:
    }
    Ok(None)
}

/// Compare two archived profiling runs.
pub async fn compare_profiling_runs(run1: String, run2: String) -> Result<()> {
    // Compare two archived profiling runs.
    let mut r1_data = _load_archived_run(run1);
    if !r1_data {
        return Err(anyhow::anyhow!("HTTPException(404, detail=f\"Run '{run1}' not found in profiling_runs/\")"));
    }
    let mut r2_data = _load_archived_run(run2);
    if !r2_data {
        return Err(anyhow::anyhow!("HTTPException(404, detail=f\"Run '{run2}' not found in profiling_runs/\")"));
    }
    let mut r1_profiles = r1_data.get(&"profiles".to_string()).cloned().unwrap_or(HashMap::new());
    let mut r2_profiles = r2_data.get(&"profiles".to_string()).cloned().unwrap_or(HashMap::new());
    let mut r1_models = r1_profiles.keys().into_iter().collect::<HashSet<_>>();
    let mut r2_models = r2_profiles.keys().into_iter().collect::<HashSet<_>>();
    let mut common = { let mut v = (r1_models & r2_models).clone(); v.sort(); v };
    let mut r1_rank = r1_data.get(&"ranking".to_string()).cloned().unwrap_or(vec![]).iter().map(|r| (r["model".to_string()], r["rank".to_string()])).collect::<HashMap<_, _>>();
    let mut r2_rank = r2_data.get(&"ranking".to_string()).cloned().unwrap_or(vec![]).iter().map(|r| (r["model".to_string()], r["rank".to_string()])).collect::<HashMap<_, _>>();
    let mut ranking_changes = common.iter().filter(|m| r1_rank.get(&m).cloned() != r2_rank.get(&m).cloned()).map(|m| HashMap::from([("model".to_string(), m), ("old_rank".to_string(), r1_rank.get(&m).cloned().unwrap_or(0)), ("new_rank".to_string(), r2_rank.get(&m).cloned().unwrap_or(0)), ("direction".to_string(), if r2_rank.get(&m).cloned().unwrap_or(0) < r1_rank.get(&m).cloned().unwrap_or(0) { "improved".to_string() } else { "declined".to_string() })])).collect::<Vec<_>>();
    let mut r1_exp = r1_data.get(&"domain_experts".to_string()).cloned().unwrap_or(HashMap::new());
    let mut r2_exp = r2_data.get(&"domain_experts".to_string()).cloned().unwrap_or(HashMap::new());
    let mut all_domains = { let mut v = (r1_exp.keys().into_iter().collect::<Vec<_>>() + r2_exp.keys().into_iter().collect::<Vec<_>>()).into_iter().collect::<HashSet<_>>().clone(); v.sort(); v };
    let mut domain_expert_changes = all_domains.iter().filter(|d| r1_exp.get(&d).cloned().unwrap_or(HashMap::new()).get(&"model".to_string()).cloned() != r2_exp.get(&d).cloned().unwrap_or(HashMap::new()).get(&"model".to_string()).cloned()).map(|d| HashMap::from([("domain".to_string(), d), ("old_expert".to_string(), r1_exp.get(&d).cloned().unwrap_or(HashMap::new()).get(&"model".to_string()).cloned().unwrap_or("".to_string())), ("new_expert".to_string(), r2_exp.get(&d).cloned().unwrap_or(HashMap::new()).get(&"model".to_string()).cloned().unwrap_or("".to_string())), ("old_score".to_string(), r1_exp.get(&d).cloned().unwrap_or(HashMap::new()).get(&"avg_score".to_string()).cloned().unwrap_or(0)), ("new_score".to_string(), r2_exp.get(&d).cloned().unwrap_or(HashMap::new()).get(&"avg_score".to_string()).cloned().unwrap_or(0))])).collect::<Vec<_>>();
    let mut perf_keys = vec!["tokens_per_sec".to_string(), "first_token_time".to_string(), "total_time".to_string(), "chars_per_sec".to_string(), "prompt_eval_tps".to_string(), "load_speed_mb_s".to_string()];
    let mut metric_deltas = HashMap::new();
    for m in common.iter() {
        let mut p1 = r1_profiles[&m].get(&"perf_stats".to_string()).cloned().unwrap_or(HashMap::new());
        let mut p2 = r2_profiles[&m].get(&"perf_stats".to_string()).cloned().unwrap_or(HashMap::new());
        let mut deltas = HashMap::new();
        for pk in perf_keys.iter() {
            let mut old_mean = p1.get(&pk).cloned().unwrap_or(HashMap::new()).get(&"mean".to_string()).cloned().unwrap_or(0);
            let mut new_mean = p2.get(&pk).cloned().unwrap_or(HashMap::new()).get(&"mean".to_string()).cloned().unwrap_or(0);
            if (old_mean || new_mean) {
                deltas[pk] = HashMap::from([("old".to_string(), ((old_mean as f64) * 10f64.powi(3)).round() / 10f64.powi(3)), ("new".to_string(), ((new_mean as f64) * 10f64.powi(3)).round() / 10f64.powi(3)), ("delta".to_string(), (((new_mean - old_mean) as f64) * 10f64.powi(3)).round() / 10f64.powi(3)), ("pct_change".to_string(), if old_mean { (((((new_mean - old_mean) / old_mean) * 100) as f64) * 10f64.powi(1)).round() / 10f64.powi(1) } else { None })]);
            }
        }
        let mut old_avg = r1_profiles[&m].get(&"avg_overall".to_string()).cloned().unwrap_or(0);
        let mut new_avg = r2_profiles[&m].get(&"avg_overall".to_string()).cloned().unwrap_or(0);
        deltas["avg_overall".to_string()] = HashMap::from([("old".to_string(), ((old_avg as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("new".to_string(), ((new_avg as f64) * 10f64.powi(1)).round() / 10f64.powi(1)), ("delta".to_string(), (((new_avg - old_avg) as f64) * 10f64.powi(1)).round() / 10f64.powi(1))]);
        metric_deltas[m] = deltas;
    }
    let mut r1_ri = r1_data.get(&"routing_improvement".to_string()).cloned().unwrap_or(HashMap::new());
    let mut r2_ri = r2_data.get(&"routing_improvement".to_string()).cloned().unwrap_or(HashMap::new());
    Ok(HashMap::from([("run1".to_string(), HashMap::from([("run_id".to_string(), run1), ("timestamp".to_string(), r1_data.get(&"timestamp".to_string()).cloned().unwrap_or("".to_string()))])), ("run2".to_string(), HashMap::from([("run_id".to_string(), run2), ("timestamp".to_string(), r2_data.get(&"timestamp".to_string()).cloned().unwrap_or("".to_string()))])), ("new_models".to_string(), { let mut v = (r2_models - r1_models).clone(); v.sort(); v }), ("removed_models".to_string(), { let mut v = (r1_models - r2_models).clone(); v.sort(); v }), ("ranking_changes".to_string(), ranking_changes), ("domain_expert_changes".to_string(), domain_expert_changes), ("metric_deltas".to_string(), metric_deltas), ("routing_improvement_delta".to_string(), HashMap::from([("old_routed_avg".to_string(), r1_ri.get(&"routed_avg".to_string()).cloned().unwrap_or(0)), ("new_routed_avg".to_string(), r2_ri.get(&"routed_avg".to_string()).cloned().unwrap_or(0)), ("old_improvement".to_string(), r1_ri.get(&"improvement_points".to_string()).cloned().unwrap_or(0)), ("new_improvement".to_string(), r2_ri.get(&"improvement_points".to_string()).cloned().unwrap_or(0))]))]))
}

/// Get trend data for a metric across all archived runs.
pub async fn profiling_trend(metric: String) -> Result<()> {
    // Get trend data for a metric across all archived runs.
    if !_PROFILING_RUNS_DIR.exists() {
        HashMap::from([("metric".to_string(), metric), ("trend".to_string(), HashMap::new()), ("run_count".to_string(), 0)])
    }
    let mut run_files = { let mut v = _PROFILING_RUNS_DIR.glob("profile_*.json".to_string()).clone(); v.sort(); v };
    let mut trend = HashMap::new();
    let mut run_count = 0;
    for fp in run_files.iter() {
        // try:
        {
            let mut f = File::open(fp)?;
            {
                let mut data = json::load(f);
            }
        }
        // except (json::JSONDecodeError, OSError) as _e:
        run_count += 1;
        let mut profiles = data.get(&"profiles".to_string()).cloned().unwrap_or(HashMap::new());
        for (model_name, profile) in profiles.iter().iter() {
            if metric == "avg_overall".to_string() {
                let mut value = profile.get(&"avg_overall".to_string()).cloned().unwrap_or(0);
            } else {
                let mut value = profile.get(&"perf_stats".to_string()).cloned().unwrap_or(HashMap::new()).get(&metric).cloned().unwrap_or(HashMap::new()).get(&"mean".to_string()).cloned().unwrap_or(0);
            }
            if !trend.contains(&model_name) {
                trend[model_name] = vec![];
            }
            trend[&model_name].push(HashMap::from([("run_id".to_string(), data.get(&"run_id".to_string()).cloned().unwrap_or("".to_string())), ("timestamp".to_string(), data.get(&"timestamp".to_string()).cloned().unwrap_or("".to_string())), ("value".to_string(), ((value as f64) * 10f64.powi(3)).round() / 10f64.powi(3))]));
        }
    }
    Ok(HashMap::from([("metric".to_string(), metric), ("trend".to_string(), trend), ("run_count".to_string(), run_count)]))
}
