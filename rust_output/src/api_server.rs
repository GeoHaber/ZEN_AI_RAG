/// ZEN_RAG API Server v3.5.0 — OpenAI-compatible, in-process inference.
/// 
/// Architecture (refactored — split into server/ package):
/// api_server::py        — App factory, middleware, lifespan, auth, main()
/// server/schemas::py    — Pydantic request/response models
/// server/state::py      — ResponseCache, ServerState, SwapTracker
/// server/helpers::py    — Shared utilities
/// server/hardware::py   — Hardware detection & GPU presets
/// server/routing::py    — Domain/difficulty classification, strategies, RAG routing
/// server/feedback::py   — FeedbackCollector
/// server/routers/      — FastAPI APIRouter modules (chat, models, inference, admin,
/// routing_routes, feedback_routes)
/// 
/// Compatible with: OpenClaw, LangChain, Aider, Continue, Open Interpreter,
/// ChatGPT UI, or any client speaking the OpenAI API.

use anyhow::{Result, Context};
use crate::admin::{router, health, prometheus_metrics, stats, clear_cache, compact_endpoint, diagnostics, crash_history_endpoint, profiles_endpoint, load_lora, unload_lora, lora_status, save_state, load_state, list_state_slots, delete_state_slot, system_hardware, api_version};
use crate::chat::{router, chat_completions, completions, infill};
use crate::feedback::{FeedbackCollector};
use crate::feedback_routes::{router};
use crate::hardware::{detect_hardware_summary, detect_hardware_full, GPU_PRESETS};
use crate::inference::{router, embeddings, tokenize, detokenize, count_token};
use crate::models::{router, list_models, model_info, switch_model, reload_model, available_models, list_presets, apply_preset, pull_model, pull_status, list_downloads, get_model_profiles, model_performance, get_model, _download_task};
use crate::rag_chat::{router};
use crate::routing::{classify_query_domain, classify_query_difficulty, DOMAIN_KEYWORDS, DIFFICULTY_HARD_SIGNALS, DIFFICULTY_EASY_SIGNALS, load_model_profiles, BUILTIN_STRATEGIES, resolve_strategy_step, evaluate_strategy, custom_strategies, DEFAULT_RAG_WEIGHTS, estimate_rag_context, score_model_for_rag, rank_models_for_rag};
use crate::routing_routes::{router};
use crate::schemas::{ChatMessage, ChatCompletionRequest, CompletionRequest, CompactRequest, EmbeddingRequest, TokenizeRequest, DetokenizeRequest, TokenCountRequest, InfillRequest, LoRALoadRequest, ModelPullRequest, StateSaveRequest, StateLoadRequest, InferenceRequest};
use crate::state::{ResponseCache, ServerState, SwapTracker};
use std::collections::HashMap;
use tokio;

pub const _PROJECT_ROOT: &str = "Path(file!()).resolve().parent";

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static STATE: std::sync::LazyLock<Option<ServerState>> = std::sync::LazyLock::new(|| None);

pub static _SWAP_TRACKER: std::sync::LazyLock<SwapTracker> = std::sync::LazyLock::new(|| Default::default());

pub static _FEEDBACK_COLLECTOR: std::sync::LazyLock<FeedbackCollector> = std::sync::LazyLock::new(|| Default::default());

pub static _IDLE_TASK: std::sync::LazyLock<Option<asyncio::Task>> = std::sync::LazyLock::new(|| None);

pub const _IDLE_TIMEOUT_SECONDS: i64 = 0;

pub static APP: std::sync::LazyLock<FastAPI> = std::sync::LazyLock::new(|| Default::default());

/// Get the raw Llama object (or None) — patchable by tests.
pub fn _get_llm() -> () {
    // Get the raw Llama object (or None) — patchable by tests.
    if (!state || !state::adapter) {
        None
    }
    let mut inner = state::get_inner_adapter();
    /* getattr */ None
}

/// Get the adapter that supports true token-level streaming — patchable by tests.
pub fn _get_token_streamer() -> () {
    // Get the adapter that supports true token-level streaming — patchable by tests.
    if (!state || !state::adapter) {
        None
    }
    for obj in (state::adapter, state::get_inner_adapter()).iter() {
        if /* hasattr(obj, "query_stream_tokens".to_string()) */ true {
            obj
        }
    }
    None
}

/// Return configured server API key, or None if auth disabled.
pub fn _get_server_api_key() -> Option<String> {
    // Return configured server API key, or None if auth disabled.
    std::env::var(&"_ZEN_RAG_SERVER_API_KEY".to_string()).unwrap_or_default().cloned()
}

/// FastAPI dependency — reject requests without valid API key.
pub async fn verify_api_key(request: Request) -> Result<()> {
    // FastAPI dependency — reject requests without valid API key.
    let mut expected = _get_server_api_key();
    if !expected {
        return;
    }
    let mut auth = request.headers.get(&"authorization".to_string()).cloned().unwrap_or("".to_string());
    if auth.starts_with(&*"Bearer ".to_string()) {
        let mut token = auth[7..];
    } else {
        let mut token = request.headers.get(&"x-api-key".to_string()).cloned().unwrap_or("".to_string());
    }
    if token != expected {
        return Err(anyhow::anyhow!("HTTPException(401, detail='Invalid API Key')"));
    }
}

/// Background task: check every 30s if model should be unloaded.
pub async fn _idle_sleep_loop() -> () {
    // Background task: check every 30s if model should be unloaded.
    while true {
        asyncio.sleep(30).await;
        if (!state || !state::ready || _IDLE_TIMEOUT_SECONDS <= 0) {
            continue;
        }
        let mut idle = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - state::last_request_time);
        if idle >= _IDLE_TIMEOUT_SECONDS {
            let mut inner = state::get_inner_adapter();
            let mut llm_cls = inner.__class__;
            if (/* hasattr(llm_cls, "_shared_llm".to_string()) */ true && llm_cls._shared_llm.is_some()) {
                logger.info(format!("[idle-sleep] Model idle {:.0}s (threshold={}s) — unloading", idle, _IDLE_TIMEOUT_SECONDS));
                let _ctx = llm_cls._shared_lock;
                {
                    drop(llm_cls._shared_llm);
                    llm_cls._shared_llm = None;
                    llm_cls._shared_model_path = None;
                }
            }
        }
    }
}

/// Initialize adapter on startup, cleanup on shutdown.
pub async fn lifespan(application: FastAPI) -> () {
    // Initialize adapter on startup, cleanup on shutdown.
    // global/nonlocal state, _idle_task
    if state::is_none() {
        let mut provider = std::env::var(&"_ZEN_RAG_PROVIDER".to_string()).unwrap_or_default().cloned().unwrap_or("Local (llama-cpp)".to_string());
        let mut model = std::env::var(&"_ZEN_RAG_MODEL".to_string()).unwrap_or_default().cloned();
        let mut api_key = std::env::var(&"_ZEN_RAG_API_KEY".to_string()).unwrap_or_default().cloned();
        let mut cache_size = std::env::var(&"_ZEN_RAG_CACHE_SIZE".to_string()).unwrap_or_default().cloned().unwrap_or("200".to_string()).to_string().parse::<i64>().unwrap_or(0);
        let mut kwargs = HashMap::new();
        if model {
            kwargs["model_name".to_string()] = model;
        }
        if api_key {
            kwargs["api_key".to_string()] = api_key;
        }
        let mut state = ServerState(/* provider= */ provider, /* cache_size= */ cache_size, /* ** */ kwargs);
    }
    if !state::ready {
        state::initialize();
    }
    if _IDLE_TIMEOUT_SECONDS > 0 {
        let mut _idle_task = asyncio.create_task(_idle_sleep_loop());
        logger.info(format!("[idle-sleep] Enabled: unload after {}s idle", _IDLE_TIMEOUT_SECONDS));
    }
    /* yield */;
    if _idle_task {
        _idle_task.cancel();
    }
    logger.info("Server shutting down.".to_string());
}

pub fn main() -> () {
    let mut parser = argparse.ArgumentParser(/* description= */ "ZEN_RAG OpenAI-Compatible API Server v3.5".to_string(), /* formatter_class= */ argparse.RawDescriptionHelpFormatter, /* epilog= */ "\nExamples:\n  python api_server::py                              # Local GGUF on :8800\n  python api_server::py --port 9000                  # Custom port\n  python api_server::py --provider \"Ollama\"           # Use Ollama backend\n  python api_server::py --provider \"OpenAI\" --model gpt-4\n  python api_server::py --server-api-key mykey        # Require API key\n  python api_server::py --idle-timeout 300            # Unload after 5min idle\n\nThen point any OpenAI-compatible client at http://localhost:8800/v1\n        ".to_string());
    parser.add_argument("--host".to_string(), /* default= */ "127.0.0.1".to_string());
    parser.add_argument("--port".to_string(), /* type= */ int, /* default= */ 8800);
    parser.add_argument("--provider".to_string(), /* default= */ "Local (llama-cpp)".to_string());
    parser.add_argument("--model".to_string(), /* default= */ None);
    parser.add_argument("--api-key".to_string(), /* default= */ None, /* help= */ "API key for upstream provider (e.g. OpenAI)".to_string());
    parser.add_argument("--server-api-key".to_string(), /* default= */ None, /* help= */ "Require this key for all API requests (Bearer token)".to_string());
    parser.add_argument("--idle-timeout".to_string(), /* type= */ int, /* default= */ 0, /* help= */ "Unload model after N seconds idle (0=disabled)".to_string());
    parser.add_argument("--reload".to_string(), /* action= */ "store_true".to_string());
    parser.add_argument("--workers".to_string(), /* type= */ int, /* default= */ 1);
    parser.add_argument("--cache-size".to_string(), /* type= */ int, /* default= */ 200);
    let mut args = parser.parse_args();
    std::env::var("_ZEN_RAG_PROVIDER".to_string()).unwrap() = args.provider;
    std::env::var("_ZEN_RAG_CACHE_SIZE".to_string()).unwrap() = args.cache_size.to_string();
    if args.model {
        std::env::var("_ZEN_RAG_MODEL".to_string()).unwrap() = args.model;
    }
    if args.api_key {
        std::env::var("_ZEN_RAG_API_KEY".to_string()).unwrap() = args.api_key;
    }
    if args.server_api_key {
        std::env::var("_ZEN_RAG_SERVER_API_KEY".to_string()).unwrap() = args.server_api_key;
    }
    if args.idle_timeout {
        std::env::var("_ZEN_RAG_IDLE_TIMEOUT".to_string()).unwrap() = args.idle_timeout.to_string();
    }
    // global/nonlocal _IDLE_TIMEOUT_SECONDS
    let mut _IDLE_TIMEOUT_SECONDS = args.idle_timeout;
    let mut auth_status = if _get_server_api_key() { "ENABLED".to_string() } else { "disabled".to_string() };
    let mut idle_status = if args.idle_timeout { format!("{}s", args.idle_timeout) } else { "disabled".to_string() };
    let mut port_pad = (" ".to_string() * 0.max((14 - args.port.to_string().len())));
    println!("\n╔{}╗\n║              ZEN_RAG API Server v3.5.0                      ║\n╠{}╣\n║  Endpoint:    http://{}:{}/v1              {}║\n║  Provider:    {:<44}║\n║  Model:       {:<44}║\n║  Cache:       {:<4} responses (LRU)                           ║\n║  Auth:        {:<44}║\n║  Idle sleep:  {:<44}║\n╠{}╣\n║  v3.5 — MoE Detection • Hardware Info • GPU Presets        ║\n║         Model Router • Model Discovery                     ║\n║  v3.4 — LoRA Hot-Swap • Model Pull • State Save/Load      ║\n║  v3.3 — Tool Calling • FIM/Infill • Structured Output     ║\n╚{}╝\n", ("=".to_string() * 62), ("=".to_string() * 62), args.host, args.port, port_pad, args.provider, (args.model || "auto-detect".to_string()), args.cache_size, auth_status, idle_status, ("=".to_string() * 62), ("=".to_string() * 62));
    uvicorn.run("api_server:app".to_string(), /* host= */ args.host, /* port= */ args.port, /* reload= */ args.reload, /* workers= */ args.workers, /* log_level= */ "info".to_string());
}
