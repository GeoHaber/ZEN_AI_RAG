# Rebuild Prompt — ZEN AI RAG

> **Purpose**: A single, comprehensive prompt that a coding LLM can follow to rebuild the ZEN AI RAG application from scratch.

---

## System Prompt

You are an expert Python developer. Build a complete, production-ready **Retrieval-Augmented Generation (RAG) application** named **ZEN AI RAG**. The system runs a local LLM (llama-cpp) with a NiceGUI web UI, a management/orchestration server, and a full SOTA RAG pipeline. Follow every specification below precisely.

---

## 1. Project Structure

```
ZEN_AI_RAG/
├── start_llm.py              # Primary entrypoint (shim → server)
├── zena.py                    # NiceGUI web UI app
├── config_system.py           # AppConfig, RAGConfig, EmbeddingConfig dataclasses
├── config.py                  # Legacy bridge re-exporting BASE_DIR, MODEL_DIR, BIN_DIR
├── settings.py                # Legacy bridge re-exporting AppSettings, get_settings
├── model_manager.py           # HuggingFace model search/download
├── llm_adapters.py            # Multi-provider LLM adapters (6 providers)
├── adapter_factory.py         # Factory: create_adapter(provider, ...)
├── async_backend.py           # AsyncZenAIBackend (httpx → llama-server)
├── mock_backend.py            # MockAsyncBackend for testing
├── rag_integration.py         # High-level RAG wrapper (hybrid search, context formatting)
├── ui_state.py                # Thread-safe UIState (RLock-backed dict)
├── utils.py                   # safe_print, HardwareProfiler, prune_zombies, ProcessManager
├── voice_service.py           # Voice/TTS integration
├── state_management.py        # App state persistence
├── requirements.txt           # ~70 Python packages
├── _bin/                      # llama-server.exe and related binaries
├── models/                    # GGUF model files
├── qdrant_storage/            # Qdrant vector DB storage
├── rag_storage/               # RAG collection storage
├── rag_cache/                 # RAG cache storage
├── conversation_cache/        # Conversation history cache
│
├── Core/                      # 24 SOTA RAG modules + services
│   ├── __init__.py            # Lazy exports: models, exceptions, all modules
│   ├── models.py              # Dataclass DTOs: QueryRequest/Response, ChatMessage, etc.
│   ├── exceptions.py          # ZenAIError hierarchy (6 subclasses)
│   ├── rag_models.py          # Pydantic: ChunkPayload, RAGSearchResult, QueryRewriteResult, EvalSample
│   ├── constants.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── enhanced_rag_service.py  # Full SOTA pipeline orchestrator
│   │   ├── llm_service.py
│   │   ├── rag_service.py
│   │   ├── document_service.py
│   │   └── session_service.py
│   ├── query_rewriter.py       # Step 0: multi-query expansion
│   ├── query_router.py         # Intent classification → pipeline selection
│   ├── hyde_retrieval.py        # Hypothetical Document Embeddings
│   ├── contextual_retrieval.py  # Anthropic-style chunk enrichment
│   ├── corrective_rag.py       # Self-healing retrieval (CRAG)
│   ├── flare_retrieval.py      # Forward-Looking Active Retrieval (FLARE)
│   ├── parent_document_retrieval.py  # Small-to-big context expansion
│   ├── graph_rag.py            # Community-based global Q&A
│   ├── knowledge_graph.py      # SQLite-backed entity/triple store
│   ├── reranker_advanced.py    # CrossEncoder reranking
│   ├── smart_deduplicator.py   # 5-tier deduplication
│   ├── contextual_compressor.py # Query-aware chunk compression
│   ├── conflict_detector.py    # Cross-source conflict detection
│   ├── hallucination_detector_v2.py # NLI-based hallucination detection
│   ├── confidence_scorer.py    # Multi-signal quality assessment
│   ├── follow_up_generator.py  # Context-aware follow-up questions
│   ├── answer_refinement.py    # Async multi-stage answer refinement
│   ├── zero_waste_cache.py     # 2-tier semantic+exact cache
│   ├── prompt_focus.py         # 7 focus modes + 12 builtin prompt templates
│   ├── metrics_tracker.py      # Thread-safe singleton metrics
│   ├── evaluation.py           # AnswerEvaluator + RetrievalEvaluator
│   └── inference_guard.py      # Async context manager + crash diagnostics
│
├── ui/                         # NiceGUI UI modules (30+)
│   ├── __init__.py             # Exports: Styles, Icons, Formatters, UI_IDS
│   ├── bootstrap.py, layout.py, handlers.py, actions.py
│   ├── sidebar.py, modern_chat.py, rag_interface.py
│   ├── theme_setup.py, styles.py, dashboard.py
│   ├── model_gallery.py, settings_dialog.py
│   └── locales/                # i18n
│
├── zena_mode/                  # Server + RAG core (45+ modules)
│   ├── __init__.py             # Exports: LocalRAG, WebsiteScraper, ConversationMemory
│   ├── server.py               # Orchestrator hub + HTTP handler
│   ├── heart_and_brain.py      # ZenHeart: LLM engine lifecycle
│   ├── rag_manager.py          # Thread-safe RAG state proxy
│   ├── rag_core_bridge.py      # LocalRAGv2: chunking → embed → qdrant
│   ├── rag_pipeline.py         # RAG pipeline helpers
│   ├── rag_db.py               # SQLite RAG metadata
│   ├── scraper.py              # WebsiteScraper
│   ├── conversation_memory.py
│   ├── universal_extractor.py  # PDF, DOCX, Excel, etc.
│   ├── handlers/               # HTTP route handlers
│   │   ├── base.py, chat.py, health.py, models.py
│   │   ├── orchestration.py, static.py, swarm_chat.py, voice.py
│   ├── asgi_server.py          # FastAPI ASGI on mgmt_port
│   ├── voice_stream.py         # WebSocket voice server
│   └── ...
│
└── tests/                      # 199 functional tests
    ├── test_core_modules.py    # 94 tests: all Core RAG modules
    ├── test_enhanced_rag.py    # 38 tests: pipeline + integration
    └── test_deep_audit.py      # 67 tests: KG, Pydantic, metrics, pipeline
```

---

## 2. Configuration System (`config_system.py`)

Create three nested dataclasses:

```python
@dataclass
class EmbeddingConfig:
    models: Dict[str, str] = field(default_factory=lambda: {
        "fast": "all-MiniLM-L6-v2",
        "balanced": "all-MiniLM-L12-v2",
        "accurate": "all-mpnet-base-v2",
    })
    fallback_model: str = "all-MiniLM-L6-v2"

@dataclass
class RAGConfig:
    embedding_model: str = "all-MiniLM-L6-v2"
    use_gpu: bool = False
    chunk_strategy: str = "recursive"
    chunk_size: int = 500
    chunk_overlap: int = 50
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    max_context_chars: int = 12000
    semantic_cache_ttl: int = 3600
    similarity_threshold: float = 0.95
    contextual_retrieval: bool = True
    mmr_diversity: float = 0.3

@dataclass
class AppConfig:
    llm_port: int = 8001
    mgmt_port: int = 8002
    ui_port: int = 8080
    voice_port: int = 8003
    host: str = "127.0.0.1"
    default_model: str = "model.gguf"
    gpu_layers: int = -1
    batch_size: int = 512
    context_size: int = 4096
    SWARM_SIZE: int = 3
    SWARM_ENABLED: bool = False
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    RAG_MAX_WORKERS: int = 8
    TTS_MAX_WORKERS: int = 4
    BASE_DIR: Path = Path(__file__).parent
    BIN_DIR: str = "_bin/"
    MODEL_DIR: str = "models/"
    rag: RAGConfig = field(default_factory=RAGConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
```

Singleton pattern: `config = AppConfig()` with `load_config()` reading from `config.json`.

---

## 3. Core Models & Exceptions (`Core/models.py`, `Core/exceptions.py`)

### DTOs (dataclasses):
- `QueryRequest(query, include_sources=True, max_tokens=1024, temperature=0.7, session_id=None, metadata=None)`
- `QueryResponse(content, sources=[], status=ResponseStatus.SUCCESS, error=None, processing_time_ms=0, token_count=0)`
- `ChatMessage(role, content)`, `ChatRequest(messages, max_tokens, temperature, stream)`, `ChatResponse(content, model, usage, finish_reason)`
- `SearchRequest(query, top_k, filter)`, `SearchResult(text, url, title, score, metadata)`, `SearchResponse(results, total_found, search_time_ms)`
- `StreamRequest/StreamChunk`, `StatusResponse`
- `ResponseStatus` enum: SUCCESS, ERROR, PARTIAL

### Exceptions (hierarchy):
```python
class ZenAIError(Exception):
    def __init__(self, message, error_code=None, details=None): ...

class ConfigurationError(ZenAIError): ...
class ProviderError(ZenAIError): ...
class AuthenticationError(ZenAIError): ...
class LLMError(ZenAIError): ...
class RAGError(ZenAIError): ...
class DocumentError(ZenAIError): ...
class ValidationError(ZenAIError): ...
```

### Pydantic Models (`Core/rag_models.py`):
```python
class ChunkPayload(BaseModel):  # extra="allow"
    text: str  # min_length=1, stripped, not blank
    url: Optional[str] = None
    title: Optional[str] = None
    scan_root: Optional[str] = None
    chunk_index: int = 0  # ge=0
    is_table: bool = False
    sheet_name: Optional[str] = None
    parent_id: Optional[str] = None
    doc_type: Optional[str] = None

class RAGSearchResult(BaseModel):  # extra="allow"
    text: str  # min_length=1, stripped
    url: Optional[str] = None
    title: Optional[str] = None
    score: float = 0.0  # coerced from any type
    rerank_score: Optional[float] = None
    fusion_score: Optional[float] = None
    is_cached: bool = False
    parent_text: Optional[str] = None
    is_table: bool = False

class QueryRewriteResult(BaseModel):
    original: str
    rewrites: List[str] = []
    strategy: str = "passthrough"
    @property all_queries -> deduplicated [original] + rewrites

class EvalSample(BaseModel):
    query: str
    expected_answer: str
    retrieved_texts: List[str] = []
    generated_answer: Optional[str] = None
    relevance_scores: List[float] = []
    ndcg: Optional[float] = None
    mrr: Optional[float] = None
```

---

## 4. Enhanced RAG Pipeline (`Core/services/enhanced_rag_service.py`)

The central orchestrator. **Pipeline stages** in order:

```
1. QueryRewrite (Step 0) — expand query via templates/LLM
2. Route — classify intent → select pipeline config
3. GraphRAG — if global/multi-hop query
4. HyDE/Retrieve — hypothetical doc embeddings + standard retrieval
5. ParentDoc — expand child chunks to parent context
6. Dedup — 5-tier deduplication
7. Rerank — CrossEncoder reranking
8. ConflictDetect — cross-source conflict detection
9. Compress — query-aware context compression
10. CRAG — corrective RAG (quality grading + web fallback)
11. FLARE — forward-looking active retrieval for uncertain passages
12. Generate — LLM answer generation
13. PostProcess — hallucination check, confidence scoring, follow-ups
14. RecordMetrics — track latency, quality, cache stats
```

```python
class EnhancedRAGService:
    def __init__(self):
        self._initialized = False
        # Lazy component refs: _router, _hyde, _crag, _flare, _compressor,
        # _reranker, _deduplicator, _conflict_detector, _hallucination_detector,
        # _confidence_scorer, _follow_up_generator, _metrics_tracker,
        # _query_rewriter, _parent_retriever, _graph_rag, _knowledge_graph

    def initialize(self, retrieve_fn, generate_fn, llm_fn=None, embed_fn=None,
                   search_by_embedding_fn=None, knowledge_graph=None): ...

    def query(self, query, top_k=10, context=None, force_strategy=None) -> Dict:
        # Returns: {"answer": str, "sources": List[Dict], "metadata": Dict}
        # metadata keys: latency_ms, routing, stages, confidence, hallucination, etc.

    def _record_metrics(self, query, result, elapsed):
        # IMPORTANT: Use correct field names:
        #   QueryEvent(query=query[:200], latency_ms=round(elapsed*1000, 2),
        #              cache_hit=False, quality_score=..., hallucination_probability=...)
```

---

## 5. Core RAG Modules (24 modules)

### 5.1 QueryRewriter (`Core/query_rewriter.py`)
- `TEMPLATES`: 4 regex patterns with template expansions
- `rewrite(query) -> QueryRewriteResult` — LLM + template-based multi-query expansion
- `reciprocal_rank_fusion(result_lists, k=60) -> List[Dict]` — static RRF merger

### 5.2 QueryRouter (`Core/query_router.py`)
- Classifies intent: simple, analytical, multi_hop, aggregate, temporal, conversational
- Returns pipeline config per intent (which modules to enable)
- Confidence score for routing decision

### 5.3 HyDE Retrieval (`Core/hyde_retrieval.py`)
- Generates hypothetical document using LLM, embeds it, searches for similar real docs
- Fuses HyDE results with standard results via RRF

### 5.4 Contextual Retrieval (`Core/contextual_retrieval.py`)
- Anthropic-style: adds document-level context prefix to each chunk
- LLM-based or heuristic fallback; caching supported

### 5.5 Corrective RAG (`Core/corrective_rag.py`)
- Grades retrieval quality; if below threshold, decomposes query and re-retrieves
- Web search fallback for insufficient local results

### 5.6 FLARE Retrieval (`Core/flare_retrieval.py`)
```python
@dataclass
class FLAREResult:
    final_answer: str
    iterations: int = 0
    sub_queries: List[str] = field(default_factory=list)
    total_chunks_retrieved: int = 0
    confidence_improved: bool = False

class FLARERetriever:
    UNCERTAINTY_PATTERNS = [...]  # 5 compiled regexes
    def retrieve_and_generate(self, query, initial_chunks=None) -> FLAREResult
```

### 5.7 Parent Document Retrieval (`Core/parent_document_retrieval.py`)
- Creates hierarchy: split large docs into parent/child chunks
- Retrieves child (precise) → expands to parent (full context)

### 5.8 Graph RAG (`Core/graph_rag.py`)
- Community detection on entity graph
- Global queries: community summaries; Local queries: entity-specific traversal

### 5.9 Knowledge Graph (`Core/knowledge_graph.py`)
- **SQLite-backed** with per-thread connections
- Tables: `entities(id, name, entity_type, mention_count)`, `triples(id, subject_id, predicate, object_id, source_url, confidence)`
- Methods: `add_entity()`, `add_triples()`, `query_entity()`, `multi_hop(start, end, max_hops=3)`, `extract_entities_regex()`, `get_stats()`, `clear()`
- Entity ID = md5(normalized_name)[:12]

### 5.10 Advanced Reranker (`Core/reranker_advanced.py`)
- CrossEncoder model: `ms-marco-MiniLM-L-6-v2`
- `rerank(query, chunks, top_k) -> List[Dict]` — adds `rerank_score` to each chunk

### 5.11 Smart Deduplicator (`Core/smart_deduplicator.py`)
- 5-tier pipeline: exact hash → boilerplate → structural → semantic → shingle
```python
@dataclass DeduplicationResult:
    unique_chunks: List[Dict]
    stats: DeduplicationStats
    conflicts: List[ConflictCandidate] = []
```

### 5.12 Contextual Compressor (`Core/contextual_compressor.py`)
- `compress(query, chunks) -> List[Dict]` — extracts only query-relevant sentences
- Adds `_compressed`, `_original_len`, `_compressed_len` keys

### 5.13 Conflict Detector (`Core/conflict_detector.py`)
- Detects numerical/factual conflicts across sources
- `detect(chunks) -> ConflictResult` with `.has_conflicts` property

### 5.14 Hallucination Detector (`Core/hallucination_detector_v2.py`)
- Uses NLI model: `cross-encoder/nli-deberta-v3-small`
- `detect(answer, sources) -> HallucinationResult` with `.probability`, `.is_clean`
- Type breakdown: factual, inferential, etc.

### 5.15 Confidence Scorer (`Core/confidence_scorer.py`)
```python
@dataclass AnswerQuality:
    confidence: float = 0.0
    breakdown: ConfidenceBreakdown = ...  # semantic_similarity, factual_grounding, source_credibility, overall
    risk_level: str = "unknown"  # "low", "medium", "high"
    explanation: str = ""

class AnswerQualityAssessor:
    def assess(answer, query, source_chunks) -> AnswerQuality
```

### 5.16 Follow-Up Generator (`Core/follow_up_generator.py`)
- `generate(query, answer, source_chunks) -> List[str]` — returns question strings

### 5.17 Answer Refinement (`Core/answer_refinement.py`)
```python
@dataclass RefinementResult:
    original_answer, refined_answer, was_refined, quality_score,
    hallucination_probability, completeness_score, stages_applied, refinement_notes

class AnswerRefinementEngine:
    async def refine(answer, query, source_chunks) -> RefinementResult
    # Stages: hallucination_fix → completeness_check → consistency_check → quality_score
```

### 5.18 Zero-Waste Cache (`Core/zero_waste_cache.py`)
- 2-tier: Tier 1 (exact + semantic answer cache), Tier 2 (context/chunk cache)
- Fingerprint-based invalidation: `CacheFingerprint(chunk_hashes, source_urls, collection_version)`
- `get_answer/set_answer`, `get_context/set_context`, `invalidate_urls()`, `bump_version()`
- Requires SentenceTransformer embedding model
- `is_temporal_query()` / `classify_strategy()` for cache bypass on time-sensitive queries

### 5.19 Prompt Focus (`Core/prompt_focus.py`)
```python
class FocusMode(str, Enum):
    GENERAL, DATA_EXTRACTION, SUMMARIZATION, COMPARISON, FACT_CHECK, TIMELINE, DEEP_ANALYSIS

FOCUS_CONFIGS: Dict[FocusMode, FocusConfig]  # 7 pre-built configs

class PromptTemplateLibrary:
    # 12 builtin templates: medical_symptoms, medical_contraindications, legal_risk,
    # compliance_audit, financial_numbers, meeting_actions, code_review,
    # api_documentation, literature_review, statistical_digest, data_quality, entity_mapper
    def list_templates(), get_template(), apply_template(), save_custom(), delete_custom()

def validate_prompt(system_prompt) -> List[str]  # returns warnings
```

### 5.20 Metrics Tracker (`Core/metrics_tracker.py`)
```python
@dataclass QueryEvent:
    query="", latency_ms=0.0, cache_hit=False, cache_tier="",
    chunks_retrieved=0, chunks_after_dedup=0, hallucination_probability=0.0,
    quality_score=0.0, timestamp=time.time()

@dataclass IndexEvent:
    url="", chunks_created=0, processing_time_ms=0.0, doc_type="", timestamp=time.time()

@dataclass MetricsSummary:
    total_queries, cache_hit_rate, avg_latency_ms, p50/p90/p99_latency_ms,
    avg_hallucination_rate, avg_quality_score, total_documents_indexed,
    avg_indexing_time_ms, total_chunks_created

class MetricsTracker:  # Thread-safe singleton
    def record_query(event), record_index(event)
    def get_summary(window_seconds=None) -> MetricsSummary
    # IMPORTANT: get_summary() must compute avg_indexing_time_ms even when there are no queries
    def get_recent_queries(n=10), clear()
```

### 5.21 Evaluation (`Core/evaluation.py`)
```python
class AnswerEvaluator:
    def evaluate(question, answer, source_texts) -> Dict[str, float]
    # Returns: overall, faithfulness(0.35), relevance(0.30), completeness(0.20), conciseness(0.15)

class RetrievalEvaluator:
    def calculate_metrics(retrieved_docs, relevant_docs, k=5) -> Dict[str, float]
    # Returns: precision@K, recall@K, mrr, f1
```

### 5.22 Inference Guard (`Core/inference_guard.py`)
```python
class InferenceGuard:  # async context manager
    def __init__(self, operation, *, adapter=None, request_info=None)
    def mark(name), phase(name)
    async def __aenter__/aexit__  # captures crash reports on exception

@dataclass CrashReport:
    operation, error_type, error_message, traceback, timestamp, phase, elapsed_seconds,
    checkpoints, memory_before/after/delta, fifo_state, llm_state, thread_state,
    request_info, likely_cause="unknown"
    def classify()  # Auto-classifies: MEMORY, FIFO, THREAD, TIMEOUT, LLAMA_CPP, CRASH
    def to_dict()

class GuardMetrics:
    def record_call(), record_success(elapsed_ms, rss_delta_mb, profile), record_crash(report)
    def get_stats() -> Dict  # total_guarded_calls, total_crashes, crash_rate, timing, memory
```

---

## 6. Server Architecture

### `start_llm.py` — Boot Sequence:
1. Self-install: `check_and_install_requirements()`
2. Hardware profiling: `HardwareProfiler.get_profile()`
3. Load config + validate paths
4. `async main()`: prune_zombies → smoke_test → update_check → `server.start_server()`

### `zena_mode/server.py` — Orchestrator:
- `ZenAIOrchestrator(BaseZenHandler)`: HTTP handler routing to modular handlers
- `start_server()`:
  1. `zen_heart.ignite()` — launch LLM engine binary
  2. `start_hub()` — management API on port 8002 (FastAPI ASGI + fallback HTTPServer)
  3. `start_voice_stream_server()` — WebSocket voice on port 8006
  4. Launch `zena.py` as subprocess (UI on port 8080)
  5. `zen_heart.pump()` — blocking health check loop

### `zena_mode/heart_and_brain.py` — Engine Lifecycle:
- `ZenHeart.ignite()`: detect hardware → find model → launch `_bin/llama-server.exe` with optimal GPU/CPU flags
- `ZenHeart.pump()`: health polling loop, auto-restart on crash

### Ports:
| Port | Service |
|------|---------|
| 8001 | llama-server (LLM engine) |
| 8002 | Management API (FastAPI) |
| 8080 | NiceGUI web UI |
| 8003 | Voice service |
| 8006 | WebSocket voice stream |

---

## 7. UI Architecture (`zena.py` + `ui/`)

### NiceGUI App (`zena.py`):
```python
setup_app() → setup_crash_handler(), setup_logging(), start_background_gateways(),
              initialize_services() → {logger, rag_system, extractor, conversation_memory, ...}

get_backend() → tries AsyncZenAIBackend → MockAsyncBackend → StubBackend

@ui.page("/")
def index():
    state = UIState()
    # Theme, RAG dialog, layout, sidebar, chat area, model gallery, settings
```

### UI Modules (`ui/`):
- `bootstrap.py` — app initialization
- `layout.py` — page structure
- `handlers.py` — chat message handling, **surfaces CRAG/FLARE/GraphRAG/Dedup metadata**
- `sidebar.py` — navigation + RAG controls
- `actions.py` — button actions
- `modern_chat.py` — chat interface
- `rag_interface.py` — RAG document management dialog
- `model_gallery.py` — model browsing/download
- `settings_dialog.py` — user preferences
- `theme_setup.py` — dark/light mode
- `dashboard.py` — metrics dashboard
- `styles.py` — CSS styling
- `locales/` — internationalization

### UIState (`ui_state.py`):
Thread-safe dict wrapper using `RLock`. Methods: `get()`, `set()`, `update_model_options()`, `safe_update()`, `safe_scroll()`.

---

## 8. LLM Adapter Layer

```python
class LLMProvider(str, Enum):
    LOCAL_LLAMA, OLLAMA, OPENAI, CLAUDE, HUGGINGFACE, GEMINI, CUSTOM

class BaseLLMAdapter:
    async def query(request: LLMRequest) -> AsyncGenerator[str, None]
    async def validate() -> bool
    async def close()

# Concrete: LocalLlamaAdapter, OllamaAdapter, OpenAIAdapter,
#           AnthropicAdapter, HuggingFaceAdapter, GeminiAdapter

# Factory:
def create_adapter(provider, api_key=None, endpoint=None, model_name=None) -> BaseLLMAdapter
```

### `AsyncZenAIBackend` (`async_backend.py`):
- httpx-based async client targeting `http://127.0.0.1:8001/v1/chat/completions`
- Streaming support for local llama-server (OpenAI-compatible API)

---

## 9. RAG Storage Layer

### `zena_mode/rag_manager.py` — Thread-safe proxy:
```python
class RAGManager:
    _lock = threading.Lock()
    def hybrid_search(query, top_k) -> List[Dict]
    def query(query) -> str
    def build_index(documents)
    def save(), warmup(), set_model(), set_system()
```

### `zena_mode/rag_core_bridge.py` — LocalRAGv2:
- Pipeline: Documents → TextChunker(recursive) → Embed(SentenceTransformer) → Dedup → Qdrant + SQLite
- Query: Dense(SentenceTransformer) + BM25 → RRF fusion → Rerank(CrossEncoder)

### Storage:
- **Qdrant** (`qdrant_client`): vector similarity search for embeddings
- **SQLite** (`rag_db.py`): metadata, document tracking
- **BM25** (`rank-bm25`): keyword-based retrieval for hybrid search

---

## 10. Key Dependencies

```
torch, torchvision, torchaudio
transformers, sentence-transformers, tokenizers
openai, anthropic (via adapters)
faiss-cpu, qdrant-client, rank-bm25
spacy
nicegui (primary UI)
fastapi, uvicorn (management API)
PyMuPDF, pypdf, pytesseract (document processing)
beautifulsoup4 (web scraping)
faster-whisper, pyttsx3 (voice)
httpx, aiohttp, requests (networking)
psutil, watchdog (system/file monitoring)
ultralytics (YOLO vision)
pydantic (validation)
pytest, pytest-asyncio (testing)
```

---

## 11. Thread-Safety Rules

1. **Always use `RAGManager`** to access/mutate RAG indexes — it uses `threading.Lock()`
2. **`MetricsTracker`** is a thread-safe singleton with `threading.RLock()`
3. **`UIState`** uses `threading.RLock()` for all get/set operations
4. **`KnowledgeGraph`** uses per-thread SQLite connections
5. **Process monitoring** uses `register_process()` / `check_processes()` pattern
6. **Never create raw threads** for background work — use provided managers

---

## 12. Test Requirements (199 tests, NO mocks)

All tests must use real module instances with real data. Three test files:

### `tests/test_core_modules.py` (94 tests):
Covers all 22 Core modules: AdvancedReranker, SmartDeduplicator, ConflictDetector, HallucinationDetector, ConfidenceScorer, FollowUpGenerator, MetricsTracker, FLARERetriever, ContextualCompressor, QueryRewriter, ZeroWasteCache, PromptTemplateLibrary, FocusModes, InferenceGuard, AnswerRefinementEngine, AnswerEvaluator, RetrievalEvaluator, CrossModuleIntegration (5 mini-pipeline tests).

### `tests/test_enhanced_rag.py` (38 tests):
Covers pipeline components: ContextualRetrieval, HyDERetrieval, CorrectiveRAG, QueryRouter, ParentDocumentRetrieval, GraphRAG, EnhancedRAGService.

### `tests/test_deep_audit.py` (67 tests):
Covers: KnowledgeGraph CRUD (SQLite, multi-hop, entity extraction), Pydantic models (ChunkPayload, RAGSearchResult, QueryRewriteResult, EvalSample validation), MetricsTracker IndexEvent + windowed summary, EnhancedRAGService._record_metrics (bug-fix verification), ZeroWasteCache fingerprint invalidation + version bump, CrashReport classification, PromptTemplate serialization, validate_prompt, deep multi-module pipeline tests, edge cases (Unicode, missing fields, extreme values).

Run with: `python -m pytest tests/test_core_modules.py tests/test_enhanced_rag.py tests/test_deep_audit.py -v`

---

## 13. Critical Implementation Notes

1. **`_record_metrics` must use correct field names**: `latency_ms=round(elapsed * 1000, 2)` and `cache_hit=False` — NOT `latency=` or `cache_tier=0`
2. **`MetricsTracker.get_summary()`** must compute `avg_indexing_time_ms` even when there are no query events (early return path)
3. **`MetricsTracker`** uses `__new__` singleton pattern with class-level `_lock`
4. **`DeduplicationResult`** is a dataclass with `.unique_chunks` (not dict access)
5. **`AnswerQuality.confidence`** is the score field (not `.score`)
6. **`CrashReport.classify()`** sets `likely_cause` to full descriptive strings containing the category (e.g., `"MEMORY: Out of memory (RAM or GPU)"`)
7. **All Core modules lazy-load** ML models (CrossEncoder, SentenceTransformer, NLI) to keep startup fast
8. **`FLAREResult`** constructor requires `final_answer` as first positional argument
9. **Pydantic models** use `extra="allow"` to accept arbitrary additional fields
10. **UI handlers** must surface metadata from CRAG, FLARE, GraphRAG, and Dedup stages in chat responses

---

## 14. Architecture Diagram

```
                    ┌─────────────────────┐
                    │   start_llm.py      │  ← Primary entrypoint
                    │  (boot + self-heal) │
                    └─────────┬───────────┘
                              │
                    ┌─────────▼───────────┐
                    │ zena_mode/server.py  │  ← Orchestrator hub
                    │  (ZenAIOrchestrator) │
                    └──┬──────┬──────┬────┘
                       │      │      │
            ┌──────────▼┐  ┌──▼───┐  ┌▼──────────────┐
            │ ZenHeart   │  │ ASGI │  │ zena.py        │
            │ (engine    │  │ :8002│  │ (NiceGUI :8080)│
            │ lifecycle) │  └──────┘  └───────┬────────┘
            └──────┬─────┘                    │
                   │                  ┌───────▼────────┐
            ┌──────▼─────┐           │  ui/ package    │
            │ llama-server│           │  (30+ modules)  │
            │   :8001     │           └───────┬────────┘
            └─────────────┘                   │
                                      ┌───────▼────────┐
                                      │ RAG Pipeline    │
                                      │ (24 Core mods)  │
                                      └───────┬────────┘
                                              │
                    ┌─────────────────────────┼──────────────────┐
                    │                         │                  │
            ┌───────▼──────┐          ┌───────▼──────┐   ┌──────▼───────┐
            │ Qdrant       │          │ SQLite       │   │ SentenceTF   │
            │ (vectors)    │          │ (KG + meta)  │   │ (embeddings) │
            └──────────────┘          └──────────────┘   └──────────────┘
```

---

## 15. Build & Run

```bash
# Install
pip install -r requirements.txt

# Start (full stack)
python start_llm.py

# UI only (dev)
python zena.py

# Tests
python -m pytest tests/test_core_modules.py tests/test_enhanced_rag.py tests/test_deep_audit.py -v
```

Place GGUF model files in `models/` and llama-server binary in `_bin/`.
