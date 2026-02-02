# ZenAI Reference Specification (Master Prompt)

**Version**: 3.1 (Refactored & Async-First)
**Date**: 2026-01-20
**Status**: Production-Ready – ZERO TOLERANCE FOR DEVIATIONS

> [!CAUTION]
> **WARNING**: THIS IS THE ABSOLUTE SINGLE SOURCE OF TRUTH. ANY DEVIATION FROM THESE RULES IS A PROJECT FAILURE AND SECURITY BREACH. REBUILD EXACTLY AS SPECIFIED – NO CREATIVITY ALLOWED IN CORE LOGIC. IF SOMETHING IS NOT EXPLICITLY PERMITTED, IT IS FORBIDDEN.

---

## 1. Project Goal & Identity
**MUST BUILD** a hyper-secure, fully local, privacy-obsessed AI assistant with dual personalities:

- **ZenAI Mode**: Professional, hospital-grade UX (clean, bilingual Romanian/English, RAG-focused on medical/info sites like "https://spitaljudetean-oradea.ro/").
- **ZenAI AI Mode**: Developer-centric, code-analysis heavy.
- **Core Mandate**: 100% ZERO DATA EGRESS – Local LLM + Local RAG only. Breach this = project death.
- **UX Imperative**: Ultra-transparent – Visual cues (e.g., green tint + "Local Context Used" label) for EVERY RAG-enhanced response. NO HIDDEN MAGIC.

## 2. Technology Stack
- **Language**: Python 3.12+ (EXACTLY – no older versions for security).
- **Frontend**: NiceGUI v1.4+ (Vue/Quasar-based) – MUST be single-page, zero-reload.
- **Backend**: Asyncio + `httpx` v0.27+ (ABSOLUTE NON-BLOCKING I/O – sync code forbidden).
- **LLM Engine**: `llama.cpp` (via `llama-server.exe`) – Managed via `subprocess.Popen` with PID tracking.
- **Orchestrator**: Custom `ThreadingHTTPServer` in Python (NO EXTERNAL FRAMEWORKS).
- **Dependencies**:
    -   **Required**: `requests`, `json`, `asyncio`, `httpx`, `logging`, `pathlib`, `subprocess`.
    -   **Optional (graceful fail)**: `sounddevice`, `scipy`, `pyttsx3`, `sentence_transformers`.
    -   **Rule**: NEVER INSTALL DURING RUNTIME – All deps pre-installed or fallback.

## 3. Architecture Overview

### A. Orchestrator (`start_llm.py`)
**IRONCLAD RESPONSIBILITIES – NO EXCEPTIONS:**
1.  **Hardware Profiling**: MUST detect CPU/GPU/RAM on startup. Auto-set `--n-threads`, `--n-gpu-layers`, `--u-batch` based on `HardwareProfiler`. Enable Nitro mode if AVX2+ detected.
2.  **Process Management**: Launch `llama-server.exe` and `zena.py` via subprocess. MUST implement `kill_process_tree` on shutdown/Interrupt. Log EVERY PID.
3.  **Auto-Update Mechanism**: MUST check for `_bin/llama-server.exe.new` on EVERY startup. If exists: Atomic swap (backup old to .bak, rename .new to .exe). NEVER overwrite running binary.
4.  **Hub API (Port 8002)**: MUST handle `/models/available` (list GGUF), `/models/download` (async fetch), `/models/set_active` (hot-swap).
5.  **Voice WebSocket (Port 8003)**: MUST use websockets for real-time audio streaming. Fallback if import fails.

### B. Async Backend (`async_backend.py`)
**ABSOLUTE ASYNC PURITY – BLOCKING = DEATH:**
1.  **True Async Mandate**: MUST use `httpx.AsyncClient` with context manager (`aenter`/`aexit`).
2.  **Model Management**: `get_models()`, `download_model()`, and `set_active_model()` MUST be fully async using `httpx`.
3.  **Streaming**: `send_message_async` MUST yield chunks via async generator. NEVER buffer full response.

### C. Frontend UI (`zena.py` & `ui_components.py`)
**UI THREAD SACRED – VIOLATE = CRASH GUARANTEE:**
1.  **De-Monolithization**: Core UI logic separated into `ui_components.py`:
    -   `setup_drawer`: Sidebar state and model management.
    -   `setup_common_dialogs`: Download/Update dialogs.
    -   `setup_app_theme`: CSS and styling.
2.  **Dual Mode Lockdown**: MUST load from `config.json`. ZenAI: Bilingual placeholder ("Spuneți-mi..."), RAG on. ZenAI: English, no RAG default.
2.  **Chat Interface**:
    -   MUST stream responses chunk-by-chunk (update markdown in real-time).
    -   **TRANSPARENCY LAW**: If RAG used, MUST append green label **"- Local Context -"** and tint bubble (#E0F7FA/Green-50). NEVER hide RAG usage.
3.  **Interactive Update**:
    -   MUST check GitHub API for `llama.cpp` releases (async).
    -   MUST show Dialog: "New Version Available! Upgrade? [Download & Install] [Skip]".
    -   Download MUST go to `_bin/llama-server.exe.new`. Instruct user to restart.
4.  **RAG Integration**: MUST scrape websites/dirs async, build FAISS index, query top-5 chunks. NEVER scrape without user consent dialog.

### D. Support Modules
-   **`utils.py`**:
    -   `sanitize_prompt(text)`: MUST remove ALL injection risks (e.g., strip `<|im_start|>`, `<|system|>`, null bytes, truncate to 8192 chars).
    -   `format_message_with_attachment`: MUST wrap in `\n{attachment}\n`. NEVER inline raw.
-   **`security.py`**:
    -   `FileValidator`: MUST enforce 10MB HARD limit, WHITELIST extensions ONLY (.txt, .py, etc.), MAGIC BYTE check (no binaries), UTF-8 strict decode.
-   **`decorators.py`**:
    -   `@retry`: Exponential backoff (max 3 attempts).
    -   `@timer`: Log EVERY execution >50ms as WARNING.
    -   `@log_errors`: MUST call `handle_error`, notify UI.

---

## 4. Key Implementation Details (The "Ultra-Hardening")

### Security Commandments – BREAK ANY = SECURITY APOCALYPSE
> **SECURITY IS NON-NEGOTIABLE – ANY BREACH IS PROJECT DEATH SENTENCE. AUDIT EVERY LINE.**

1.  **NEVER** pass ANY user string to LLM without `sanitize_prompt()`. DEATH SENTENCE.
2.  **NEVER** trust file extensions – MUST use magic bytes/content-type validation. Reject binaries INSTANTLY.
3.  **NEVER** allow non-text files – WHITELIST ONLY, reject with `ui.notify(ERROR)`.
4.  **NEVER** concatenate user content into system prompt – MUST use separate `{"role": "user"}` message.
5.  **MUST** truncate ALL user content to 100_000 chars HARD (`sanitize_content`).
6.  **NEVER** expose local paths/ports externally – All APIs localhost ONLY.

#### Concrete Example: File Upload Handler
```python
async def on_upload(e):
    content = await e.content.read()  # ASYNC ONLY
    is_valid, err, decoded = FileValidator.validate_file(e.name, content)
    if not is_valid:
        ui.notify(f"{EMOJI['error']} {err}", color='negative')  # MUST NOTIFY
        return
    sanitized = FileValidator.sanitize_content(decoded)
    attachment_state.set(e.name, sanitized, preview=sanitized[:200] + '...')  # THREAD-SAFE
```

### Async Commandments – BLOCK UI THREAD = INSTANT FAILURE
> **UI THREAD BLOCKING = IMMEDIATE PROJECT DEATH – ZERO TOLERANCE POLICY.**

1.  **ALL** event handlers in `zena.py` MUST be `async def`. NEVER sync.
2.  **NEVER** use `requests`/sync HTTP – MUST `httpx.AsyncClient`.
3.  **NEVER** use `time.sleep()` – MUST `asyncio.sleep()`.
4.  **For sync heavy work** (e.g., RAG build) – MUST use `await asyncio.get_event_loop().run_in_executor(None, func)`.
5.  **Streaming**: MUST use `async for chunk in backend.send_message_async()` – Update UI per chunk.

#### Concrete Example: Stream Response
```python
async def stream_response(text: str):
    final_prompt = sanitize_prompt(text)  # SECURITY FIRST
    if ZENA_MODE and rag_system:
        context = await rag_system.query(final_prompt)  # ASYNC
        final_prompt += f"\nContext: {context}"  # SEPARATE
    add_message("user", final_prompt)  # THREAD-SAFE
    msg_ui = add_message("assistant", "")  # Placeholder
    full_text = ""
    async for chunk in async_backend.send_message_async(final_prompt):
        full_text += chunk
        msg_ui.update(full_text)  # REAL-TIME
    if context: msg_ui.classes.add('rag-tint')  # TRANSPARENCY
```

### Update Lifecycle – EXACT PROTOCOL, NO DEVIATIONS
1.  **User Trigger**: On "Check Version" click – Async GitHub API fetch latest release.
2.  **Dialog**: MUST show: "Upgrade to vX.Y? [Download & Install] [Skip]". Warn: "Restart required".
3.  **Download**: MUST fetch win-x64 binary to `_bin/llama-server.exe.new`. Progress bar UI.
4.  **Restart**: Instruct user to close/reopen app.
5.  **Swap on Startup**: In `start_llm.py` – If `.new` exists: Rename current to `.bak`, `.new` to `.exe`. Log + notify success.
    -   **NEVER** auto-restart – User manual only.

## 5. Directory Structure – EXACT, NO CHANGES
```
ZenAI/
├── _bin/                  # llama-server.exe, .new, .bak
├── rag_cache/             # FAISS indexes – MUST exist
├── tests/                 # MANDATORY test suite
├── zena.py                # UI Entry Point – EXACTLY this name
├── ui_components.py       # UI Components (Drawer, Dialogs, Theme)
├── start_llm.py           # Orchestrator – EXACTLY
├── async_backend.py       # Async Backend – EXACTLY
├── config_system.py       # Config – EXACTLY
├── security.py            # Security – EXACTLY
├── state_management.py    # State – EXACTLY
├── decorators.py          # Decorators – EXACTLY
├── utils.py               # Helpers + Sanitize – EXACTLY
└── zena_mode/             # RAG – LocalRAG.py, WebsiteScraper.py
```

## 6. Forbidden Patterns – DO THESE = PROJECT REJECTION
1.  **NEVER** use globals without locks (e.g., `rag_system` MUST be thread-safe).
2.  **NEVER** hardcode ports/URLs – MUST from `config.json`.
3.  **NEVER** sync I/O in UI – e.g., no `open(file)` without executor.
4.  **NEVER** RAG without consent – MUST dialog: "Scan site? [Yes/No]".
5.  **NEVER** ignore errors – MUST `handle_error` EVERY exception.
6.  **NEVER** expose PII – Voice/RAG local ONLY.

## 7. Verification Status – MANDATORY TESTS (GREEN OR FAIL)
> **TDD MANDATE: ALL TESTS MUST PASS 100%. NO EXCEPTIONS.**

**MUST IMPLEMENT AT MINIMUM:**
-   **Security**: Test `validate_file` rejects large/binary/invalid UTF-8. Test `sanitize` truncates/injection-strips.
-   **Async**: Test `stream_response` yields chunks without blocking (mock `httpx`).
-   **State**: Thread-safety: 100 concurrent set/get on `AttachmentState` – No races.
-   **RAG**: Test query returns top-5, no scrape without cache hit.
-   **Update**: Mock download/swap – Verify `.new` → `.exe` atomic.
-   **UI**: NiceGUI tests: Simulate send/upload – Assert chat updates real-time.
-   **Decorators**: Test `@retry` succeeds after 2 fails; `@timer` logs slow.
-   **E2E**: Startup → Send message → RAG tint appears.

**Tools**: `pytest` + `nicegui.testing` + `concurrent.futures`.

---

## 8. UI Interaction & Testability
**MANDATORY TRACKING OF INTERACTIVE ELEMENTS**

1.  **UI Registry**: EVERY button, menu item, and switch MUST have a unique ID defined in `ui/registry.py`.
2.  **ID Assignment**: IDs MUST be assigned via the `.props(f'id={UI_IDS.NAME}')` or `.classes(id=...)` method in NiceGUI.
3.  **Chaos Testing**: The `live_diagnostics.py` (Monkey Test) MUST include a UI chaos phase that targets these IDs to ensure no "dead" or crashing elements exist.
4.  **Semantic Validation**: Chaos testing MUST be "Smart"—utilizing the Local LLM to verify that UI actions and resulting transitions make logical sense based on the registry metadata.
5.  **No Exceptions**: Any new interactive element added without an ID in the registry and a corresponding test case is a specification violation.

---

**FINAL COMMANDMENT**: REBUILD THIS EXACTLY. AUDIT AGAINST THIS SPEC. ANY MISSING RULE = REJECT AND REDO. Use flow diagrams from prior analysis for visual guidance.
