/// Admin router — health, metrics, stats, diagnostics, LoRA, state, compact, version.
/// 
/// Endpoints:
/// GET  /health
/// GET  /metrics, /v1/metrics
/// GET  /v1/stats
/// GET  /v1/diagnostics
/// GET  /v1/diagnostics/crashes
/// GET  /v1/diagnostics/profiles
/// POST /v1/cache/clear
/// POST /v1/compact
/// POST /v1/lora/load
/// DELETE /v1/lora/unload
/// GET  /v1/lora/status
/// POST /v1/state/save
/// POST /v1/state/load
/// GET  /v1/state/slots
/// DELETE /v1/state/{slot_name}
/// GET  /v1/system/hardware
/// GET  /api/version

use anyhow::{Result, Context};
use crate::compact_tokens::{compact_messages, CompactConfig};
use crate::hardware::{detect_hardware_summary, detect_hardware_full};
use crate::helpers::{get_state, get_llm, get_token_streamer};
use crate::inference_guard::{get_guard_stats, get_crash_history, get_request_profiles, get_memory_snapshot};
use crate::schemas::{CompactRequest, LoRALoadRequest, StateSaveRequest, StateLoadRequest};
use std::collections::HashMap;
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static ROUTER: std::sync::LazyLock<APIRouter> = std::sync::LazyLock::new(|| Default::default());

/// Health check — public, no auth required.
pub async fn health() -> Result<()> {
    // Health check — public, no auth required.
    let mut state = get_state();
    let mut result = HashMap::from([("status".to_string(), if (state && state::ready) { "ok".to_string() } else { "initializing".to_string() }), ("version".to_string(), "3.5.0".to_string()), ("provider".to_string(), if state { state::provider } else { None }), ("model".to_string(), if state { state::model_id } else { None }), ("uptime_seconds".to_string(), if state { (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - state::start_time).to_string().parse::<i64>().unwrap_or(0) } else { 0 }), ("requests_served".to_string(), if state { state::request_count } else { 0 }), ("cache".to_string(), if state { state::cache::stats() } else { None }), ("streaming".to_string(), if get_token_streamer() { "true_token_level".to_string() } else { "batched".to_string() })]);
    // try:
    {
        let mut hw = detect_hardware_summary();
        if hw {
            result["hardware".to_string()] = hw;
        }
    }
    // except Exception as exc:
    Ok(result)
}

/// Prometheus-compatible text exposition.
pub async fn prometheus_metrics() -> () {
    // Prometheus-compatible text exposition.
    let mut state = get_state();
    let mut lines = vec![];
    let _counter = |name, help_text, value| {
        lines.push(format!("# HELP {} {}", name, help_text));
        lines.push(format!("# TYPE {} counter", name));
        lines.push(format!("{} {}", name, value));
    };
    let _gauge = |name, help_text, value| {
        lines.push(format!("# HELP {} {}", name, help_text));
        lines.push(format!("# TYPE {} gauge", name));
        lines.push(format!("{} {}", name, value));
    };
    if state {
        _counter("ragrat_requests_total".to_string(), "Total requests served".to_string(), state::request_count);
        _counter("ragrat_cache_served_total".to_string(), "Requests served from cache".to_string(), state::cache_served);
        _counter("ragrat_tokens_generated_total".to_string(), "Approximate tokens generated".to_string(), state::total_tokens_approx);
        let mut cs = state::cache::stats();
        _gauge("ragrat_cache_size".to_string(), "Current cache entries".to_string(), cs["size".to_string()]);
        _counter("ragrat_cache_hits_total".to_string(), "Cache hits".to_string(), cs["hits".to_string()]);
        _counter("ragrat_cache_misses_total".to_string(), "Cache misses".to_string(), cs["misses".to_string()]);
        _gauge("ragrat_uptime_seconds".to_string(), "Server uptime".to_string(), (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - state::start_time).to_string().parse::<i64>().unwrap_or(0));
    }
    let mut gs = get_guard_stats();
    _counter("ragrat_inference_calls_total".to_string(), "Total guarded inference calls".to_string(), gs.get(&"total_guarded_calls".to_string()).cloned().unwrap_or(0));
    _counter("ragrat_crashes_total".to_string(), "Total inference crashes".to_string(), gs.get(&"total_crashes".to_string()).cloned().unwrap_or(0));
    let mut timing = gs.get(&"timing".to_string()).cloned().unwrap_or(HashMap::new());
    _gauge("ragrat_inference_avg_ms".to_string(), "Average inference time (ms)".to_string(), format!("{:.1}", timing.get(&"avg_ms".to_string()).cloned().unwrap_or(0)));
    _gauge("ragrat_inference_fastest_ms".to_string(), "Fastest inference (ms)".to_string(), if timing.get(&"fastest_ms".to_string()).cloned() { format!("{:.1}", timing.get(&"fastest_ms".to_string()).cloned().unwrap_or(0)) } else { "0".to_string() });
    _gauge("ragrat_inference_slowest_ms".to_string(), "Slowest inference (ms)".to_string(), format!("{:.1}", timing.get(&"slowest_ms".to_string()).cloned().unwrap_or(0)));
    let mut mem = get_memory_snapshot();
    if mem {
        _gauge("ragrat_process_rss_mb".to_string(), "Process RSS (MB)".to_string(), format!("{:.1}", mem.get(&"process_rss_mb".to_string()).cloned().unwrap_or(0)));
        _gauge("ragrat_system_memory_percent".to_string(), "System memory usage (%)".to_string(), format!("{:.1}", mem.get(&"system_percent".to_string()).cloned().unwrap_or(0)));
    }
    PlainTextResponse((lines.join(&"\n".to_string()) + "\n".to_string()), /* media_type= */ "text/plain; version=0.0.4; charset=utf-8".to_string())
}

/// Server statistics.
pub async fn stats() -> () {
    // Server statistics.
    let mut state = get_state();
    if !state {
        HashMap::from([("status".to_string(), "not initialized".to_string())])
    }
    let mut guard_stats = get_guard_stats();
    let mut timing = guard_stats.get(&"timing".to_string()).cloned().unwrap_or(HashMap::new());
    let mut avg_tps = if timing.get(&"total_ms".to_string()).cloned().unwrap_or(0) > 0 { (state::total_tokens_approx / (timing.get(&"total_ms".to_string()).cloned().unwrap_or(0) / 1000)) } else { 0 };
    let mut info = HashMap::from([("version".to_string(), "3.5.0".to_string()), ("uptime_seconds".to_string(), (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - state::start_time).to_string().parse::<i64>().unwrap_or(0)), ("provider".to_string(), state::provider), ("model".to_string(), state::model_id), ("requests_served".to_string(), state::request_count), ("cache_served".to_string(), state::cache_served), ("approx_tokens_generated".to_string(), state::total_tokens_approx), ("timing".to_string(), HashMap::from([("avg_inference_ms".to_string(), timing.get(&"avg_ms".to_string()).cloned().unwrap_or(0)), ("fastest_ms".to_string(), timing.get(&"fastest_ms".to_string()).cloned()), ("slowest_ms".to_string(), timing.get(&"slowest_ms".to_string()).cloned().unwrap_or(0)), ("avg_tokens_per_sec".to_string(), ((avg_tps as f64) * 10f64.powi(1)).round() / 10f64.powi(1))])), ("cache".to_string(), state::cache::stats()), ("streaming".to_string(), if get_token_streamer() { "true_token_level".to_string() } else { "batched_fallback".to_string() })]);
    let mut inner = state::get_inner_adapter();
    if /* hasattr(inner, "get_stats".to_string()) */ true {
        info["fifo".to_string()] = inner.get_stats();
    }
    info
}

/// Clear the response cache.
pub async fn clear_cache() -> Result<()> {
    // Clear the response cache.
    let mut state = get_state();
    if !state {
        return Err(anyhow::anyhow!("HTTPException(503, 'Server not initialized')"));
    }
    let mut old_stats = state::cache::stats();
    state::cache::clear();
    Ok(HashMap::from([("status".to_string(), "ok".to_string()), ("cleared_entries".to_string(), old_stats["size".to_string()])]))
}

/// Compact a conversation to reduce token count.
pub async fn compact_endpoint(req: CompactRequest) -> Result<()> {
    // Compact a conversation to reduce token count.
    let mut messages = req.messages.iter().map(|m| HashMap::from([("role".to_string(), m.role), ("content".to_string(), m.content)])).collect::<Vec<_>>();
    if !messages {
        return Err(anyhow::anyhow!("HTTPException(400, 'messages required')"));
    }
    let mut config = CompactConfig(/* keep_last_n= */ req.keep_last_n, /* summarize_older= */ req.summarize_older, /* compress_text= */ req.compress_text, /* target_ctx_tokens= */ req.target_tokens);
    let (mut compacted, mut stats_data) = compact_messages(messages, config);
    Ok(HashMap::from([("messages".to_string(), compacted), ("stats".to_string(), stats_data)]))
}

/// Inference diagnostics — memory, crash data, FIFO state.
pub async fn diagnostics() -> () {
    // Inference diagnostics — memory, crash data, FIFO state.
    let mut state = get_state();
    let mut result = HashMap::from([("guard_stats".to_string(), get_guard_stats()), ("memory".to_string(), get_memory_snapshot()), ("recent_crashes".to_string(), get_crash_history()[..10])]);
    if (state && state::adapter) {
        let mut inner = state::get_inner_adapter();
        if /* hasattr(inner, "get_stats".to_string()) */ true {
            result["fifo".to_string()] = inner.get_stats();
        }
    }
    result
}

/// Full crash history (last 50 crashes).
pub async fn crash_history_endpoint() -> () {
    // Full crash history (last 50 crashes).
    HashMap::from([("stats".to_string(), get_guard_stats()), ("crashes".to_string(), get_crash_history())])
}

/// Per-request profiling.
pub async fn profiles_endpoint(last_n: i64) -> () {
    // Per-request profiling.
    let mut profiles = get_request_profiles(/* last_n= */ last_n.min(100));
    HashMap::from([("stats".to_string(), get_guard_stats()), ("profile_count".to_string(), profiles.len()), ("profiles".to_string(), profiles)])
}

/// Load a LoRA adapter at runtime.
pub async fn load_lora(req: LoRALoadRequest) -> Result<()> {
    // Load a LoRA adapter at runtime.
    let mut state = get_state();
    let mut llm = get_llm();
    if !llm {
        return Err(anyhow::anyhow!("HTTPException(503, detail='Model not loaded')"));
    }
    let mut lora_path = PathBuf::from(req.lora_path);
    if !lora_path.exists() {
        return Err(anyhow::anyhow!("HTTPException(404, detail=f'LoRA file not found: {req.lora_path}')"));
    }
    // try:
    {
        let _ctx = state::inference_semaphore;
        {
            if /* hasattr(llm, "load_lora_adapter".to_string()) */ true {
                llm.load_lora_adapter(lora_path.to_string(), /* scale= */ req.scale);
            } else if /* hasattr(llm, "set_lora".to_string()) */ true {
                llm.set_lora(lora_path.to_string(), /* scale= */ req.scale);
            } else {
                return Err(anyhow::anyhow!("HTTPException(501, detail='LoRA API not available in this llama-cpp-python version')"));
            }
        }
        state::active_lora = lora_path.to_string();
        state::lora_scale = req.scale;
        state::cache::clear();
        logger.info(format!("LoRA loaded: {} (scale={})", lora_path.file_name().unwrap_or_default().to_str().unwrap_or(""), req.scale));
        HashMap::from([("status".to_string(), "ok".to_string()), ("lora_path".to_string(), lora_path.to_string()), ("lora_name".to_string(), lora_path.file_stem().unwrap_or_default().to_str().unwrap_or("")), ("scale".to_string(), req.scale), ("model".to_string(), state::model_id)])
    }
    // except HTTPException as _e:
    // except Exception as e:
}

/// Remove the currently loaded LoRA adapter.
pub async fn unload_lora() -> Result<()> {
    // Remove the currently loaded LoRA adapter.
    let mut state = get_state();
    let mut llm = get_llm();
    if !llm {
        return Err(anyhow::anyhow!("HTTPException(503, detail='Model not loaded')"));
    }
    if !state::active_lora {
        HashMap::from([("status".to_string(), "ok".to_string()), ("message".to_string(), "No LoRA adapter loaded".to_string())])
    }
    // try:
    {
        let _ctx = state::inference_semaphore;
        {
            if /* hasattr(llm, "unload_lora_adapter".to_string()) */ true {
                llm.unload_lora_adapter();
            } else if /* hasattr(llm, "set_lora".to_string()) */ true {
                llm.set_lora(None);
            }
        }
        let mut prev = state::active_lora;
        state::active_lora = None;
        state::lora_scale = 1.0_f64;
        state::cache::clear();
        logger.info(format!("LoRA unloaded: {}", prev));
        HashMap::from([("status".to_string(), "ok".to_string()), ("unloaded".to_string(), prev)])
    }
    // except Exception as e:
}

/// Check current LoRA adapter status.
pub async fn lora_status() -> () {
    // Check current LoRA adapter status.
    let mut state = get_state();
    HashMap::from([("active".to_string(), if state { state::active_lora.is_some() } else { false }), ("lora_path".to_string(), if state { state::active_lora } else { None }), ("scale".to_string(), if state { state::lora_scale } else { 1.0_f64 }), ("model".to_string(), if state { state::model_id } else { None })])
}

/// Save the model's KV-cache state to disk.
pub async fn save_state(req: StateSaveRequest) -> Result<()> {
    // Save the model's KV-cache state to disk.
    let mut state = get_state();
    let mut llm = get_llm();
    if !llm {
        return Err(anyhow::anyhow!("HTTPException(503, detail='Model not loaded')"));
    }
    let mut slot_file = (state::_states_dir / format!("{}.bin", req.slot_name));
    // try:
    {
        let _ctx = state::inference_semaphore;
        {
            if /* hasattr(llm, "save_state".to_string()) */ true {
                let mut llm_state = llm.save_state();
                slot_file.write_bytes(llm_state);
            } else {
                return Err(anyhow::anyhow!("HTTPException(501, detail='State save not supported in this llama-cpp-python version')"));
            }
        }
        let mut size_mb = (slot_file.stat().st_size / (1024 * 1024));
        logger.info(format!("State saved: {} ({:.1} MB)", req.slot_name, size_mb));
        HashMap::from([("status".to_string(), "ok".to_string()), ("slot_name".to_string(), req.slot_name), ("path".to_string(), slot_file.to_string()), ("size_mb".to_string(), ((size_mb as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("model".to_string(), state::model_id)])
    }
    // except HTTPException as _e:
    // except Exception as e:
}

/// Load a previously saved KV-cache state from disk.
pub async fn load_state(req: StateLoadRequest) -> Result<()> {
    // Load a previously saved KV-cache state from disk.
    let mut state = get_state();
    let mut llm = get_llm();
    if !llm {
        return Err(anyhow::anyhow!("HTTPException(503, detail='Model not loaded')"));
    }
    let mut slot_file = (state::_states_dir / format!("{}.bin", req.slot_name));
    if !slot_file.exists() {
        let mut available = state::_states_dir.glob("*.bin".to_string()).iter().map(|f| f.file_stem().unwrap_or_default().to_str().unwrap_or("")).collect::<Vec<_>>();
        return Err(anyhow::anyhow!("HTTPException(404, detail=f\"State slot '{req.slot_name}' not found. Available: {available}\")"));
    }
    // try:
    {
        let _ctx = state::inference_semaphore;
        {
            if /* hasattr(llm, "load_state".to_string()) */ true {
                let mut state_data = slot_file.read_bytes();
                llm.load_state(state_data);
            } else {
                return Err(anyhow::anyhow!("HTTPException(501, detail='State load not supported in this llama-cpp-python version')"));
            }
        }
        let mut size_mb = (slot_file.stat().st_size / (1024 * 1024));
        logger.info(format!("State loaded: {} ({:.1} MB)", req.slot_name, size_mb));
        HashMap::from([("status".to_string(), "ok".to_string()), ("slot_name".to_string(), req.slot_name), ("size_mb".to_string(), ((size_mb as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("model".to_string(), state::model_id)])
    }
    // except HTTPException as _e:
    // except Exception as e:
}

/// List all saved state slots with metadata.
pub async fn list_state_slots() -> () {
    // List all saved state slots with metadata.
    let mut state = get_state();
    let mut slots = vec![];
    if (state && state::_states_dir.exists()) {
        for f in state::_states_dir.glob("*.bin".to_string()).iter() {
            slots.push(HashMap::from([("slot_name".to_string(), f.file_stem().unwrap_or_default().to_str().unwrap_or("")), ("size_mb".to_string(), (((f.stat().st_size / (1024 * 1024)) as f64) * 10f64.powi(2)).round() / 10f64.powi(2)), ("created".to_string(), f.stat().st_mtime)]));
        }
    }
    HashMap::from([("slots".to_string(), slots), ("count".to_string(), slots.len())])
}

/// Delete a saved state slot.
pub async fn delete_state_slot(slot_name: String) -> Result<()> {
    // Delete a saved state slot.
    let mut state = get_state();
    if !state {
        return Err(anyhow::anyhow!("HTTPException(503, detail='Server not initialized')"));
    }
    let mut slot_file = (state::_states_dir / format!("{}.bin", slot_name));
    if !slot_file.exists() {
        return Err(anyhow::anyhow!("HTTPException(404, detail=f\"State slot '{slot_name}' not found\")"));
    }
    slot_file.remove_file().ok();
    logger.info(format!("State slot deleted: {}", slot_name));
    Ok(HashMap::from([("status".to_string(), "ok".to_string()), ("deleted".to_string(), slot_name)]))
}

/// Full hardware report with model recommendations.
pub async fn system_hardware() -> () {
    // Full hardware report with model recommendations.
    detect_hardware_full()
}

/// Simple version endpoint — compatible with Ollama's /api/version.
pub async fn api_version() -> () {
    // Simple version endpoint — compatible with Ollama's /api/version.
    HashMap::from([("version".to_string(), "3.5.0".to_string()), ("name".to_string(), "RAG_RAT API Server".to_string()), ("api_compatibility".to_string(), "OpenAI".to_string()), ("features".to_string(), vec!["chat_completions".to_string(), "completions".to_string(), "embeddings".to_string(), "tool_calling".to_string(), "fim_infill".to_string(), "structured_output".to_string(), "lora_hot_swap".to_string(), "model_pull".to_string(), "state_save_load".to_string(), "tokenize".to_string(), "detokenize".to_string(), "metrics".to_string(), "diagnostics".to_string(), "moe_detection".to_string(), "hardware_detection".to_string(), "model_router".to_string(), "gpu_presets".to_string(), "model_discovery".to_string(), "domain_routing".to_string(), "performance_profiling".to_string(), "run_history".to_string(), "difficulty_routing".to_string(), "swap_cost_tracking".to_string(), "compound_strategies".to_string(), "rag_aware_routing".to_string(), "live_feedback_loop".to_string()])])
}
