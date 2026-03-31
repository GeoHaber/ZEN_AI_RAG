"""
RAG Test Bench — Flask application
===================================
Web UI for managing websites, crawling, indexing, and testing RAG queries.
Includes a chatbot that converses with the indexed data via any OpenAI-compatible API.

Usage:
    pip install -r requirements.txt
    python app.py          # → http://localhost:5050

Environment variables (all optional):
    RAG_MODEL      = sentence-transformer model  (default: all-MiniLM-L6-v2)
    RAG_NBITS      = TurboQuant bit width          (default: 3)
    RAG_CHUNK_SIZE = chunk size in chars            (default: 512)
    RAG_PORT       = server port                    (default: 5050)
    LLM_BASE_URL   = OpenAI-compatible API base     (default: http://localhost:11434/v1)
    LLM_API_KEY    = API key                        (default: ollama)
    LLM_MODEL      = model name                     (default: llama3.2)
"""

from __future__ import annotations

import json
import logging
import os
import queue as queue_mod
import threading
import time
from pathlib import Path

# Force PyTorch-only mode (avoid Keras 3 / TensorFlow conflicts)
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")

from flask import Flask, jsonify, make_response, render_template, request, Response, stream_with_context

from crawler import CrawlResult, crawl_site
import requests as http_requests
from zen_core_libs.llm import LlamaServerManager, discover_models, find_llama_server_binary, pick_default_model
from zen_core_libs.acquire.model_hub import ModelHub, MODEL_CATALOG
from zen_core_libs.rag import (
    RAGIndex, chunk_text, warmup as warmup_embedder, Chunk,
    SmartDeduplicator,
    Reranker, get_reranker,
    QueryRouter, QueryIntent,
    HallucinationDetector,
    ZeroWasteCache,
    MetricsTracker, get_tracker,
    HyDERetriever,
    FLARERetriever,
    CorrectiveRAG,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
SITES_FILE = Path("sites.json")
INDEX = RAGIndex()
LLAMA = LlamaServerManager()
MODEL_HUB = ModelHub()

# ── zen_core_libs advanced RAG components ─────────────────────────────────
DEDUPER = SmartDeduplicator()
RERANKER = Reranker(use_cross_encoder=False)   # heuristic by default (fast)
ROUTER = QueryRouter()
HALLUCINATION_DETECTOR = HallucinationDetector()
SEARCH_CACHE = ZeroWasteCache(max_entries=256, ttl_seconds=1800)
METRICS = get_tracker()

# ── Pipeline Presets (Benchmark Comparison Framework) ─────────────────────
PIPELINE_PRESETS = {
    "baseline": {
        "label": "Baseline",
        "desc": "Direct vector search \u2014 no post-processing.",
        "color": "#3b82f6",
        "rerank": False, "dedup": False, "query_routing": False,
        "hallucination_check": False, "corrective_rag": False,
    },
    "reranked": {
        "label": "Reranked",
        "desc": "Vector search + Reranker + Smart Dedup.",
        "color": "#8b5cf6",
        "rerank": True, "dedup": True, "query_routing": False,
        "hallucination_check": False, "corrective_rag": False,
    },
    "routed": {
        "label": "Query Routed",
        "desc": "Intent-aware routing + adaptive retrieval + Reranker.",
        "color": "#f59e0b",
        "rerank": True, "dedup": True, "query_routing": True,
        "hallucination_check": False, "corrective_rag": False,
    },
    "full_stack": {
        "label": "Full Stack",
        "desc": "CRAG + Reranker + Dedup + Hallucination detection.",
        "color": "#10b981",
        "rerank": True, "dedup": True, "query_routing": True,
        "hallucination_check": True, "corrective_rag": True,
    },
}

_ACTIVE_PIPELINES_FILE = Path("active_pipelines.json")


def _load_active_pipelines() -> list[str]:
    if _ACTIVE_PIPELINES_FILE.exists():
        try:
            with open(_ACTIVE_PIPELINES_FILE, "r", encoding="utf-8") as f:
                ids = json.load(f)
            return [pid for pid in ids if pid in PIPELINE_PRESETS][:4]
        except (json.JSONDecodeError, ValueError, OSError):
            logger.warning("Corrupt active_pipelines.json — using defaults")
    return ["full_stack"]


def _save_active_pipelines(ids: list[str]):
    with open(_ACTIVE_PIPELINES_FILE, "w", encoding="utf-8") as f:
        json.dump(ids, f)


def _pipeline_retrieve(pid: str, query: str, k: int = 5):
    """Apply pipeline-specific retrieval strategy to the shared INDEX."""
    cfg = PIPELINE_PRESETS[pid]
    t0 = time.monotonic()
    timing = {"pipeline": pid}

    fetch_k = k * 3 if (cfg["rerank"] or cfg["dedup"]) else k

    routing = None
    if cfg["query_routing"]:
        routing = ROUTER.route(query)
        routed_k = routing.config.get("top_k", k)
        fetch_k = max(fetch_k, routed_k * 2)
        timing["intent"] = routing.intent.value
        timing["intent_confidence"] = round(routing.confidence, 2)

    results, search_timing = INDEX.search_timed(query, k=fetch_k)
    timing.update(search_timing)

    if cfg["corrective_rag"] and results:
        chunk_dicts = [
            {"text": r.chunk.text, "score": r.score,
             "source_url": r.chunk.source_url, "page_title": r.chunk.page_title}
            for r in results
        ]
        crag = CorrectiveRAG(
            retrieve_fn=lambda q, kk: [
                {"text": r.chunk.text, "score": r.score}
                for r in INDEX.search(q, k=kk)
            ],
        )
        grade, confidence = crag._grade(query, chunk_dicts)
        timing["crag_grade"] = grade.value
        timing["crag_confidence"] = round(confidence, 3)

    if cfg["rerank"] and results:
        texts = [r.chunk.text for r in results]
        reranked_texts, _ = RERANKER.rerank(query, texts, top_k=k, return_scores=True)
        text_to_result = {r.chunk.text: r for r in results}
        results = [text_to_result[t] for t in reranked_texts if t in text_to_result]
    else:
        results = results[:k]

    timing["total_ms"] = round((time.monotonic() - t0) * 1000, 1)
    return results, timing


def _pipeline_build_context(pid: str, query: str, k: int = 5, threshold: float = 0.15):
    """Build RAG context for one pipeline."""
    results, timing = _pipeline_retrieve(pid, query, k)
    strong = [r for r in results if r.score >= threshold]
    timing["filtered_weak"] = len(results) - len(strong)

    parts, sources = [], []
    total_chars = 0
    for r in strong:
        chunk_str = f"[{r.chunk.page_title}] ({r.chunk.source_url})\n{r.chunk.text}"
        if total_chars + len(chunk_str) > 4800:
            break
        parts.append(chunk_str)
        total_chars += len(chunk_str)
        sources.append({"title": r.chunk.page_title, "url": r.chunk.source_url, "score": round(r.score, 4)})

    timing["chunks_sent"] = len(sources)
    return "\n\n---\n\n".join(parts), sources, timing


def _trim_history(messages: list, budget_chars: int = 8000) -> list:
    """Trim chat history to fit token budget, keeping most recent messages."""
    trimmed = []
    total = 0
    for m in reversed(messages):
        mc = len(m.get("content", ""))
        if total + mc > budget_chars:
            break
        trimmed.insert(0, m)
        total += mc
    if not trimmed and messages:
        trimmed = [messages[-1]]
    return trimmed


# ── LLM config (any OpenAI-compatible API) ────────────────────────────────
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "ollama")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.2")
LLM_CONFIG_FILE = Path("llm_config.json")


def _load_llm_config() -> dict:
    """Load persisted LLM config (overrides env vars via UI)."""
    if LLM_CONFIG_FILE.exists():
        try:
            with open(LLM_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Corrupt llm_config.json — using defaults")
    return {}


def _save_llm_config(cfg: dict):
    with open(LLM_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def _get_llm_settings() -> dict:
    """Return effective LLM settings (file overrides > env vars > defaults)."""
    cfg = _load_llm_config()
    return {
        "base_url": cfg.get("base_url") or LLM_BASE_URL,
        "api_key": cfg.get("api_key") or LLM_API_KEY,
        "model": cfg.get("model") or LLM_MODEL,
        "system_prompt": cfg.get("system_prompt", ""),
    }

# ── crawl state (shared across threads) ───────────────────────────────────
_crawl_lock = threading.Lock()
_crawl_status: dict = {"running": False, "progress": []}
_crawl_cancel = threading.Event()

# ── site list persistence ────────────────────────────────────────────────

def _load_sites() -> list[dict]:
    if SITES_FILE.exists():
        try:
            with open(SITES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError, OSError):
            logger.warning("Corrupt sites.json — returning empty list")
    return []


def _save_sites(sites: list[dict]):
    with open(SITES_FILE, "w", encoding="utf-8") as f:
        json.dump(sites, f, ensure_ascii=False, indent=2)


# ── routes ────────────────────────────────────────────────────────────────

@app.get("/")
def ui():
    resp = make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


# --- Sites CRUD ---

@app.get("/api/sites")
def get_sites():
    return jsonify(_load_sites())


@app.post("/api/sites")
def add_site():
    data = request.get_json(force=True)
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "url is required"}), 400
    # Auto-prepend https:// if no scheme provided
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        depth = max(1, min(int(data.get("depth", 2)), 10))
        max_pages = max(1, min(int(data.get("max_pages", 50)), 5000))
    except (ValueError, TypeError):
        return jsonify({"error": "depth and max_pages must be integers"}), 400

    sites = _load_sites()
    # prevent exact duplicate
    if any(s["url"] == url for s in sites):
        return jsonify({"error": "URL already exists"}), 409

    entry = {
        "url": url,
        "depth": depth,
        "max_pages": max_pages,
        "added": time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_crawled": None,
        "pages_crawled": 0,
        "chunks_indexed": 0,
    }
    sites.append(entry)
    _save_sites(sites)
    return jsonify(entry), 201


@app.delete("/api/sites")
def remove_site():
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    sites = _load_sites()
    sites = [s for s in sites if s["url"] != url]
    _save_sites(sites)
    return jsonify({"ok": True})


# --- Pipeline Management ---

@app.get("/api/pipelines")
def get_pipelines():
    active = _load_active_pipelines()
    return jsonify([
        {
            "id": pid,
            "label": cfg["label"],
            "desc": cfg["desc"],
            "color": cfg["color"],
            "active": pid in active,
            "features": {k: v for k, v in cfg.items() if k not in ("label", "desc", "color")},
        }
        for pid, cfg in PIPELINE_PRESETS.items()
    ])


@app.post("/api/pipelines/active")
def set_active_pipelines():
    data = request.get_json(force=True)
    ids = [pid for pid in data.get("pipelines", []) if pid in PIPELINE_PRESETS]
    if not ids:
        return jsonify({"error": "At least one pipeline required"}), 400
    _save_active_pipelines(ids[:4])
    return jsonify({"active": ids[:4]})


# --- Crawl & Index ---

@app.post("/api/crawl")
def start_crawl():
    """Crawl all sites (or one if ?url= given) and index results."""
    with _crawl_lock:
        if _crawl_status["running"]:
            return jsonify({"error": "Crawl already running"}), 409
        _crawl_status.clear()
        _crawl_status.update({"running": True, "progress": []})
        _crawl_cancel.clear()

    target_url = request.args.get("url")
    sites = _load_sites()
    if target_url:
        sites = [s for s in sites if target_url in s["url"] or s["url"] in target_url]

    def _run():
        try:
            all_sites = _load_sites()  # reload for update
            for site in sites:
                if _crawl_cancel.is_set():
                    _crawl_status["progress"].append(
                        {"url": "", "status": "cancelled", "error": "Cancelled by user"})
                    break
                # Remove only this site's old chunks (not everything)
                INDEX.remove_by_source(site["url"])
                prog = {
                    "url": site["url"], "status": "crawling", "pages": 0, "chunks": 0,
                }
                _crawl_status["progress"].append(prog)

                # Live progress callback — updates page count as pages are fetched
                def _on_page(cr, _p=prog):
                    if not cr.error:
                        _p["pages"] = _p.get("pages", 0) + 1

                results, stats = crawl_site(
                    site["url"],
                    max_depth=site.get("depth", 2),
                    max_pages=site.get("max_pages", 50),
                    on_page=_on_page,
                    cancel_event=_crawl_cancel,
                )
                # chunk all pages
                all_chunks = []
                for r in results:
                    if r.error:
                        continue
                    all_chunks.extend(chunk_text(r.text, source_url=r.url, page_title=r.title))
                prog["chunks"] = len(all_chunks)  # live update before dedup
                chunks_before_dedup = len(all_chunks)

                # 5-tier smart deduplication before indexing
                if all_chunks:
                    chunk_dicts = [
                        {"text": c.text, "source_url": c.source_url,
                         "page_title": c.page_title, "chunk_idx": c.chunk_idx,
                         "char_offset": c.char_offset}
                        for c in all_chunks
                    ]
                    dedup_result = DEDUPER.deduplicate(chunk_dicts)
                    dedup_stats = dedup_result.stats
                    all_chunks = [
                        Chunk(**d) for d in dedup_result.unique_chunks
                    ]
                    logger.info(
                        "Dedup: %d→%d chunks (removed %d dupes)",
                        dedup_stats.total_input, dedup_stats.total_output,
                        dedup_stats.total_removed,
                    )
                    METRICS.record("dedup_removed", dedup_stats.total_removed)

                n_added = INDEX.add_chunks(all_chunks) if all_chunks else 0
                SEARCH_CACHE.invalidate()  # new data → invalidate cache

                # update site record
                for s in all_sites:
                    if s["url"] == site["url"]:
                        s["last_crawled"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        s["pages_crawled"] = stats.pages_fetched
                        s["chunks_indexed"] = n_added

                _crawl_status["progress"][-1].update({
                    "status": "done",
                    "pages": stats.pages_fetched,
                    "chunks": n_added,
                    "errors": stats.pages_errored,
                    "skipped": stats.pages_skipped,
                    "urls_visited": stats.urls_visited,
                    "content_types": stats.content_types,
                    "total_chars": stats.total_chars,
                    "dedup_removed": chunks_before_dedup - n_added,
                    "elapsed": stats.elapsed_sec,
                })
            _save_sites(all_sites)
            INDEX.save()
        except Exception as exc:
            logger.exception("Crawl failed")
            _crawl_status["progress"].append({"error": str(exc)})
        finally:
            with _crawl_lock:
                _crawl_status["running"] = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"started": True, "sites": len(sites)})


@app.get("/api/crawl/status")
def crawl_status():
    return jsonify(_crawl_status)


@app.post("/api/crawl/cancel")
def cancel_crawl():
    """Cancel a running crawl."""
    _crawl_cancel.set()
    with _crawl_lock:
        _crawl_status["running"] = False
    return jsonify({"ok": True})


# --- Search ---

@app.post("/api/search")
def search():
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400
    try:
        k = max(1, min(int(data.get("k", 5)), 20))
    except (ValueError, TypeError):
        return jsonify({"error": "k must be an integer"}), 400

    t0 = time.monotonic()

    # Route the query for intent-specific config
    routing = ROUTER.route(query)
    routed_k = routing.config.get("top_k", k)
    effective_k = max(k, routed_k)

    # Check cache first
    cached = SEARCH_CACHE.get_context(query)
    if cached is not None:
        elapsed = round(time.monotonic() - t0, 4)
        METRICS.record("search_ms", elapsed * 1000)
        METRICS.increment("search_cache_hits")
        return jsonify({**cached, "elapsed_sec": elapsed, "cache_hit": True})

    results = INDEX.search(query, k=effective_k)

    # Rerank results for better relevance
    if results and routing.config.get("rerank", True):
        texts = [r.chunk.text for r in results]
        reranked_texts, rerank_scores = RERANKER.rerank(query, texts, top_k=k, return_scores=True)
        # Rebuild results in reranked order
        text_to_result = {r.chunk.text: r for r in results}
        results = [text_to_result[t] for t in reranked_texts if t in text_to_result]
    else:
        results = results[:k]

    elapsed = round(time.monotonic() - t0, 4)
    METRICS.record("search_ms", elapsed * 1000)
    METRICS.increment("search_total")

    response_data = {
        "query": query,
        "k": k,
        "elapsed_sec": elapsed,
        "intent": routing.intent.value,
        "intent_confidence": round(routing.confidence, 2),
        "results": [
            {
                "text": r.chunk.text[:500],
                "source_url": r.chunk.source_url,
                "page_title": r.chunk.page_title,
                "score": round(r.score, 4),
                "chunk_idx": r.chunk.chunk_idx,
            }
            for r in results
        ],
    }

    # Cache the results
    SEARCH_CACHE.put_context(query, response_data)

    return jsonify(response_data)


# --- Index stats ---

@app.get("/api/stats")
def stats():
    base = INDEX.stats
    base["reranker"] = RERANKER.get_stats()
    base["cache"] = SEARCH_CACHE.get_stats()
    base["metrics"] = METRICS.snapshot_all()
    return jsonify(base)


@app.post("/api/clear")
def clear_index():
    INDEX.clear()
    SEARCH_CACHE.invalidate()
    METRICS.reset()
    return jsonify({"ok": True})


@app.post("/api/load")
def load_index():
    """Load persisted index from disk."""
    INDEX.load()
    return jsonify({"loaded": INDEX.n_chunks, "stats": INDEX.stats})


# --- Chat with RAG ---

# --- Model Hub (download/search/manage GGUF models) ---

@app.get("/api/models/catalog")
def models_catalog():
    """Return curated model catalog with download status."""
    tier = request.args.get("tier")
    tag = request.args.get("tag")
    catalog = MODEL_HUB.catalog(tier=tier, tag=tag)
    for m in catalog:
        m["downloaded"] = MODEL_HUB.is_downloaded(m["filename"])
    return jsonify(catalog)


@app.get("/api/models/local")
def models_local():
    """List locally available GGUF models."""
    return jsonify(MODEL_HUB.list_local())


@app.get("/api/models/recommend")
def models_recommend():
    """Recommend models based on system RAM."""
    import psutil
    ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    return jsonify({
        "ram_gb": round(ram_gb, 1),
        "models": MODEL_HUB.recommend(ram_gb=ram_gb),
    })


@app.post("/api/models/download")
def models_download():
    """Download a model. SSE stream with progress events.

    Body: {"catalog_id": "llama-3.2-3b"}
      OR: {"repo_id": "bartowski/...", "filename": "model.gguf"}
    """
    data = request.get_json(force=True)
    catalog_id = data.get("catalog_id")
    repo_id = data.get("repo_id")
    filename = data.get("filename")

    def generate():
        if catalog_id:
            gen = MODEL_HUB.download_catalog(catalog_id)
        elif repo_id and filename:
            gen = MODEL_HUB.download(repo_id, filename)
        else:
            yield f"data: {json.dumps({'status': 'error', 'error': 'catalog_id or repo_id+filename required'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        for event in gen:
            yield f"data: {json.dumps(event.to_dict())}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/models/downloads/active")
def models_downloads_active():
    """Check status of active downloads."""
    return jsonify(MODEL_HUB.active_downloads)


@app.delete("/api/models/<filename>")
def models_delete(filename: str):
    """Delete a local model file."""
    if not filename.endswith(".gguf"):
        return jsonify({"error": "Only .gguf files can be deleted"}), 400
    ok = MODEL_HUB.delete_model(filename)
    return jsonify({"deleted": ok, "filename": filename})


@app.get("/api/models/search")
def models_search():
    """Search HuggingFace for GGUF models."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter required"}), 400
    try:
        limit = min(int(request.args.get("limit", 20)), 50)
    except (ValueError, TypeError):
        return jsonify({"error": "limit must be an integer"}), 400
    results = MODEL_HUB.search_hf(query, limit=limit)
    return jsonify(results)


@app.get("/api/models/repo/<path:repo_id>")
def models_repo_files(repo_id: str):
    """List GGUF files in a HuggingFace repo."""
    files = MODEL_HUB.list_repo_files(repo_id)
    return jsonify({"repo_id": repo_id, "files": files})


# --- Local LLM (llama-server) management ---

@app.get("/api/llm/binary")
def llm_binary():
    """Check if llama-server binary is available."""
    binary = find_llama_server_binary()
    return jsonify({"found": binary is not None, "path": binary})


@app.get("/api/llm/models")
def llm_models():
    """List available .gguf models on disk."""
    models = discover_models()
    default = pick_default_model(models)
    return jsonify({
        "models": models,
        "default": default["path"] if default else None,
    })


@app.post("/api/llm/server/start")
def llm_start():
    """Start llama-server with a chosen model + optimization flags."""
    data = request.get_json(force=True)
    model_path = data.get("model_path", "")
    try:
        port = int(data.get("port", 8090))
        gpu_layers = int(data.get("gpu_layers", -1))
        ctx_size = int(data.get("ctx_size", 4096))
    except (ValueError, TypeError):
        return jsonify({"error": "port, gpu_layers, ctx_size must be integers"}), 400

    # Optimization flags (defaults match llama_server.py optimized defaults)
    kv_cache_type_k = data.get("kv_cache_type_k", "q8_0")
    kv_cache_type_v = data.get("kv_cache_type_v", "q8_0")
    flash_attn = data.get("flash_attn", "on")
    mlock = bool(data.get("mlock", True))
    cont_batching = bool(data.get("cont_batching", True))
    try:
        cache_reuse = int(data.get("cache_reuse", 256))
        slot_prompt_similarity = float(data.get("slot_prompt_similarity", 0.5))
    except (ValueError, TypeError):
        return jsonify({"error": "cache_reuse must be int, slot_prompt_similarity must be float"}), 400

    if not model_path:
        # Auto-pick default
        models = discover_models()
        default = pick_default_model(models)
        if not default:
            return jsonify({"error": "No .gguf models found"}), 404
        model_path = default["path"]

    def _start():
        try:
            LLAMA.start(
                model_path,
                port=port,
                gpu_layers=gpu_layers,
                ctx_size=ctx_size,
                kv_cache_type_k=kv_cache_type_k,
                kv_cache_type_v=kv_cache_type_v,
                flash_attn=flash_attn,
                mlock=mlock,
                cont_batching=cont_batching,
                cache_reuse=cache_reuse,
                slot_prompt_similarity=slot_prompt_similarity,
            )
            # Auto-configure LLM settings to point at local server
            cfg = _load_llm_config()
            cfg["base_url"] = LLAMA.base_url
            cfg["api_key"] = "none"
            cfg["model"] = LLAMA.model_name
            _save_llm_config(cfg)
            logger.info("LLM config auto-set to local llama-server")
        except Exception as exc:
            logger.exception("Failed to start llama-server")

    # Start in thread so the HTTP response returns immediately
    threading.Thread(target=_start, daemon=True).start()
    return jsonify({"starting": True, "model": os.path.basename(model_path), "port": port})


@app.post("/api/llm/server/stop")
def llm_stop():
    """Stop llama-server."""
    return jsonify(LLAMA.stop())


@app.get("/api/llm/server/status")
def llm_status():
    """Current llama-server status."""
    return jsonify(LLAMA.status())


# --- Chat with RAG ---
@app.get("/api/llm/config")
def get_llm_config():
    return jsonify(_get_llm_settings())


@app.post("/api/llm/config")
def set_llm_config():
    data = request.get_json(force=True)
    cfg = _load_llm_config()
    for key in ("base_url", "api_key", "model", "system_prompt"):
        if key in data and data[key] is not None:
            cfg[key] = data[key].strip()
    _save_llm_config(cfg)
    return jsonify({"ok": True})


@app.get("/api/llm/health")
def llm_health():
    """Quick LLM connectivity check (< 3 s timeout)."""
    llm = _get_llm_settings()
    api_url = llm["base_url"].rstrip("/") + "/models"
    try:
        r = http_requests.get(api_url, timeout=3,
                              headers={"Authorization": f"Bearer {llm['api_key']}"})
        r.raise_for_status()
        return jsonify({"ok": True, "base_url": llm["base_url"], "model": llm["model"]})
    except Exception as exc:
        return jsonify({
            "ok": False,
            "base_url": llm["base_url"],
            "error": _friendly_llm_error(exc),
        })


def _friendly_llm_error(exc: Exception) -> str:
    """Turn a raw requests/connection exception into a short human message."""
    msg = str(exc)
    if "ConnectionRefusedError" in msg or "10061" in msg:
        return "LLM server is not running. Start it in Settings or configure a remote endpoint."
    if "MaxRetryError" in msg or "Max retries" in msg:
        return "Cannot reach LLM server — is the URL correct?"
    if "Timeout" in msg or "timed out" in msg:
        return "LLM server timed out — it may be loading a model."
    if "401" in msg or "403" in msg:
        return "Authentication failed — check your API key."
    if "404" in msg:
        return "LLM endpoint not found — check the Base URL."
    return f"LLM error: {msg[:150]}"


@app.post("/api/chat")
def chat():
    """Chat endpoint. Retrieves RAG context, sends to LLM, streams response.

    Advanced RAG pipeline (zen_core_libs):
      1. QueryRouter classifies intent → adjusts retrieval strategy
      2. ZeroWasteCache checks for cached answer
      3. CorrectiveRAG grades retrieval, auto-corrects if weak
      4. Reranker re-orders results by relevance
      5. Score threshold + token budget filtering
      6. Chat history trimming
      7. HallucinationDetector checks LLM output (post-stream)
      8. MetricsTracker records latency / cache hits
    """
    data = request.get_json(force=True)
    messages = data.get("messages", [])
    if not messages:
        return jsonify({"error": "messages required"}), 400

    try:
        rag_k = int(data.get("rag_k", 5))
        rag_score_threshold = float(data.get("rag_score_threshold", 0.15))  # filter weak matches
    except (ValueError, TypeError):
        return jsonify({"error": "rag_k must be int, rag_score_threshold must be float"}), 400
    llm = _get_llm_settings()

    t_chat_start = time.monotonic()

    # ── Token budget constants (1 token ≈ 4 chars) ──
    CTX_BUDGET = 3072       # total token budget for system+RAG+history
    RAG_TOKEN_BUDGET = 1200 # max tokens allocated to RAG context
    CHARS_PER_TOKEN = 4     # rough estimate

    # Get last user message for RAG retrieval
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "")
            break

    # Route the query for intent-specific config
    routing = ROUTER.route(last_user_msg) if last_user_msg else None
    routed_k = routing.config.get("top_k", rag_k) if routing else rag_k
    effective_k = max(rag_k, routed_k)

    # Check answer cache
    cached_answer = SEARCH_CACHE.get_answer(last_user_msg) if last_user_msg else None
    if cached_answer is not None:
        METRICS.increment("chat_cache_hits")

    # Retrieve RAG context with score-based filtering
    rag_context = ""
    rag_sources = []
    rag_timing = {}
    rag_filtered = 0
    crag_info = {}
    if last_user_msg and INDEX.is_built:
        results, rag_timing = INDEX.search_timed(last_user_msg, k=effective_k)

        # CorrectiveRAG: grade retrieval quality, auto-correct if needed
        if results:
            chunk_dicts = [
                {"text": r.chunk.text, "score": r.score,
                 "source_url": r.chunk.source_url, "page_title": r.chunk.page_title}
                for r in results
            ]
            crag = CorrectiveRAG(
                retrieve_fn=lambda q, k: [
                    {"text": r.chunk.text, "score": r.score}
                    for r in INDEX.search(q, k=k)
                ],
            )
            grade, confidence = crag._grade(last_user_msg, chunk_dicts)
            crag_info = {"grade": grade.value, "confidence": round(confidence, 3)}
            rag_timing["crag_grade"] = grade.value
            rag_timing["crag_confidence"] = round(confidence, 3)

        # Rerank results if routing recommends it
        if results and (routing is None or routing.config.get("rerank", True)):
            texts = [r.chunk.text for r in results]
            reranked_texts, _ = RERANKER.rerank(
                last_user_msg, texts, top_k=effective_k, return_scores=True,
            )
            text_to_result = {r.chunk.text: r for r in results}
            results = [text_to_result[t] for t in reranked_texts if t in text_to_result]

        if results:
            # Filter by score threshold — skip low-relevance chunks
            strong = [r for r in results if r.score >= rag_score_threshold]
            rag_filtered = len(results) - len(strong)

            # Budget-cap RAG context
            parts = []
            total_chars = 0
            max_rag_chars = RAG_TOKEN_BUDGET * CHARS_PER_TOKEN
            for r in strong:
                chunk_text_str = f"[{r.chunk.page_title}] ({r.chunk.source_url})\n{r.chunk.text}"
                if total_chars + len(chunk_text_str) > max_rag_chars:
                    break  # stop adding more chunks
                parts.append(chunk_text_str)
                total_chars += len(chunk_text_str)
                rag_sources.append({
                    "title": r.chunk.page_title,
                    "url": r.chunk.source_url,
                    "score": round(r.score, 4),
                })
            rag_context = "\n\n---\n\n".join(parts)

    # Add compression stats to rag_timing
    rag_timing["rag_filtered_weak"] = rag_filtered
    rag_timing["rag_chunks_sent"] = len(rag_sources)
    rag_timing["rag_context_chars"] = len(rag_context)
    rag_timing["rag_context_est_tokens"] = len(rag_context) // CHARS_PER_TOKEN
    if routing:
        rag_timing["query_intent"] = routing.intent.value
        rag_timing["intent_confidence"] = round(routing.confidence, 2)

    # Build system prompt
    system_parts = []
    if llm["system_prompt"]:
        system_parts.append(llm["system_prompt"])
    else:
        system_parts.append(
            "You are a helpful assistant. Always respond in the same language as the user's question. "
            "Answer questions based on the provided context. "
            "If the context doesn't contain the answer, say so honestly. "
            "Always cite your sources when using the retrieved context."
        )
    if rag_context:
        system_parts.append(f"\n\n## Retrieved Context\n\n{rag_context}")

    system_msg = {"role": "system", "content": "\n".join(system_parts)}

    # ── Chat history compression ──
    # Keep the most recent turns that fit within remaining token budget
    system_tokens = len(system_msg["content"]) // CHARS_PER_TOKEN
    remaining = CTX_BUDGET - system_tokens
    trimmed_messages = []
    total_msg_chars = 0
    for m in reversed(messages):
        mc = len(m.get("content", ""))
        if total_msg_chars + mc > remaining * CHARS_PER_TOKEN:
            break
        trimmed_messages.insert(0, m)
        total_msg_chars += mc

    # Always keep at least the last message
    if not trimmed_messages and messages:
        trimmed_messages = [messages[-1]]

    history_trimmed = len(messages) - len(trimmed_messages)
    rag_timing["history_trimmed"] = history_trimmed
    rag_timing["history_sent"] = len(trimmed_messages)

    def generate():
        full_response = []   # collect for hallucination check
        try:
            api_url = llm["base_url"].rstrip("/") + "/chat/completions"
            resp = http_requests.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {llm['api_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": llm["model"],
                    "messages": [system_msg] + trimmed_messages,
                    "stream": True,
                    "temperature": 0.3,
                    "max_tokens": 2048,
                },
                stream=True,
                timeout=120,
            )
            resp.raise_for_status()

            # Yield sources + RAG timing first
            yield f"data: {json.dumps({'sources': rag_sources, 'rag_timing': rag_timing})}\n\n"

            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        full_response.append(content)
                        yield f"data: {json.dumps({'content': content})}\n\n"
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

            # Hallucination detection on full response
            answer_text = "".join(full_response)
            if answer_text and rag_context:
                h_report = HALLUCINATION_DETECTOR.detect(answer_text, rag_context)
                hallucination_info = {
                    "score": round(h_report.score, 2),
                    "has_hallucinations": h_report.has_hallucinations,
                    "findings": [
                        {"type": f.type.value, "severity": round(f.severity, 2),
                         "text": f.text[:100], "explanation": f.explanation[:200]}
                        for f in h_report.findings[:5]
                    ],
                }
                yield f"data: {json.dumps({'hallucination': hallucination_info})}\n\n"
                METRICS.record("hallucination_score", h_report.score)

            # Cache the answer for future requests
            if answer_text and last_user_msg:
                SEARCH_CACHE.put_answer(last_user_msg, answer_text)

            # Record metrics
            chat_ms = round((time.monotonic() - t_chat_start) * 1000, 1)
            METRICS.record("chat_ms", chat_ms)
            METRICS.increment("chat_total")

            yield "data: [DONE]\n\n"

        except Exception as exc:
            logger.exception("Chat LLM error")
            yield f"data: {json.dumps({'error': _friendly_llm_error(exc)})}\n\n"
            yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- Multi-Pipeline Comparison Chat ---

@app.post("/api/chat/compare")
def chat_compare():
    """Fan-out same question to all active pipelines, stream interleaved."""
    data = request.get_json(force=True)
    messages = data.get("messages", [])
    if not messages:
        return jsonify({"error": "messages required"}), 400

    active_ids = _load_active_pipelines()
    llm = _get_llm_settings()
    try:
        rag_k = int(data.get("rag_k", 5))
    except (ValueError, TypeError):
        return jsonify({"error": "rag_k must be an integer"}), 400

    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = m["content"]
            break

    # Build per-pipeline RAG context (local, fast)
    pipeline_data = {}
    for pid in active_ids:
        if INDEX.is_built:
            ctx, sources, timing = _pipeline_build_context(pid, last_user_msg, k=rag_k)
        else:
            ctx, sources, timing = "", [], {"pipeline": pid, "total_ms": 0}

        sp = llm.get("system_prompt", "")
        sys_text = sp if sp else (
            "You are a helpful assistant. Always respond in the same language as the user's question. "
            "Answer based on the provided context. "
            "If the context doesn't contain the answer, say so."
        )
        if ctx:
            sys_text += f"\n\n## Retrieved Context\n\n{ctx}"

        pipeline_data[pid] = {
            "system_msg": {"role": "system", "content": sys_text},
            "sources": sources,
            "timing": timing,
        }

    trimmed = _trim_history(messages)
    q = queue_mod.Queue()

    def _worker(pid):
        pd = pipeline_data[pid]
        full_text = []
        t0 = time.monotonic()
        try:
            q.put({"pipeline": pid, "sources": pd["sources"], "timing": pd["timing"]})
            resp = http_requests.post(
                llm["base_url"].rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {llm['api_key']}", "Content-Type": "application/json"},
                json={
                    "model": llm["model"],
                    "messages": [pd["system_msg"]] + trimmed,
                    "stream": True, "temperature": 0.3, "max_tokens": 2048,
                },
                stream=True, timeout=120,
            )
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                    if content:
                        full_text.append(content)
                        q.put({"pipeline": pid, "content": content})
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

            answer = "".join(full_text)
            hallu = None
            cfg = PIPELINE_PRESETS[pid]
            if cfg["hallucination_check"] and answer and pd["sources"]:
                ctx_text = pd["system_msg"]["content"]
                report = HALLUCINATION_DETECTOR.detect(answer, ctx_text)
                hallu = {"score": round(report.score, 2), "has_hallucinations": report.has_hallucinations}

            q.put({
                "pipeline": pid, "done": True,
                "latency_ms": round((time.monotonic() - t0) * 1000, 1),
                "answer_length": len(answer),
                "hallucination": hallu,
            })
        except Exception as e:
            q.put({"pipeline": pid, "error": _friendly_llm_error(e), "done": True})

    for pid in active_ids:
        threading.Thread(target=_worker, args=(pid,), daemon=True).start()

    def generate():
        done = 0
        total = len(active_ids)
        deadline = time.monotonic() + 180  # 3-minute total timeout
        while done < total:
            if time.monotonic() > deadline:
                yield f"data: {json.dumps({'error': 'Pipeline comparison timed out', 'done': True})}\n\n"
                break
            try:
                event = q.get(timeout=0.1)
            except queue_mod.Empty:
                continue
            if event.get("done"):
                done += 1
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Try to load persisted index on startup
    try:
        INDEX.load()
        logger.info("Loaded persisted index: %d chunks", INDEX.n_chunks)
    except (FileNotFoundError, OSError, json.JSONDecodeError, ValueError):
        logger.warning("No persisted index found — starting empty")

    # Pre-warm the embedding model in background so first chat is fast
    threading.Thread(target=warmup_embedder, daemon=True, name="emb-warmup").start()

    port = int(os.environ.get("RAG_PORT", "5050"))
    print(f"\n  RAG Test Bench -> http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
