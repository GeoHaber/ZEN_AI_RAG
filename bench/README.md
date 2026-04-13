# RAG Test Bench

> **Part of [ZEN_AI_RAG](https://github.com/GeoHaber/ZEN_AI_RAG)** — the lightweight benchmarking companion to Zena AI.

A self-contained web application for **benchmarking RAG pipelines side-by-side**.
Crawl real websites, index them with `zen_core_libs`, then run the same query through
up to four different pipeline configurations and compare answers, latency, sources,
and hallucination scores — all from a single dark-mode dashboard.

---

## Why This Exists

[ZEN_AI_RAG](https://github.com/GeoHaber/ZEN_AI_RAG) is a full-stack AI assistant
(NiceGUI + Flet UIs, 22+ SOTA RAG modules, Qdrant, local LLM server, voice, gateways).
It is designed for **production use**.

**RAG Test Bench** extracts the core RAG primitives from `zen_core_libs` into a
minimal Flask app whose _sole purpose_ is to let you **measure and compare** pipeline
configurations. Think of it as the lab bench where you tune the knobs before deploying
to the full Zena stack.

### How It Relates to ZEN_AI_RAG

| Aspect | ZEN_AI_RAG (Zena AI) | RAG Test Bench |
|--------|---------------------|----------------|
| **Purpose** | Production AI assistant | Pipeline benchmarking & A/B testing |
| **UI** | NiceGUI + Flet (desktop & web) | Single-page Flask (vanilla JS) |
| **RAG backend** | Qdrant + BM25 + `rag_core` lib | `zen_core_libs[rag]` in-memory index |
| **LLM** | In-process llama-cpp + 7 cloud adapters | Any OpenAI-compatible API (local or cloud) |
| **Modules shared** | 22+ Core/ modules | Subset via zen_core_libs: Dedup, Rerank, QueryRouter, Cache, Corrective RAG, Hallucination Detector, Metrics |
| **Pipelines** | Single enhanced pipeline (adaptive routing) | 4 named presets run **in parallel** for comparison |
| **Footprint** | ~200 files, ~50 dependencies | 2 Python files + 1 HTML template, 7 dependencies |

Both share the same underlying RAG primitives — `zen_core_libs` packages the
algorithms that ZEN_AI_RAG's `Core/` modules implement, making RAG Test Bench a
focused, lightweight harness to test them.

---

## Quick Start

```bash
cd rag-test-bench
pip install -r requirements.txt
python app.py
# → http://localhost:5050
```

That's it. The UI opens in three phases: **Setup → Crawl → Chat**.

---

## What It Does

### Phase 1 — Setup

Add one or more website URLs with configurable crawl depth (1–10) and a max-pages cap.
Select which pipeline presets to activate (see [Pipelines](#pipelines) below).

### Phase 2 — Crawl & Index

Click **Start Crawl**. The BFS crawler (`crawler.py`) fetches pages, strips boilerplate,
and hands clean text to the indexing pipeline:

```
Pages  →  chunk_text()  →  SmartDeduplicator (5-tier)  →  RAGIndex.add()  →  persist
```

Live progress bars show pages fetched, chunks created, duplicates removed, and a
per-site crawl report when done.

### Phase 3 — Chat & Compare

Ask a question. The app runs the full advanced RAG pipeline:

```
Query
 ├─ QueryRouter  →  intent classification (SIMPLE / ANALYTICAL / MULTI_HOP / …)
 ├─ ZeroWasteCache  →  cache hit? return instantly
 ├─ RAGIndex.search()  →  top-K retrieval
 ├─ CorrectiveRAG  →  grade chunks (CORRECT / AMBIGUOUS / INCORRECT)
 ├─ Reranker  →  re-score survivors
 ├─ Token-budget filter  →  fit within context window
 ├─ Chat-history compression  →  keep conversation within limits
 ├─ LLM streaming  →  SSE tokens to browser
 ├─ HallucinationDetector  →  post-check the answer
 └─ MetricsTracker  →  log latency, cache hit, chunk count
```

**Multi-pipeline comparison**: select 2–4 presets, ask the same question, and see each
pipeline's answer side-by-side with timing, sources, and hallucination risk badges.
The UI auto-detects the fastest pipeline and marks it.

---

## Pipelines

Four built-in presets with increasing sophistication:

| Preset | Rerank | Dedup | Query Routing | Hallucination Check | Corrective RAG |
|--------|:------:|:-----:|:-------------:|:-------------------:|:--------------:|
| `baseline` | — | — | — | — | — |
| `reranked` | ✓ | ✓ | — | — | — |
| `routed` | ✓ | ✓ | ✓ | — | — |
| `full_stack` | ✓ | ✓ | ✓ | ✓ | ✓ |

Each preset is a dict of boolean flags passed through the chat pipeline.
Active presets are persisted in `active_pipelines.json`.

---

## Integrated LLM Management

RAG Test Bench includes **full llama-server lifecycle management** — you can
download models, start/stop a local LLM, and configure the API, all from the UI:

- **Model Hub** — browse a curated catalog, discover local GGUF models, search
  HuggingFace, download with SSE progress bars
- **Local LLM** — auto-detect `llama-server` binary, start with GPU offload,
  monitor status, stop
- **LLM Config** — set base URL / API key / model for any OpenAI-compatible
  endpoint (Ollama, llama-server, OpenAI, etc.)
- **Health Check** — real-time connectivity test with friendly error messages

---

## Architecture

```
rag-test-bench/
├── app.py              Flask app — 29 API endpoints, chat pipeline, SSE streaming
├── crawler.py          BFS web crawler — same-domain, robots.txt-aware, cancelable
├── templates/
│   └── index.html      Single-page UI — dark/light theme, i18n (6 languages),
│                        pipeline selector, Model Hub, streaming chat, comparison grid
├── static/             (empty — everything is inlined in index.html)
├── conftest.py         pytest markers: slow, live
├── test_zen_integration.py   Unit tests — chunking, index, dedup, reranker, cache
├── test_advanced_rag.py      Unit tests — dedup, hallucination, query router, corrective RAG
├── test_optimizations.py     Unit tests — llama-server flags, KV cache, chat compression
├── test_e2e.py               40 mocked e2e tests — full user journey with fake data
├── test_live_e2e.py          18 live e2e tests — real crawl, real embedder, real LLM
├── test_crawl.py             Manual crawl smoke test
├── requirements.txt          7 dependencies
├── sites.json                Persisted site list
├── active_pipelines.json     Persisted pipeline selection
├── llm_config.json           Persisted LLM endpoint config
└── index_data/               Persisted embeddings + metadata (auto-created)
```

### Dependency on `zen_core_libs`

All RAG intelligence lives in [`zen_core_libs`](https://github.com/GeoHaber/zen_core_libs)
(installed via `pip install zen-core-libs[rag]`). The app imports:

| Module | Components |
|--------|-----------|
| `zen_core_libs.rag` | `RAGIndex`, `chunk_text`, `Chunk`, `warmup`, `SmartDeduplicator`, `Reranker`, `QueryRouter`, `HallucinationDetector`, `ZeroWasteCache`, `MetricsTracker`, `HyDERetriever`, `FLARERetriever`, `CorrectiveRAG` |
| `zen_core_libs.llm` | `LlamaServerManager`, `discover_models`, `find_llama_server_binary`, `pick_default_model` |
| `zen_core_libs.acquire` | `ModelHub`, `MODEL_CATALOG` |

This is the same library whose algorithms power ZEN_AI_RAG's `Core/` modules.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer embedding model |
| `RAG_NBITS` | `3` | TurboQuant quantization bits |
| `RAG_CHUNK_SIZE` | `512` | Chunk size (characters) |
| `RAG_CHUNK_OVERLAP` | `64` | Overlap between adjacent chunks |
| `RAG_PORT` | `5050` | Flask server port |
| `RAG_INDEX_DIR` | `./index_data` | Persistence directory |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible API base URL |
| `LLM_API_KEY` | `ollama` | API key (use any string for local servers) |
| `LLM_MODEL` | `llama3.2` | Default model name for chat |

---

## API Reference

### Sites

| Method | Path | Body / Params | Description |
|--------|------|---------------|-------------|
| GET | `/api/sites` | — | List all sites |
| POST | `/api/sites` | `{url, depth, max_pages}` | Add a site |
| DELETE | `/api/sites` | `{url}` | Remove a site |

### Crawl

| Method | Path | Body / Params | Description |
|--------|------|---------------|-------------|
| POST | `/api/crawl` | `?url=` (optional, single site) | Start crawl |
| GET | `/api/crawl/status` | — | Poll progress (pages, chunks, errors per site) |
| POST | `/api/crawl/cancel` | — | Cancel running crawl |

### Search & Index

| Method | Path | Body / Params | Description |
|--------|------|---------------|-------------|
| POST | `/api/search` | `{query, k}` | Search with query routing + reranking |
| GET | `/api/stats` | — | Index statistics (n_chunks, memory, compression) |
| POST | `/api/clear` | — | Clear index |
| POST | `/api/load` | — | Reload persisted index from disk |

### Pipelines

| Method | Path | Body / Params | Description |
|--------|------|---------------|-------------|
| GET | `/api/pipelines` | — | List all presets with feature flags |
| GET | `/api/pipelines/active` | — | Currently active presets |
| POST | `/api/pipelines/active` | `{pipelines: [...]}` | Set active presets |

### Chat

| Method | Path | Body / Params | Description |
|--------|------|---------------|-------------|
| POST | `/api/chat` | `{messages, pipeline?, rag_k?}` | SSE streaming chat (single pipeline) |
| POST | `/api/chat/compare` | `{messages}` | SSE streaming comparison (all active pipelines) |

### LLM Management

| Method | Path | Body / Params | Description |
|--------|------|---------------|-------------|
| GET | `/api/llm/config` | — | Current LLM endpoint config |
| POST | `/api/llm/config` | `{base_url, api_key, model}` | Update LLM config |
| GET | `/api/llm/health` | — | Test LLM connectivity |
| GET | `/api/llm/binary` | — | Check for llama-server binary |
| GET | `/api/llm/models` | — | Discover local GGUF models |
| POST | `/api/llm/server/start` | `{model, gpu_layers?}` | Start local llama-server |
| POST | `/api/llm/server/stop` | — | Stop local llama-server |
| GET | `/api/llm/server/status` | — | Server running status |

### Model Hub

| Method | Path | Body / Params | Description |
|--------|------|---------------|-------------|
| GET | `/api/models/catalog` | — | Curated model catalog |
| GET | `/api/models/local` | — | Locally available models |
| GET | `/api/models/recommend` | — | Hardware-matched recommendation |
| POST | `/api/models/download` | `{repo_id, filename}` | SSE download with progress |
| DELETE | `/api/models/<name>` | — | Delete a downloaded model |
| GET | `/api/models/hf/search?q=` | — | Search HuggingFace |
| GET | `/api/models/hf/files?repo_id=` | — | List files in HF repo |

---

## Tests

### Test Suites (212 total)

| Suite | File | Tests | What It Covers |
|-------|------|:-----:|----------------|
| Integration | `test_zen_integration.py` | 26 | Chunking, RAGIndex, dedup, reranker, cache, metrics |
| Advanced RAG | `test_advanced_rag.py` | 21 | SmartDeduplicator, HallucinationDetector, QueryRouter, CorrectiveRAG |
| Optimizations | `test_optimizations.py` | 13 | llama-server KV cache flags, command construction, chat compression |
| E2E (mocked) | `test_e2e.py` | 40 | Full user journey — fake crawler, fake embedder, fake LLM |
| E2E (live) | `test_live_e2e.py` | 18 | Real crawl (httpbin.org), real embeddings, real llama-server |

### Running Tests

```bash
# Default — fast, no network or GPU required (194 pass, 18 skip)
python -m pytest -v

# Live e2e — requires internet + llama-server + GGUF model (~3 min)
python -m pytest test_live_e2e.py -v -m live
```

Live tests auto-detect prerequisites (internet, binary, model) and skip gracefully
if anything is missing.

---

## Dependencies

```
flask>=3.0,<4.0
requests>=2.31
beautifulsoup4>=4.12
lxml>=5.0
sentence-transformers>=3.0,<4.0
numpy>=1.26
zen-core-libs[rag]
```

---

## Code Quality — X-Ray Scan (March 2026)

| Metric | Value |
|--------|-------|
| Files scanned | 10 |
| Rules checked | 42 |
| HIGH severity | 0 |
| MEDIUM severity | 1 |
| Status | Clean |

Run locally: `python -m xray . --dry-run`

## License

Same as [ZEN_AI_RAG](https://github.com/GeoHaber/ZEN_AI_RAG).
