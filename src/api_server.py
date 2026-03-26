"""
ZEN_RAG API Server v3.5.0 — OpenAI-compatible, in-process inference.

Architecture (refactored — split into server/ package):
  api_server.py        — App factory, middleware, lifespan, auth, main()
  server/schemas.py    — Pydantic request/response models
  server/state.py      — ResponseCache, ServerState, SwapTracker
  server/helpers.py    — Shared utilities
  server/hardware.py   — Hardware detection & GPU presets
  server/routing.py    — Domain/difficulty classification, strategies, RAG routing
  server/feedback.py   — FeedbackCollector
  server/routers/      — FastAPI APIRouter modules (chat, models, inference, admin,
                         routing_routes, feedback_routes)

Compatible with: OpenClaw, LangChain, Aider, Continue, Open Interpreter,
                 ChatGPT UI, or any client speaking the OpenAI API.
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Import split modules ──────────────────────────────────────────────
from server.schemas import (  # noqa: E402, F401
    ChatMessage,
    ChatCompletionRequest,
    CompletionRequest,
    CompactRequest,
    EmbeddingRequest,
    TokenizeRequest,
    DetokenizeRequest,
    TokenCountRequest,
    InfillRequest,
    LoRALoadRequest,
    ModelPullRequest,
    StateSaveRequest,
    StateLoadRequest,
    InferenceRequest,
)
from server.state import (  # noqa: E402, F401
    ResponseCache,
    ServerState,
    SwapTracker,
)
from server.hardware import (  # noqa: E402, F401
    detect_hardware_summary as _detect_hardware_summary,
    detect_hardware_full as _detect_hardware_full,
    GPU_PRESETS as _GPU_PRESETS,
)
from server.routing import (  # noqa: E402, F401
    classify_query_domain as _classify_query_domain,
    classify_query_difficulty as _classify_query_difficulty,
    DOMAIN_KEYWORDS as _DOMAIN_KEYWORDS,
    DIFFICULTY_HARD_SIGNALS as _DIFFICULTY_HARD_SIGNALS,
    DIFFICULTY_EASY_SIGNALS as _DIFFICULTY_EASY_SIGNALS,
    load_model_profiles as _load_model_profiles,
    BUILTIN_STRATEGIES as _BUILTIN_STRATEGIES,
    resolve_strategy_step as _resolve_strategy_step,
    evaluate_strategy as _evaluate_strategy,
    custom_strategies as _custom_strategies,
    DEFAULT_RAG_WEIGHTS as _DEFAULT_RAG_WEIGHTS,
    estimate_rag_context as _estimate_rag_context,
    score_model_for_rag as _score_model_for_rag,
    rank_models_for_rag as _rank_models_for_rag,
)
from server.feedback import FeedbackCollector  # noqa: E402, F401

# Router imports
from server.routers.chat import (  # noqa: E402, F401
    router as _chat_router,
    chat_completions,
    completions,
    infill,
)
from server.routers.models import (  # noqa: E402, F401
    router as _models_router,
    list_models,
    model_info,
    switch_model,
    reload_model,
    available_models,
    list_presets,
    apply_preset,
    pull_model,
    pull_status,
    list_downloads,
    get_model_profiles,
    model_performance,
    get_model,
    _download_tasks,
)
from server.routers.inference import (  # noqa: E402, F401
    router as _inference_router,
    embeddings,
    tokenize,
    detokenize,
    count_tokens,
)
from server.routers.admin import (  # noqa: E402, F401
    router as _admin_router,
    health,
    prometheus_metrics,
    stats,
    clear_cache,
    compact_endpoint,
    diagnostics,
    crash_history_endpoint,
    profiles_endpoint,
    load_lora,
    unload_lora,
    lora_status,
    save_state,
    load_state,
    list_state_slots,
    delete_state_slot,
    system_hardware,
    api_version,
)
from server.routers.routing_routes import (  # noqa: E402, F401
    router as _routing_router,
)
from server.routers.feedback_routes import (  # noqa: E402, F401
    router as _feedback_router,
)
from server.routers.rag_chat import (  # noqa: E402, F401
    router as _rag_chat_router,
)

# ── Logging ───────────────────────────────────────────────────────────

logger = logging.getLogger("api_server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-14s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)

# ── Global singletons (canonical locations) ───────────────────────────

state: Optional[ServerState] = None
_swap_tracker = SwapTracker()
_feedback_collector = FeedbackCollector()


def _get_llm():
    """Get the raw Llama object (or None) — patchable by tests."""
    if not state or not state.adapter:
        return None
    inner = state.get_inner_adapter()
    return getattr(inner.__class__, "_shared_llm", None)


def _get_token_streamer():
    """Get the adapter that supports true token-level streaming — patchable by tests."""
    if not state or not state.adapter:
        return None
    for obj in (state.adapter, state.get_inner_adapter()):
        if hasattr(obj, "query_stream_tokens"):
            return obj
    return None


# Idle sleep
_idle_task: Optional[asyncio.Task] = None
_IDLE_TIMEOUT_SECONDS = int(os.environ.get("_ZEN_RAG_IDLE_TIMEOUT", "0"))


# ── API Key Authentication ────────────────────────────────────────────


def _get_server_api_key() -> Optional[str]:
    """Return configured server API key, or None if auth disabled."""
    return os.environ.get("_ZEN_RAG_SERVER_API_KEY")


async def verify_api_key(request: Request):
    """FastAPI dependency — reject requests without valid API key."""
    expected = _get_server_api_key()
    if not expected:
        return
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    else:
        token = request.headers.get("x-api-key", "")
    if token != expected:
        raise HTTPException(401, detail="Invalid API Key")


# ── Idle Sleep ────────────────────────────────────────────────────────


async def _idle_sleep_loop():
    """Background task: check every 30s if model should be unloaded."""
    while True:
        await asyncio.sleep(30)
        if not state or not state.ready or _IDLE_TIMEOUT_SECONDS <= 0:
            continue
        idle = time.time() - state.last_request_time
        if idle >= _IDLE_TIMEOUT_SECONDS:
            inner = state.get_inner_adapter()
            llm_cls = inner.__class__
            if hasattr(llm_cls, "_shared_llm") and llm_cls._shared_llm is not None:
                logger.info(f"[idle-sleep] Model idle {idle:.0f}s (threshold={_IDLE_TIMEOUT_SECONDS}s) — unloading")
                with llm_cls._shared_lock:
                    del llm_cls._shared_llm
                    llm_cls._shared_llm = None
                    llm_cls._shared_model_path = None


# ── Lifespan ──────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize adapter on startup, cleanup on shutdown."""
    global state, _idle_task
    if state is None:
        provider = os.environ.get("_ZEN_RAG_PROVIDER", "Local (llama-cpp)")
        model = os.environ.get("_ZEN_RAG_MODEL")
        api_key = os.environ.get("_ZEN_RAG_API_KEY")
        cache_size = int(os.environ.get("_ZEN_RAG_CACHE_SIZE", "200"))
        kwargs = {}
        if model:
            kwargs["model_name"] = model
        if api_key:
            kwargs["api_key"] = api_key
        state = ServerState(provider=provider, cache_size=cache_size, **kwargs)
    if not state.ready:
        state.initialize()
    if _IDLE_TIMEOUT_SECONDS > 0:
        _idle_task = asyncio.create_task(_idle_sleep_loop())
        logger.info(f"[idle-sleep] Enabled: unload after {_IDLE_TIMEOUT_SECONDS}s idle")
    yield
    if _idle_task:
        _idle_task.cancel()
    logger.info("Server shutting down.")


# ── FastAPI App ───────────────────────────────────────────────────────

app = FastAPI(
    title="ZEN_RAG API",
    description=(
        "OpenAI-compatible API with TRUE token streaming. "
        "In-process FIFO inference via llama_cpp. Zero network to model."
    ),
    version="3.5.0",
    lifespan=lifespan,
    dependencies=[Depends(verify_api_key)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8501",
        "http://localhost:8502",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:8501",
        "http://127.0.0.1:8502",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(_chat_router)
app.include_router(_inference_router)
app.include_router(_admin_router)
app.include_router(_routing_router)
app.include_router(_feedback_router)
app.include_router(_rag_chat_router)
# Models router LAST because /v1/models/{model_id} catch-all must not shadow others
app.include_router(_models_router)


# ── Main ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="ZEN_RAG OpenAI-Compatible API Server v3.5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python api_server.py                              # Local GGUF on :8800
  python api_server.py --port 9000                  # Custom port
  python api_server.py --provider "Ollama"           # Use Ollama backend
  python api_server.py --provider "OpenAI" --model gpt-4
  python api_server.py --server-api-key mykey        # Require API key
  python api_server.py --idle-timeout 300            # Unload after 5min idle

Then point any OpenAI-compatible client at http://localhost:8800/v1
        """,
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8800)
    parser.add_argument("--provider", default="Local (llama-cpp)")
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key", default=None, help="API key for upstream provider (e.g. OpenAI)")
    parser.add_argument(
        "--server-api-key",
        default=None,
        help="Require this key for all API requests (Bearer token)",
    )
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=0,
        help="Unload model after N seconds idle (0=disabled)",
    )
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--cache-size", type=int, default=200)

    args = parser.parse_args()

    os.environ["_ZEN_RAG_PROVIDER"] = args.provider
    os.environ["_ZEN_RAG_CACHE_SIZE"] = str(args.cache_size)
    if args.model:
        os.environ["_ZEN_RAG_MODEL"] = args.model
    if args.api_key:
        os.environ["_ZEN_RAG_API_KEY"] = args.api_key
    if args.server_api_key:
        os.environ["_ZEN_RAG_SERVER_API_KEY"] = args.server_api_key
    if args.idle_timeout:
        os.environ["_ZEN_RAG_IDLE_TIMEOUT"] = str(args.idle_timeout)

    global _IDLE_TIMEOUT_SECONDS
    _IDLE_TIMEOUT_SECONDS = args.idle_timeout

    auth_status = "ENABLED" if _get_server_api_key() else "disabled"
    idle_status = f"{args.idle_timeout}s" if args.idle_timeout else "disabled"
    port_pad = " " * max(0, 14 - len(str(args.port)))
    print(f"""
\u2554{"=" * 62}\u2557
\u2551              ZEN_RAG API Server v3.5.0                      \u2551
\u2560{"=" * 62}\u2563
\u2551  Endpoint:    http://{args.host}:{args.port}/v1              {port_pad}\u2551
\u2551  Provider:    {args.provider:<44}\u2551
\u2551  Model:       {(args.model or "auto-detect"):<44}\u2551
\u2551  Cache:       {args.cache_size:<4} responses (LRU)                           \u2551
\u2551  Auth:        {auth_status:<44}\u2551
\u2551  Idle sleep:  {idle_status:<44}\u2551
\u2560{"=" * 62}\u2563
\u2551  v3.5 \u2014 MoE Detection \u2022 Hardware Info \u2022 GPU Presets        \u2551
\u2551         Model Router \u2022 Model Discovery                     \u2551
\u2551  v3.4 \u2014 LoRA Hot-Swap \u2022 Model Pull \u2022 State Save/Load      \u2551
\u2551  v3.3 \u2014 Tool Calling \u2022 FIM/Infill \u2022 Structured Output     \u2551
\u255a{"=" * 62}\u255d
""")

    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level="info",
    )


if __name__ == "__main__":
    main()
