# ZEN_AI_RAG — Zena AI with RAG & Local LLM

Full-stack AI assistant with **Retrieval-Augmented Generation**, local LLM inference via **llama-cpp**, and a NiceGUI web UI — designed to run entirely offline.

## Features

- **Local LLM inference** — llama-cpp server with auto-model discovery and GPU/CPU selection
- **RAG pipeline** — BGE embeddings, semantic chunking, Qdrant vector search, layout-aware PDF parsing
- **Enhanced RAG Pipeline** — 22+ SOTA modules with adaptive query routing (see [Core Modules](#core-modules))
- **Multi-format ingestion** — PDF, DOCX, XLSX, web pages, code files (30+ types)
- **NiceGUI UI** — dark mode, RAG badges, chat interface, settings sidebar, pipeline selector
- **Pre-flight validation** — auto-checks binary, models, and dependencies on startup
- **Multi-model support** — auto-discovers GGUF models, switch models live
- **Zena AI personality** — customizable AI assistant with enhanced capabilities
- **[RAG Test Bench](rag-test-bench/)** — lightweight Flask app for A/B testing RAG pipelines side-by-side

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Launch (auto-validates and starts llama-cpp server + NiceGUI UI)
python start_llm.py
```

Or use the batch/shell scripts:

```bash
# Windows
Run_Me.bat

# Linux/macOS
./Run_Me.sh
```

## Architecture

```
start_llm.py                     # Entry point — delegates to zena_mode/server.py
zena.py                          # NiceGUI chat application (main UI)
zena_mode/
├── server.py                    # Orchestrator: model engines, health checks, HTTP endpoints
├── rag_manager.py               # Thread-safe RAG state proxy (uses RLock)
config.py                        # Configuration management (ports, model paths, dirs)
model_manager.py                 # Model discovery and hot-swap
```

### Core Modules (Core/)

The enhanced RAG pipeline consists of 22+ industry-best modules orchestrated by `EnhancedRAGService`:

| Module | File | Description |
|--------|------|-------------|
| **Query Router** | `Core/query_router.py` | Intent classification → adaptive pipeline selection (simple/analytical/multi-hop/aggregate/temporal) |
| **Query Rewriter** | `Core/query_rewriter.py` | Multi-query expansion via LLM or templates |
| **HyDE Retrieval** | `Core/hyde_retrieval.py` | Hypothetical document embeddings for improved recall |
| **Contextual Retrieval** | `Core/contextual_retrieval.py` | Anthropic-style chunk enrichment with document context |
| **Parent Document Retrieval** | `Core/parent_document_retrieval.py` | Hierarchical small-to-big context expansion |
| **Knowledge Graph** | `Core/knowledge_graph.py` | Entity-relation graph with SQLite backend |
| **Graph RAG** | `Core/graph_rag.py` | Community detection and global/local Q&A strategies |
| **Advanced Reranker** | `Core/reranker_advanced.py` | 5-signal reranking: semantic, position, density, answer-type, source credibility |
| **Smart Deduplicator** | `Core/smart_deduplicator.py` | Multi-strategy dedup: exact, boilerplate, structural, semantic, shingle |
| **Contextual Compressor** | `Core/contextual_compressor.py` | Query-focused chunk compression to reduce noise |
| **Corrective RAG** | `Core/corrective_rag.py` | Self-healing retrieval with quality grading (CORRECT/AMBIGUOUS/INCORRECT) |
| **FLARE Retrieval** | `Core/flare_retrieval.py` | Forward-looking active retrieval for uncertain answers |
| **Conflict Detector** | `Core/conflict_detector.py` | Cross-source numerical, temporal, and factual conflict detection |
| **Hallucination Detector** | `Core/hallucination_detector_v2.py` | Multi-signal detection: ungrounded, NLI contradiction, numerical, causal |
| **Confidence Scorer** | `Core/confidence_scorer.py` | Multi-factor quality assessment with risk levels |
| **Follow-Up Generator** | `Core/follow_up_generator.py` | Context-aware follow-up question generation |
| **Answer Refinement** | `Core/answer_refinement.py` | Post-generation quality pipeline (hallucination fix, completeness, consistency) |
| **Metrics Tracker** | `Core/metrics_tracker.py` | Query/index event tracking with latency percentiles and cache hit rates |
| **Zero-Waste Cache** | `Core/zero_waste_cache.py` | Two-tier semantic cache: answer-level (T1) + context-level (T2) with fingerprint validation |
| **Inference Guard** | `Core/inference_guard.py` | Crash diagnostics, memory snapshots, performance profiling |
| **Prompt Templates** | `Core/prompt_focus.py` | 12+ built-in templates (Medical, Legal, Business, Technical, Research) with 7 focus modes |
| **Evaluation** | `Core/evaluation.py` | Answer quality (faithfulness, relevance, completeness, conciseness) + retrieval metrics (Precision@K, Recall@K, MRR, F1) |

### Pipeline Flow

```
Query → QueryRewriter → QueryRouter → [Strategy Selection]
                                         │
                    ┌────────────────────┤
                    ▼                    ▼
              Simple Path          Analytical Path
              (fast)               (full SOTA)
                    │                    │
                    ▼                    ▼
              Retrieve            HyDE + Retrieve
                    │                    │
                    └────────┬───────────┘
                             ▼
                    Parent Document Expand
                             ▼
                    Smart Deduplicator
                             ▼
                    Advanced Reranker
                             ▼
                    Conflict Detector
                             ▼
                    Contextual Compressor
                             ▼
                    Corrective RAG (CRAG)
                             ▼
                    FLARE (if uncertain)
                             ▼
                    LLM Generate Answer
                             ▼
                    Post-Processing:
                    ├── Hallucination Detection
                    ├── Confidence Scoring
                    ├── Follow-Up Generation
                    └── Metrics Recording
```

## UI Features

- **Pipeline selector**: Choose between Standard RAG and Enhanced (SOTA) pipeline
- **Live metadata display**: Routing intent, pipeline stages, latency, confidence score, hallucination probability
- **CRAG feedback**: Retrieval grade and corrections applied
- **FLARE status**: Iteration count and sub-queries generated
- **Conflict alerts**: Cross-source contradictions detected
- **Follow-up suggestions**: Context-aware next questions

## Running Tests

```bash
# All tests (uses the test runner with server lifecycle management)
python run_tests.py

# Core module tests only (94 tests, fast)
python -m pytest tests/test_core_modules.py -v

# Enhanced RAG integration tests (38 tests)
python -m pytest tests/test_enhanced_rag.py -v

# Deep audit tests — KnowledgeGraph, Pydantic models, pipeline integration (67 tests)
python -m pytest tests/test_deep_audit.py -v

# All three test suites (199 tests)
python -m pytest tests/test_core_modules.py tests/test_enhanced_rag.py tests/test_deep_audit.py -v

# With coverage
python run_tests.py --coverage
```

## Dependencies

- `llama-cpp-python` — local GGUF model inference
- `nicegui` — web UI
- `sentence-transformers` — BGE embeddings + cross-encoder reranking
- `qdrant-client` — vector database
- `beautifulsoup4`, `PyMuPDF` — document parsing
- `pydantic` — data validation for RAG models
- `psutil` — process/memory monitoring for inference guard

## Configuration

- `config.py` / `config.json` — Ports (default engine: 8001), model paths, directories
- `settings.json` — User preferences (theme, voice, RAG settings)
- `data/custom_prompts.json` — User-created prompt templates

## Code Quality — X-Ray Scan (March 2026)

| Metric | Value |
|--------|-------|
| Files scanned | 507 |
| Rules checked | 42 |
| HIGH severity | 32 (down from 36 after fixes) |
| MEDIUM severity | 514 |
| Fixes applied | SEC-003: subprocess `shell=True` → `shell=False` in utils.py, utils_hardware.py, dependency_check.py |
| Fixes applied | PORT-002: Hardcoded `C:/AI/Models` → `Path.home() / "AI" / "Models"` in server.py |
| Fixes applied | SEC-009: pickle.load annotated with integrity check comment |
| Remaining | PY-005 (json.load), SEC-007 false positives (function names containing 'eval'/'exec') |
| Status | Security-hardened |

Run locally: `python -m xray . --dry-run`

## License

MIT
