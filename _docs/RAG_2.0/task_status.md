# Code Review Remediation Tasks

## ✅ Completed

- [x] Fix bare exception clauses (16 in main files)
- [x] Environment variables for API keys (.env.example)
- [x] API authentication middleware (asgi_server.py)
- [x] Performance profiling (profile_performance.py)
- [x] Connection pooling (async_backend.py)
- [x] Kill stale processes (3 log watchers)
- [x] RAG search result caching (rag_pipeline.py)
- [x] Adversarial test suite (39 tests)
- [x] Integration tests (18 tests in test_break_it.py)
- [x] Monkey chaos tests (11 tests in test_monkey.py)
- [x] Fix "Connection Lost" instability (offloaded blocking RAG calls)
- [x] Refactor monolith `ui_components.py` (Simplify to Amplify)
- [x] Split `ui_components.py` into `ui/sidebar.py`, `ui/actions.py`, etc.)
- [x] Add RAG Ingestion Summary UI (Colorful/Detailed)
- [x] Improve Intelligence Judge UI (Show Active Model/Status)
)

## 🚀 RAG 2.0 Upgrade (Current Priority)
- [x] **Configurable Embeddings**: Upgrade to BGE-Base / E5-Large
- [x] **True Semantic Chunking**: Implement cosine-similarity splitting in `chunker.py`
- [x] **Semantic Caching**: Implement multi-tier cache in `rag_pipeline.py`
- [x] **Layout-Aware PDF**: Improve table/figure extraction in `universal_extractor.py`
- [x] **Advanced Reranking**: Late interaction reranking via Cross-Encoder (BGE-Reranker)
- [x] **UI Visualization**: Badges for "⚡ MEMORY" and "🎯 Rerank Scores" in `modern_chat.py`

## ⏳ Backlog (Lower Priority)
- [x] Fix Connection Lost (Hot Swap) - Server stays online during swap!
- [x] Fix LLM 400 Errors (Input Sanitization)
- [x] Debug RAG Ingestion (Enhanced Image ALT text support)

## 🧠 Multi-Model Consensus (New)
- [ ] Download second model (TinyLlama) for comparison
- [x] Update `server.py` to support `POST /swarm/launch` (Mixed Models)
- [x] Integrate `SwarmArbitrator` into main chat flow
- [x] Implement UI "Council" Panel
- [x] Download second model (TinyLlama) for comparison

## 🛡️ Security Hardening (Immediate)
- [x] Fix Symlink Path Traversal in `security.py` (strict=True)
- [x] Implement MIME Type Validation (Magic Numbers)
- [x] Create `tests/test_security_hardening.py` to verify

## ⚡ Performance Optimization
- [x] Refactor `rag_pipeline.py` to use `run_in_executor` (Non-blocking)
- [x] Add loading skeletons for RAG search
- [x] Debug RAG Ingestion (Enhanced Image ALT text support)

## 🔍 RAG Integrity Audit
- [x] Verify `UniversalExtractor` capabilities (OCR, Vision)
- [x] Verify Web Scraper capabilities (Text + ALT)
- [x] Identify gaps vs. SOTA (State of the Art) -> **Completed (RAG 2.0 Implemented)**


