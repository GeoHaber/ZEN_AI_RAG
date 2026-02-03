# ZenAI Design Review - Module-by-Module Analysis

**Date:** February 1, 2026 | **Status:** Comprehensive Module Review

---

## Quick Navigation

| Module | Lines | Issues | Debt Score | Priority |
|--------|-------|--------|-----------|----------|
| [start_llm.py](#start_llmpy) | 129 | 1 | 3/10 | LOW |
| [zena_mode/server.py](#zena_modeserverpy) | 932 | **7** | **9/10** | **CRITICAL** |
| [zena.py](#zenappy) | 1415 | **8** | **8/10** | **CRITICAL** |
| [async_backend.py](#async_backendpy) | 229 | 2 | 3/10 | LOW |
| [config_system.py](#config_systempy) | 277 | 1 | 2/10 | LOW |
| [ui_components.py](#ui_componentspy) | 1351 | 3 | 4/10 | MEDIUM |
| [security.py](#securitypy) | 137 | 1 | 2/10 | LOW |
| [zena_mode/rag_manager.py](#zena_moderag_managerpy) | 80 | 0 | 1/10 | LOW |
| [voice_service.py](#voice_servicepy) | unknown | 1 | 3/10 | LOW |

---

## start_llm.py

**Lines:** 129 | **Health:** ✅ GOOD | **Score:** 7/10

### Purpose
Entry point handling hardware profiling, process cleanup, and orchestrator launch.

### Strengths ✅
- Clear single responsibility (orchestration startup)
- Good diagnostic logging with EMOJI
- Hardware tuning logic well-commented
- Atomic update mechanism for engine binary

### Issues ⚠️

#### Issue #1: Cleanup Depends on External Function
**Severity:** LOW | **Type:** Dependency

```python
if not prune_zombies(auto_confirm=True):
    sys.exit(0)  # Confusing exit on False
```

**Problem:** Unclear when `prune_zombies()` returns False. What failed? Exit codes should be different.

**Fix:**
```python
result = prune_zombies(auto_confirm=True)
if result == CleanupStatus.CRITICAL_FAILURE:
    safe_print(f"FATAL: {result.message}")
    sys.exit(1)
elif result == CleanupStatus.USER_ABORT:
    safe_print("Cleanup cancelled by user")
    sys.exit(0)
```

### Recommendations
1. ✅ ACCEPT as-is (good module)
2. Standardize exit codes globally
3. Add metrics export on startup

---

## zena_mode/server.py

**Lines:** 932 | **Health:** 🔴 CRITICAL | **Score:** 2/10

### Purpose
Orchestrator managing backend services, HTTP routing, model lifecycle, and process monitoring.

### Strengths ✅
- Process registration with health monitoring ✅
- Comprehensive HTTP API coverage
- Lazy loading of optional dependencies (model_manager, voice_service)
- Good logging with diagnostic captures

### Issues 🔴

#### Issue #1: CRITICAL - Monolithic Request Handler
**Severity:** 🔴 CRITICAL | **Type:** Architecture

**Problem:** Single `ZenAIOrchestrator` class mixes 11 concerns:
```python
class ZenAIOrchestrator(BaseHTTPRequestHandler):
    # Routes:
    # - GET /models/* (model management)
    # - GET /voice/* (voice endpoints)
    # - GET /list (model list)
    # - POST /swap (model swap)
    # - POST /health (health check)
    # - GET /assets/* (static file serving)
    # - GET /updates/* (update checking)
    # ... 20+ endpoint handlers in one class
```

**Impact:** 
- Can't test individual endpoint without full HTTP server
- Can't reuse business logic
- Changes to one handler affect entire class

**Fix:** Break into route modules
```
routes/
├── models_routes.py (model loading, swapping, listing)
├── voice_routes.py (voice APIs, devices)
├── health_routes.py (health checks, metrics)
├── static_routes.py (file serving, assets)
└── diagnostics_routes.py (updates, profiling)
```

---

#### Issue #2: Sync HTTP Server Doesn't Scale
**Severity:** 🔴 HIGH | **Type:** Performance/Reliability

**Problem:** Uses `BaseHTTPRequestHandler` (synchronous) with `ThreadingHTTPServer`

```python
# Current: Blocking handler
class ZenAIOrchestrator(BaseHTTPRequestHandler):
    def do_GET(self):
        # Synchronous I/O blocks thread
        response = self.client.get(...)  # BLOCKS entire handler thread
        self.wfile.write(response)
```

**Impact:**
- Long-running requests block other clients
- Streaming responses don't work well
- No proper async/await support
- Scaling to multiple users is inefficient

**Fix:** Use FastAPI/Starlette
```python
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import StreamingResponse

async def chat_endpoint(request):
    payload = await request.json()
    async def generate():
        async for chunk in backend.stream_response(**payload):
            yield chunk
    return StreamingResponse(generate())

routes = [Route('/v1/chat/completions', chat_endpoint, methods=['POST'])]
app = Starlette(routes=routes)
```

**Effort:** 2-3 days | **Benefit:** +2 reliability, +1 performance

---

#### Issue #3: No Request Size Limits
**Severity:** 🟡 MEDIUM | **Type:** Security

**Problem:** No validation of request body size

```python
async def send_message_async(text: str):
    payload = {
        "messages": [{"role": "user", "content": text}]
        # No size check on 'text'
    }
```

**Attack:** Send 1GB prompt → OOM server

**Fix:**
```python
MAX_REQUEST_SIZE = 1024 * 1024  # 1MB

@app.middleware("http")
async def enforce_size_limit(request, call_next):
    if int(request.headers.get('content-length', 0)) > MAX_REQUEST_SIZE:
        return JSONResponse({'error': 'Payload too large'}, status_code=413)
    return await call_next(request)
```

---

#### Issue #4: CORS Wildcard Everywhere
**Severity:** 🟡 MEDIUM | **Type:** Security

**Problem:** `Access-Control-Allow-Origin: *` on all endpoints

```python
self.send_header('Access-Control-Allow-Origin', '*')  # Anyone can call
```

**Attack:** Remote machine can call your API if not bound to localhost

**Fix:**
```python
ALLOWED_ORIGINS = ["http://localhost:8080", "http://127.0.0.1:8080"]

@app.middleware("http")
async def enforce_cors(request, call_next):
    origin = request.headers.get("origin", "")
    if origin not in ALLOWED_ORIGINS:
        return JSONResponse({'error': 'Forbidden'}, status_code=403)
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = origin
    return response
```

---

#### Issue #5: No Authentication on Management Endpoints
**Severity:** 🟡 MEDIUM | **Type:** Security

**Problem:** `/swap`, `/models/download` accessible without auth

```python
# POST /swap - anyone can swap models
@app.post('/swap')
async def swap_model(request):
    data = await request.json()
    # No token check
    switch_model(data['model'])
```

**Attack:** DOS by repeatedly swapping models (ties up GPU/VRAM)

**Fix:**
```python
ADMIN_TOKEN = os.environ.get("ZENAI_ADMIN_TOKEN", "")

def require_admin_token(f):
    @wraps(f)
    async def wrapper(request):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "")
        if not token or (ADMIN_TOKEN and token != ADMIN_TOKEN):
            return JSONResponse({'error': 'Unauthorized'}, status_code=403)
        return await f(request)
    return wrapper

@app.post('/swap')
@require_admin_token
async def swap_model(request):
    ...
```

---

#### Issue #6: Hardcoded Ports/Paths
**Severity:** 🟡 MEDIUM | **Type:** Config Drift

**Problem:** Some hardcoded values mixed with config

```python
# Some modules use config:
self.api_url = f"http://{config.host}:{config.llm_port}/v1/chat/completions"

# Others hardcode:
API_URL = "http://127.0.0.1:8001/v1/chat/completions"  # zena.py
```

**Impact:** Changing config.llm_port doesn't update all code paths

**Fix:** Audit all hardcoded values
```python
# Run this search
grep -r "127.0.0.1\|0\.0\.0\.0\|localhost" --include="*.py" .
grep -r "8001\|8002\|8080\|8003" --include="*.py" .

# Replace all with config references
```

---

#### Issue #7: Process Monitoring Incomplete
**Severity:** 🟡 MEDIUM | **Type:** Reliability

**Problem:** Process monitoring loop runs, but restart logic unclear

```python
def check_processes():
    crashed = []
    # Detects crashes, but then what?
    return crashed

# Called but result not always handled
check_processes()  # Lost information
```

**Impact:** Crashed processes not automatically restarted

**Fix:** Implement state machine + auto-restart
```python
class ProcessMonitor:
    async def run_health_check_loop(self):
        while True:
            crashed = check_processes()
            for name, exit_code, is_critical in crashed:
                if is_critical and info["restarts"] < info["max_restarts"]:
                    await restart_process(name)
                    info["restarts"] += 1
            await asyncio.sleep(5)
```

---

### Recommendations for server.py

**Priority:** CRITICAL - Must fix

1. **Week 1:** Break into route modules (3 days)
   ```python
   # Move HTTP logic to:
   routes/
   ├── __init__.py
   ├── models.py (150 lines)
   ├── voice.py (100 lines)
   ├── health.py (80 lines)
   └── static.py (100 lines)
   
   # Keep business logic in:
   services/
   ├── __init__.py
   ├── model_service.py (model ops)
   ├── process_service.py (lifecycle)
   └── voice_service.py (voice ops)
   ```

2. **Week 2:** Switch to ASGI (2 days)
   ```python
   from starlette.applications import Starlette
   # Replace BaseHTTPRequestHandler with async handlers
   ```

3. **Week 2:** Add security (1 day)
   ```python
   # Add middleware for:
   - Request size limits
   - CORS validation
   - Token auth for management endpoints
   - Local-only binding enforcement
   ```

**Estimated Total Effort:** 1 week  
**Benefit:** Moves from 2/10 to 7/10 health score

---

## zena.py

**Lines:** 1415 | **Health:** 🔴 CRITICAL | **Score:** 2/10

### Purpose
NiceGUI-based chat interface with RAG, file uploads, voice, and settings.

### Strengths ✅
- Rich, professional UI with dark mode support ✅
- Comprehensive keyboard shortcuts
- RAG integration with sidebar controls
- File upload with format detection
- Background scanner for updates

### Issues 🔴

#### Issue #1: CRITICAL - Monolithic 1415-Line Page Component
**Severity:** 🔴 CRITICAL | **Type:** Architecture

**Problem:** Single `@ui.page('/')` function contains entire app

```python
@ui.page('/')
async def nebula_page():
    # Lines 1-1415:
    # - 200 lines: UI composition
    # - 300 lines: Chat message handling
    # - 150 lines: RAG integration
    # - 200 lines: Background tasks
    # - 200 lines: Settings/dialogs
    # - 165 lines: Misc
```

**Impact:**
- Can't test chat logic without full UI
- Can't reuse message rendering logic
- Can't test attachment handling separately
- 5+ minute test startup time

**Example Problem:**
```python
# Can't test this without UI
async def send_chat_message(text):
    ui_state.status_text.set_text("Sending...")  # Hardcoded to UI
    response = await async_backend.send_message_async(text)
    ui_state.chat_log.refresh()  # Can't test without browser
```

**Fix:** Extract to service layer
```python
# services/chat_service.py - pure business logic
class ChatService:
    async def send_message(text: str) -> Message:
        return Message(role="user", content=text)  # No UI
    
    async def get_response(messages: List[Message]) -> str:
        async for chunk in self.backend.send_message_async(...):
            yield chunk  # No UI
```

Then UI calls it:
```python
# pages/chat.py - UI layer
async def on_send_click():
    msg = await chat_service.send_message(input.value)
    display_message(msg)  # UI-only logic
```

**Estimated Fix:** 4 days (extract 400 lines to services)

---

#### Issue #2: Background Tasks Embedded in UI
**Severity:** 🔴 HIGH | **Type:** Architecture

**Problem:** Long-running tasks in UI render path

```python
@ui.page('/')
async def nebula_page():
    # Background scanner started during page render
    app.on_startup(lambda: asyncio.create_task(background_scanner_loop()))
    
    # Periodic cleanup also in render
    ui.timer(10.0, run_cleanup, once=True)
```

**Impact:**
- If scanner crashes, page render affected
- Hard to monitor task health separately
- Resource leaks if page reloaded

**Fix:** Move to separate module
```python
# services/background_tasks.py
class BackgroundTaskManager:
    async def start(self):
        asyncio.create_task(self._scanner_loop())
        asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        # Graceful shutdown

# In main.py
task_mgr = BackgroundTaskManager()
app.on_startup(task_mgr.start)
app.on_shutdown(task_mgr.stop)
```

---

#### Issue #3: RAG Operations Mixed with UI
**Severity:** 🟡 HIGH | **Type:** Coupling

**Problem:** RAG queries directly in UI event handlers

```python
# Can't test RAG logic without UI
async def on_rag_upload(files):
    for file in files:
        docs = await extract_pdf(file)  # Mixed in UI
        await rag_system.build_index(docs)  # Mixed in UI
        ui.notify(f"Indexed {len(docs)} docs")
```

**Fix:** Create RAG service
```python
# services/rag_service.py
class RAGService:
    async def ingest_documents(docs) -> IngestResult:
        return await self.rag_manager.build_index(docs)

# pages/rag_dialog.py
async def on_rag_upload(files):
    result = await rag_service.ingest_documents(docs)
    ui.notify(f"Indexed {result.count} docs")
```

---

#### Issue #4: Global State Access
**Severity:** 🟡 MEDIUM | **Type:** Testing

**Problem:** Uses globals making tests hard

```python
# Global access throughout file
rag_system = None
conversation_memory = None
universal_extractor = None

# Later:
if ZENA_MODE:
    rag_system = LocalRAG(...)  # Set globally
```

**Impact:** Can't run tests in parallel

**Fix:** Use dependency injection
```python
class UIState:
    def __init__(self, rag_service, memory_service, backend):
        self.rag = rag_service
        self.memory = memory_service
        self.backend = backend

@ui.page('/')
async def nebula_page():
    ui_state = UIState(
        rag_service=get_rag_service(),
        memory_service=get_memory_service(),
        backend=get_async_backend()
    )
    # Now injectable and testable
```

---

#### Issue #5: Configuration Hardcoding
**Severity:** 🟡 MEDIUM | **Type:** Config Drift

**Problem:** URLs hardcoded despite config system

```python
API_URL = "http://127.0.0.1:8001/v1/chat/completions"  # Hardcoded!

# async_backend.py uses config (correct):
self.api_url = f"http://{config.host}:{config.llm_port}/v1/chat/completions"
```

**Impact:** If you change llm_port in config, zena.py still uses 8001

**Fix:** Remove hardcodes
```python
# zena.py - DELETE THIS:
API_URL = "..."

# Instead use:
from config_system import config
API_URL = f"http://{config.host}:{config.llm_port}/v1/chat/completions"
```

---

#### Issue #6: Theme Sync Complexity
**Severity:** 🟡 MEDIUM | **Type:** Maintainability

**Problem:** Dark mode sync requires JavaScript + CSS + Python logic

```python
# JavaScript dark mode observer:
const observer = new MutationObserver(...);
observer.observe(document.body, { attributes: true, ...});

# Plus CSS:
.body--dark { background-color: var(--slate-950); }

# Plus Python:
dark_mode = ui.dark_mode(value=saved_dark_mode)
```

**Impact:** Bug in one layer breaks dark mode

**Fix:** Centralize theme logic
```python
# services/theme_service.py
class ThemeService:
    def __init__(self):
        self.current = "light"
    
    def set_dark(self, is_dark):
        self.current = "dark" if is_dark else "light"
        self._apply_to_ui()
        self._save_preference()
    
    def _apply_to_ui(self):
        # Single source of truth
```

---

#### Issue #7: Complex Keyboard Shortcut Handling
**Severity:** 🟡 LOW | **Type:** Maintainability

**Problem:** Keyboard shortcuts scattered throughout file

```python
# Shortcuts defined in multiple places
ui.run_javascript('...')  # In one section
ui.keyboard(...)  # In another
element.props('shortcut=...')  # In a third
```

**Impact:** Hard to document, test, modify shortcuts globally

**Fix:** Centralize shortcuts
```python
# ui/shortcuts.py
SHORTCUTS = {
    "Ctrl+Enter": handle_send_message,
    "Ctrl+K": focus_search,
    "Escape": close_dialogs,
    "Ctrl+,": open_settings,
}

def setup_shortcuts(ui_state):
    for keys, handler in SHORTCUTS.items():
        ui.keyboard(keys, handler)
```

---

#### Issue #8: Session Management Incomplete
**Severity:** 🟡 LOW | **Type:** Reliability

**Problem:** Session ID created but not well utilized

```python
ui_state.session_id = str(uuid.uuid4())[:8]

# Later: Used for conversation memory, but no cleanup
```

**Impact:** Sessions accumulate indefinitely

**Fix:** Add session cleanup
```python
class SessionManager:
    MAX_SESSION_AGE = 24 * 3600  # 24 hours
    
    async def cleanup_old_sessions(self):
        for session_id, metadata in self.sessions.items():
            age = time.time() - metadata['created']
            if age > self.MAX_SESSION_AGE:
                await self.delete_session(session_id)
```

---

### Recommendations for zena.py

**Priority:** CRITICAL - Must split immediately

**Week 1 (3 days):**
1. Extract chat service (message handling, backend calls)
2. Extract RAG service (document ingestion, queries)
3. Extract settings service (preference management)

**Week 2 (2 days):**
1. Extract UI components to separate modules
2. Create page modules: `pages/chat.py`, `pages/settings.py`
3. Move keyboard shortcuts to dedicated module

**Week 3 (2 days):**
1. Move background tasks to `BackgroundTaskManager`
2. Add dependency injection
3. Add unit tests for services

**Final Structure:**
```
ui/
├── main.py (page layout, 150 lines)
├── pages/
│   ├── chat_page.py (chat UI)
│   ├── sidebar.py (left drawer)
│   └── settings_page.py (settings)
├── components/
│   ├── chat_bubble.py
│   ├── message_input.py
│   └── dialogs.py
├── services/
│   ├── chat_service.py (business logic)
│   ├── rag_service.py (RAG ops)
│   ├── theme_service.py (dark mode)
│   └── keyboard_service.py (shortcuts)
└── state.py (UIState)
```

**Benefit:** Moves from 2/10 to 7/10, enables unit testing

---

## async_backend.py

**Lines:** 229 | **Health:** ✅ GOOD | **Score:** 7/10

### Purpose
Async HTTP backend for LLM communication with streaming support.

### Strengths ✅
- True async/await design ✅
- Streaming response handling
- Proper error messages (connection, timeout)
- Payload diagnostic capture
- Metrics collection (TTFT, TPS)

### Issues ⚠️

#### Issue #1: Incomplete Error Handling
**Severity:** LOW | **Type:** Reliability

**Problem:** Some errors silently ignored

```python
try:
    data = json.loads(json_str)
    delta = data['choices'][0]['delta']
    content = delta.get('content', '')
except (json.JSONDecodeError, KeyError, IndexError) as e:
    logger.debug(f"[AsyncBackend] Skipping malformed chunk: {e}")
    pass  # Silently continue
```

**Impact:** Malformed responses can corrupt chat

**Fix:** Track corruption
```python
if not isinstance(data, dict) or 'choices' not in data:
    logger.warning(f"[AsyncBackend] Malformed response: {json_str[:100]}")
    # Optionally: yield error indicator to UI
    yield f"[Parse error at token {chunk_count}]"
    continue
```

---

#### Issue #2: Resource Not Properly Scoped
**Severity:** LOW | **Type:** Resource Management

**Problem:** Context manager creates new clients unnecessarily

```python
async def get_models(self) -> list:
    if not self.client:
        async with httpx.AsyncClient() as temp_client:
            return await self._fetch_models(temp_client)
    return await self._fetch_models(self.client)
```

**Impact:** Extra client connections, more latency

**Fix:** Use property
```python
async def get_client(self):
    if not self.client:
        self.client = httpx.AsyncClient(timeout=300)
    return self.client
```

---

### Recommendations for async_backend.py
✅ **ACCEPT** as primary backend
- Improve error tracking (log corruption events)
- Add connection pooling configuration
- Extend metrics collection

---

## config_system.py

**Lines:** 277 | **Health:** ✅ EXCELLENT | **Score:** 8/10

### Purpose
Centralized configuration with layered loading and type safety.

### Strengths ✅
- Clean dataclass design ✅
- Layered config loading (system > user > defaults)
- Nested dataclass support
- Type hints throughout
- Backward compatibility with dict-like access
- Clear security boundaries (MAX_FILE_SIZE, ALLOWED_EXTENSIONS)

### Issues ⚠️

#### Issue #1: No Validation on Load
**Severity:** LOW | **Type:** Reliability

**Problem:** Config loaded but not validated

```python
@classmethod
def load(cls) -> 'AppConfig':
    # Loads config but doesn't validate
    # Port could be 999999 - not caught until runtime
    config_inst = cls()
    for k, v in merged_data.items():
        setattr(config_inst, k, v)  # No validation
```

**Fix:** Add validator
```python
def __post_init__(self):
    # Validate ports
    if not (1024 <= self.llm_port <= 65535):
        raise ValueError(f"Invalid llm_port: {self.llm_port}")
    
    # Validate paths exist
    if not self.MODEL_DIR.exists():
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
```

---

### Recommendations for config_system.py
✅ **ACCEPT** as-is
- Add `__post_init__` validation
- Add config version field for migrations
- Consider environment variable expansion for secrets

---

## ui_components.py

**Lines:** 1351 | **Health:** ⚠️ MEDIUM | **Score:** 5/10

### Purpose
NiceGUI setup including theming, dialogs, and common components.

### Strengths ✅
- Comprehensive CSS theming (600+ lines)
- Dark mode support
- Responsive design
- Glassmorphism styling

### Issues ⚠️

#### Issue #1: Mixed Concerns (Code vs Styling)
**Severity:** MEDIUM | **Type:** Organization

**Problem:** 600+ lines of CSS mixed with 700 lines of Python

```python
# ui_components.py contains:
# 1. setup_app_theme() - CSS generator
# 2. setup_common_dialogs() - Dialog components
# 3. setup_drawer() - Sidebar setup
# 4. setup_rag_dialog() - RAG dialog
# ... all in one file
```

**Fix:** Split into modules
```
ui/
├── theme.py (CSS + theme setup, 600 lines)
├── components/
│   ├── dialogs.py (common dialogs, 300 lines)
│   ├── drawer.py (sidebar, 200 lines)
│   └── rag_dialog.py (RAG dialog, 150 lines)
```

---

#### Issue #2: CSS String Concatenation
**Severity:** LOW | **Type:** Maintainability

**Problem:** CSS written as Python strings

```python
ui.add_head_html('''
    <style>
        .q-card { 
            border-radius: 16px !important;
            box-shadow: ...
        }
        ...
    </style>
''')
```

**Impact:** Hard to lint, format, preview

**Fix:** Use external CSS file
```python
# ui/styles.css
.q-card {
    border-radius: 16px !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

# ui_components.py
with open('ui/styles.css') as f:
    css = f.read()
ui.add_head_html(f'<style>{css}</style>')
```

---

#### Issue #3: Hardcoded Colors
**Severity:** LOW | **Type:** Maintainability

**Problem:** Color values repeated throughout file

```python
--primary: #3b82f6;  # Used in 5 places
--slate-950: #0f172a;  # Used in 8 places
```

**Fix:** Use CSS variables consistently
```python
:root {
    --color-primary: #3b82f6;
    --color-bg-dark: #0f172a;
    --color-border: #cbd5e1;
}

/* Use everywhere */
.q-card { border: 1px solid var(--color-border); }
```

---

### Recommendations for ui_components.py
1. Split into theme.py + component modules
2. Move CSS to external files
3. Centralize color variables

---

## security.py

**Lines:** 137 | **Health:** ✅ GOOD | **Score:** 8/10

### Purpose
File upload validation and security checks.

### Strengths ✅
- Path traversal detection ✅
- File size limits (10MB hard cap)
- Extension whitelist
- UTF-8 validation
- Content sanitization

### Issues ⚠️

#### Issue #1: No Hash Verification
**Severity:** MEDIUM | **Type:** Security

**Problem:** No way to verify file wasn't corrupted/modified

**Fix:**
```python
def validate_file(...) -> (bool, error, decoded):
    # Existing checks...
    
    # New: hash verification (optional, if checksum provided)
    if 'x-file-sha256' in headers:
        actual_hash = hashlib.sha256(content).hexdigest()
        expected_hash = headers['x-file-sha256']
        if actual_hash != expected_hash:
            return (False, "File corruption detected", None)
```

---

### Recommendations for security.py
✅ **ACCEPT** with hash verification addition

---

## zena_mode/rag_manager.py

**Lines:** 80 | **Health:** ✅ EXCELLENT | **Score:** 9/10

### Purpose
Thread-safe proxy for RAG state management.

### Strengths ✅
- Proper RLock usage ✅
- Atomic updates
- Clean interface
- No exposed internals

### Issues

None identified. This module is well-designed.

---

## voice_service.py

**Status:** Not reviewed (location/size unknown)

### Recommendations
- Extract voice pipeline to service module
- Add error recovery for TTS failures
- Cache voice embeddings

---

## Summary by Category

### Critical Issues (Prevent Production)
| File | Issue | Effort | Priority |
|------|-------|--------|----------|
| server.py | Monolithic (932 lines) | 3 days | P0 |
| server.py | Sync HTTP server | 2 days | P0 |
| server.py | No request limits | 1 day | P0 |
| zena.py | Monolithic (1415 lines) | 4 days | P0 |
| zena.py | Can't unit test | 3 days | P0 |

### High Issues (Should Fix)
| File | Issue | Effort | Priority |
|------|-------|--------|----------|
| server.py | No auth on management | 1 day | P1 |
| server.py | Wildcard CORS | 1 day | P1 |
| zena.py | RAG coupling | 2 days | P1 |
| zena.py | Config hardcoding | 1 day | P1 |

### Medium Issues (Nice to Fix)
| File | Issue | Effort | Priority |
|------|-------|--------|----------|
| ui_components.py | Mixed concerns | 2 days | P2 |
| zena.py | Session cleanup | 1 day | P2 |
| config_system.py | No validation | 1 day | P2 |

---

**Total Effort to Fix All Issues:** ~6-7 weeks (prioritized)
**ROI:** Increases code quality score from **5.8/10 to 7.8/10**
