The following notes are intended to help an AI coding agent be immediately productive working in this repository.

Purpose
- **Goal**: Fast navigation and safe edits — prefer small, well-tested changes that respect thread-safety and process orchestration.

Key entrypoints & architecture
- **`start_llm.py`**: primary entrypoint. It's a shim that delegates to `zena_mode.server` and synchronizes patched globals before calling implementation functions.
- **`zena_mode/server.py`**: the orchestrator/hub. Manages model engines, background processes, health checks, and exposes simple HTTP endpoints (e.g. `/model/status`, `/models/*`). Use this file to understand process lifecycle and model hot-swap flows.
- **`zena.py`**: main NiceGUI app (UI). The UI talks to the orchestrator and RAG layer; many UI-only behaviors live here (dialogs, timers, theme toggles).
- **`zena_mode/rag_manager.py`**: thread-safe RAG state proxy. Always use `RAGManager` to access or mutate RAG indexes/documents (it uses an `RLock`). Do not mutate global RAG state without locks.

Developer workflows / commands
- **Start dev server (backend + UI)**: `python start_llm.py` (preferred — runs the orchestrator and supporting jobs).
- **Run UI only (dev debug)**: `python zena.py` (used by some test helpers).
- **Run tests**: `python run_tests.py` (wrapper with sensible flags). Or use `python -m pytest tests/` directly for focused runs.
- **Install deps**: `pip install -r requirements.txt`. The repo also calls `dependency_manager.check_and_install()` at startup for self-healing installs.

Project-specific conventions & gotchas
- **Thread-safety is explicit**: many modules provide thin thread-safe managers (`RAGManager`, `resource_manager`). Prefer those helpers for background work instead of creating raw threads.
- **Process monitoring**: `zena_mode/server.py` keeps `MONITORED_PROCESSES` and uses `register_process()` / `check_processes()` for health and restarts — follow that pattern for any new long-running subprocess you add.
- **Shim synchronization**: tests may patch names on `start_llm` — the shim syncs names into the implementation module. When adding functions referenced by tests, ensure the shim continues to re-export/sync as needed.
- **Environment awareness**: `server.py` performs a pre-flight `validate_environment()` (hardware, free disk, existing LLM processes). CI/test code relies on those checks; avoid bypassing them unless intentionally testing failure modes.
- **Ports & engine**: default engine port is `8001` and the orchestrator expects engine binaries in `_bin/` (see `config.py` and `MODEL_DIR` / `BIN_DIR`). Tests may assume `ZENAI_PORT` or `NICEGUI_SCREEN_TEST_PORT` env vars (see `run_tests.py`).

Integration points & external services
- **Local engines**: `_bin/` contains `llama-server.exe` and related binaries — orchestrator launches and monitors these processes.
- **RAG storage**: `qdrant_storage/`, `rag_storage/`, `rag_cache/` are used by RAG tooling. Look at `zena_mode/rag_manager.py` and any `rag_*` modules under `zena_mode` for exact load/save semantics.
- **Voice / TTS**: `voice_service.py` and `experimental_voice_lab/` provide voice integration. Use `get_cached_voice_service()` wrapper in `server.py` for lazy imports.

Tests and test expectations
- **Test runner**: `run_tests.py` manages server lifecycle (starts `zena.py` on `ZENAI_PORT`) and runs pytest. Use its `--fast`, `--coverage`, and `--watch` flags.
- **E2E/UI tests**: many tests require a running NiceGUI server; `run_tests.py` starts it and sets `NICEGUI_SCREEN_TEST_PORT`. When writing tests, follow existing patterns in `tests/` for env var setup and server readiness polling.

When editing code (agent guidance)
- Make minimal, focused changes and run the related tests (`pytest tests/test_xxx.py`) locally.
- Preserve thread-safety and use provided manager APIs (`RAGManager`, `resource_manager`, `register_process`).
- For process lifecycle changes, update `MONITORED_PROCESSES` via `register_process()` to keep health checks consistent.
- For API changes, update the simple HTTP endpoints in `zena_mode/server.py` and the UI call sites in `zena.py` together in the same PR.

Files to inspect first (examples)
- `start_llm.py`, `zena_mode/server.py`, `zena.py`, `zena_mode/rag_manager.py`, `model_manager.py`, `run_tests.py`, `requirements.txt`, `_bin/`, `models/`, `tests/`

If anything in these notes is unclear or you want deeper detail on any component, tell me which area to expand (server, RAG, UI, tests, or process management).
