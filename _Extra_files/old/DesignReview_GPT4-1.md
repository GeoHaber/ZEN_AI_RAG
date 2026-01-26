# ZenAI Design Review (GPT-4.1)

## 1. Executive Summary
ZenAI is a privacy-first, local AI assistant with dual personas (ZenAI Mode for medical/bilingual UX, ZenAI AI Mode for developer/code analysis). The system is built for security, async performance, and transparency, with a modular architecture and strict adherence to a master specification. This review covers architecture, code quality, security, async compliance, RAG, model management, UI, and test coverage.

## 2. Architecture Overview
- **Frontend**: NiceGUI (Vue/Quasar), single-page, streaming chat, file upload, model selection, voice, and RAG controls.
- **Backend**: Async Python (httpx, asyncio), orchestrator (start_llm.py), async backend, model router, model discovery, and RAG pipeline.
- **LLM Engine**: llama.cpp via managed subprocess, hot-swappable models, multi-expert (swarm) support.
- **RAG**: Local website/directory/PDF ingestion, FAISS+SQLite, deduplication, hybrid search.
- **Security**: File validation, prompt sanitization, strict extension/encoding checks, no data egress.
- **Testing**: Pytest, NiceGUI testing, E2E, async, security, and state management tests.

## 3. Security & Compliance
- **Prompt Sanitization**: All user input passes through `sanitize_prompt`.
- **File Uploads**: 10MB hard limit, extension whitelist, magic byte check, UTF-8 only, path traversal protection.
- **No Data Egress**: All LLM/RAG is local; APIs bind to localhost only.
- **No Runtime Installs**: All dependencies pre-installed or fail gracefully.
- **No PII Exposure**: RAG/voice strictly local.

## 4. Async & Performance
- **Async Mandate**: All backend I/O is async (httpx, streaming, RAG scraping, model management).
- **No Blocking**: No `requests` or `time.sleep` in async code; uses `asyncio.sleep` and `run_in_executor` for heavy sync work.
- **Streaming**: UI and backend stream responses chunk-by-chunk.
- **Thread Safety**: State management (attachments, chat history) uses locks; tested for concurrency.

## 5. Model Management & Discovery
- **Model Discovery**: Monitors HuggingFace, analyzes new models, scores and recommends upgrades, multi-source planned.
- **Model Router**: Fast intent classifier routes queries to best model for task (code, reasoning, chat, etc.).
- **Benchmarking**: Automated speed/quality benchmarks, task routing config, model advisor.
- **Hot Swap**: Models can be downloaded, loaded, and swapped at runtime via Hub API.

## 6. Retrieval-Augmented Generation (RAG)
- **Website Scraper**: Async, domain-restricted, user-consent dialog, cleans and deduplicates content.
- **Directory Scanner**: Recursively indexes local files, extension/size/encoding checks.
- **PDF Extraction**: Uses PyPDF2, robust error handling.
- **FAISS+SQLite**: Vector and metadata storage, hybrid search (BM25+embeddings), deduplication (hash+semantic).

## 7. UI/UX
- **Streaming Chat**: Real-time markdown updates, RAG transparency (green tint, label), bilingual support.
- **Dialogs**: Model download, update, and consent dialogs.
- **Sidebar**: Model selection, RAG controls, diagnostics.
- **Voice**: Whisper STT, piper TTS, async WebSocket.

## 8. Test Coverage & Quality
- **Security**: File validation, prompt sanitization, path traversal, encoding, and extension tests.
- **Async**: Backend, streaming, and context manager tests.
- **State**: Thread safety, pagination, and error handling.
- **RAG**: Deduplication, junk filtering, batch/cross-batch, and query tests.
- **Decorators**: Retry, timer, log_errors, and performance criticality.
- **UI**: Menu/button, chat input, and E2E tests.

## 9. Gaps & Issues
- **Hub/Swarm Scaling**: Tests fail if Hub server is not running; needs better local mock/fallback.
- **Engine Guard**: Process management test (kill/swap) is brittle on Windows; needs more robust PID handling.
- **Model Discovery**: Multi-source (beyond HuggingFace) is planned but not yet implemented.
- **Async Purity**: Some legacy sync code (requests, time.sleep) remains in non-critical paths (e.g., fallback, discovery); should be refactored.
- **UI Polish**: Some planned features (floating popup, pulsing trigger, full multilingual) are not yet implemented.
- **Test Isolation**: Some tests require live servers or real models; more mocking would improve CI reliability.

## 10. Prioritized Fixes & Recommendations
1. **Critical**: Refactor any remaining sync I/O (requests, time.sleep) in backend/model discovery to async/httpx/asyncio.sleep.
2. **Critical**: Add local mocks/fallbacks for Hub/Swarm API in tests to avoid failures when server is down.
3. **High**: Complete multi-source model discovery (add other reputable model repositories, not just HuggingFace).
4. **High**: Harden process management (engine guard) for cross-platform reliability; improve test cleanup.
5. **High**: Enforce async/await in all event handlers and backend calls (audit for any missed sync code).
6. **Medium**: Polish UI (floating popup, pulsing trigger, full multilingual, RAG consent dialog always visible).
7. **Medium**: Expand test mocks for model API, RAG, and UI to improve CI reliability.
8. **Medium**: Add more granular logging and error reporting for all async operations.
9. **Low**: Continue to optimize RAG deduplication and hybrid search (BM25+embeddings fusion).
10. **Low**: Document all config options and add more user-facing diagnostics in the UI.

---

**This review is based on a full codebase and spec audit as of 2026-01-22. All recommendations are prioritized by security, stability, and user impact.**
