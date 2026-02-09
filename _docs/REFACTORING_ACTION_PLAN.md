# ZenAI Refactoring Action Plan

**Created:** February 1, 2026  
**Status:** Ready to Execute  
**Total Duration:** 6-8 weeks (4 weeks priority 1-2, 2-4 weeks priority 3-4)

---

## Phase 1: Foundation (Weeks 1-2)

### Week 1: Modularize server.py

**Goal:** Break 932-line monolith into focused route handlers + services

**Day 1: Plan & Prepare**
- [ ] Create directory structure
- [ ] Set up new modules with stubs
- [ ] Copy existing tests

```bash
mkdir -p zena_mode/routes zena_mode/services
touch zena_mode/routes/__init__.py
touch zena_mode/routes/models.py
touch zena_mode/routes/voice.py
touch zena_mode/routes/health.py
touch zena_mode/routes/static.py
touch zena_mode/services/__init__.py
touch zena_mode/services/model_service.py
touch zena_mode/services/process_service.py
```

**Day 2-3: Extract Models Routes**

Move model-related endpoints to `routes/models.py`:
```python
# zena_mode/routes/models.py (150 lines)
from starlette.responses import JSONResponse

async def list_models(request):
    """GET /models/available - List installed models"""
    # Logic from server.py
    
async def get_model_status(request):
    """GET /model/status - Get current model info"""
    # Logic from server.py

async def swap_model(request):
    """POST /swap - Switch active model"""
    # Logic from server.py

async def download_model(request):
    """POST /models/download - Download new model"""
    # Logic from server.py

# Routes list for registration
ROUTES = [
    ('GET', '/models/available', list_models),
    ('GET', '/model/status', get_model_status),
    ('POST', '/swap', swap_model),
    ('POST', '/models/download', download_model),
]
```

**Day 4: Extract Voice Routes**

Move voice-related endpoints to `routes/voice.py`:
```python
# zena_mode/routes/voice.py (100 lines)
async def get_devices(request):
    """GET /api/devices - List audio devices"""

async def get_tts_voices(request):
    """GET /api/tts-voices - List TTS voices"""

async def test_llm(request):
    """GET /api/test-llm - Test LLM connection"""

ROUTES = [
    ('GET', '/api/devices', get_devices),
    ('GET', '/api/tts-voices', get_tts_voices),
    ('GET', '/api/test-llm', test_llm),
]
```

**Day 5-6: Extract Health Routes**

Move health/diagnostics to `routes/health.py`:
```python
# zena_mode/routes/health.py (80 lines)
async def health_check(request):
    """GET /health - Health check"""

async def startup_progress(request):
    """GET /startup/progress - Installation progress"""

async def updates_check(request):
    """GET /updates/check - Check for updates"""

ROUTES = [
    ('GET', '/health', health_check),
    ('GET', '/startup/progress', startup_progress),
    ('GET', '/updates/check', updates_check),
]
```

**Day 7: Extract Static Routes**

Move file serving to `routes/static.py`:
```python
# zena_mode/routes/static.py (100 lines)
async def serve_static(request):
    """GET /assets/* - Serve static files"""

async def serve_voice_lab(request):
    """GET /voice/lab - Serve voice lab UI"""

ROUTES = [
    ('GET', '/assets/{path}', serve_static),
    ('GET', '/voice/lab', serve_voice_lab),
]
```

**Day 8: Consolidate New Server**

Update main server.py:
```python
# zena_mode/server.py (100 lines, down from 932)
from starlette.applications import Starlette
from starlette.routing import Route

from . import routes

# Collect all routes
all_routes = []
all_routes.extend(routes.models.ROUTES)
all_routes.extend(routes.voice.ROUTES)
all_routes.extend(routes.health.ROUTES)
all_routes.extend(routes.static.ROUTES)

# Convert to Starlette Route objects
starlette_routes = [
    Route(path, endpoint, methods=[method])
    for method, path, endpoint in all_routes
]

app = Starlette(routes=starlette_routes)

def start_server():
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.mgmt_port)
```

**Deliverable:** server.py is now 100 lines with clear separation

---

### Week 1: Add API Security

**Goal:** Lock down management endpoints

**Files to Modify:**
- `zena_mode/server.py` - add middleware
- Create `zena_mode/security_middleware.py` - new module

**Implementation:**

```python
# zena_mode/security_middleware.py (80 lines)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os

class SizeLimitMiddleware(BaseHTTPMiddleware):
    MAX_REQUEST_SIZE = 1024 * 1024  # 1MB
    
    async def dispatch(self, request, call_next):
        if request.method in ('POST', 'PUT'):
            content_length = request.headers.get('content-length')
            if content_length and int(content_length) > self.MAX_REQUEST_SIZE:
                return JSONResponse(
                    {'error': 'Payload too large'},
                    status_code=413
                )
        return await call_next(request)

class AuthTokenMiddleware(BaseHTTPMiddleware):
    PROTECTED_PATHS = ['/swap', '/models/download']
    ADMIN_TOKEN = os.environ.get('ZENAI_ADMIN_TOKEN', '')
    
    async def dispatch(self, request, call_next):
        if any(request.url.path.startswith(p) for p in self.PROTECTED_PATHS):
            if self.ADMIN_TOKEN:  # Only enforce if token set
                token = request.headers.get('authorization', '').replace('Bearer ', '')
                if token != self.ADMIN_TOKEN:
                    return JSONResponse({'error': 'Unauthorized'}, status_code=403)
        return await call_next(request)

class CORSMiddleware(BaseHTTPMiddleware):
    ALLOWED_ORIGINS = ['http://localhost:8080', 'http://127.0.0.1:8080']
    
    async def dispatch(self, request, call_next):
        if request.method == 'OPTIONS':
            return JSONResponse({}, headers=self._get_cors_headers(request))
        response = await call_next(request)
        for header, value in self._get_cors_headers(request).items():
            response.headers[header] = value
        return response
    
    def _get_cors_headers(self, request):
        origin = request.headers.get('origin', '')
        if origin in self.ALLOWED_ORIGINS:
            return {'Access-Control-Allow-Origin': origin}
        return {}
```

```python
# zena_mode/server.py - add middleware
app = Starlette(routes=routes)
app.add_middleware(SizeLimitMiddleware)
app.add_middleware(AuthTokenMiddleware)
app.add_middleware(CORSMiddleware)
```

**Deliverable:** Management endpoints are now protected

---

### Week 2: Extract Chat Service from zena.py

**Goal:** Separate business logic from UI

**New File: `services/chat_service.py`**

```python
# ui/services/chat_service.py (150 lines)
from typing import AsyncGenerator, Optional
from async_backend import AsyncZenAIBackend

class ChatMessage:
    def __init__(self, role: str, content: str, session_id: str):
        self.role = role
        self.content = content
        self.session_id = session_id
        self.timestamp = time.time()

class ChatService:
    """Pure business logic for chat operations"""
    
    def __init__(self, backend: AsyncZenAIBackend, memory_service):
        self.backend = backend
        self.memory = memory_service
    
    async def send_message(
        self,
        text: str,
        session_id: str,
        include_rag: bool = True
    ) -> ChatMessage:
        """Send user message and get response"""
        # No UI operations here - pure logic
        msg = ChatMessage(role='user', content=text, session_id=session_id)
        await self.memory.add_message(msg)
        return msg
    
    async def stream_response(
        self,
        messages: List[ChatMessage],
        cancellation_event: Optional[asyncio.Event] = None
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response"""
        async for chunk in self.backend.send_message_async(
            text=messages[-1].content,
            cancellation_event=cancellation_event
        ):
            yield chunk
    
    async def get_history(self, session_id: str) -> List[ChatMessage]:
        """Get conversation history"""
        return await self.memory.get_messages(session_id)
    
    async def clear_history(self, session_id: str):
        """Clear conversation"""
        await self.memory.clear(session_id)
```

**Update zena.py to use service:**

```python
# zena.py - BEFORE (can't test)
async def send_chat_message(text):
    ui_state.status_text.set_text("Sending...")
    response = await async_backend.send_message_async(text)
    ui_state.chat_log.refresh()

# zena.py - AFTER (testable)
async def on_send_click():
    msg = await chat_service.send_message(input.value, ui_state.session_id)
    
    # Display user message
    display_message(msg)
    
    # Stream response
    response_text = ""
    async for chunk in chat_service.stream_response(ui_state.messages):
        response_text += chunk
        # Update UI incrementally
        update_response_display(response_text)
```

**Deliverable:** Chat logic can now be unit tested independently

---

### Week 2: Extract RAG Service

**Goal:** Decouple RAG from UI

**New File: `zena_mode/rag_service.py`**

```python
# zena_mode/rag_service.py (200 lines)
from pathlib import Path
from typing import List, Optional
from .rag_manager import RAGManager

class Document:
    def __init__(self, content: str, source: str, metadata: dict = None):
        self.content = content
        self.source = source
        self.metadata = metadata or {}

class RAGQuery:
    def __init__(self, query: str, results: List[Document]):
        self.query = query
        self.results = results

class RAGService:
    """Business logic for RAG operations"""
    
    def __init__(self, manager: RAGManager, cache_dir: Path):
        self.manager = manager
        self.cache_dir = cache_dir
    
    async def ingest_documents(
        self,
        documents: List[Document],
        session_id: str = None
    ) -> dict:
        """Ingest documents into index"""
        # Validate, chunk, embed
        with self.manager:
            self.manager.build_index(documents)
        
        return {
            'count': len(documents),
            'total_chars': sum(len(d.content) for d in documents),
            'status': 'success'
        }
    
    async def query(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5
    ) -> RAGQuery:
        """Execute RAG query"""
        with self.manager:
            results = self.manager.hybrid_search(
                query,
                k=top_k,
                similarity_threshold=threshold
            )
        
        return RAGQuery(query=query, results=results)
    
    async def refresh_from_web(self, url: str) -> dict:
        """Scrape and ingest web content"""
        # ... scrape logic
```

**Update zena.py:**

```python
# zena.py - BEFORE (can't test)
async def on_rag_upload(files):
    for file in files:
        docs = await extract_pdf(file)
        rag_system.build_index(docs)
        ui.notify(f"Indexed")

# zena.py - AFTER (testable)
async def on_rag_upload(files):
    docs = await extract_documents(files)
    result = await rag_service.ingest_documents(docs, ui_state.session_id)
    ui.notify(f"Indexed {result['count']} documents")
```

**Deliverable:** RAG service separated from UI

---

## Phase 2: Stability (Weeks 3-4)

### Week 3: Replace Sync HTTP with ASGI

**Goal:** Move to true async framework

**Implementation Plan:**

```bash
pip install fastapi uvicorn
```

Create new `zena_mode/async_server.py`:

```python
# zena_mode/async_server.py (200 lines)
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Add middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/v1/chat/completions')
async def chat_completions(request: Request):
    """Stream LLM responses"""
    payload = await request.json()
    
    async def generate():
        async for chunk in backend.send_message_async(
            text=payload['messages'][-1]['content']
        ):
            yield f"data: {chunk}\n"
    
    return StreamingResponse(generate())

@app.get('/models/available')
async def list_models():
    """List installed models"""
    return get_model_manager().get_installed_models()

@app.post('/swap')
async def swap_model(request: Request):
    """Swap active model"""
    if not check_admin_token(request):
        raise HTTPException(status_code=403)
    
    data = await request.json()
    success = await set_active_model(data['model'])
    return {'success': success}

def start_async_server():
    config.validate_environment()
    uvicorn.run(
        app,
        host=config.host,
        port=config.mgmt_port,
        log_level="info"
    )

if __name__ == '__main__':
    start_async_server()
```

**Migrate server.py gradually:**
- Keep old implementation for compatibility
- New code uses FastAPI
- Deprecate BaseHTTPRequestHandler use

**Deliverable:** Async server ready for production

---

### Week 3: Fix Async/Sync Boundaries

**Goal:** Enforce pure async event loop

**Identify issues:**

```bash
# Find blocking calls
grep -n "time.sleep\|subprocess\|requests\." zena.py
grep -n "synchronous\|blocking" async_backend.py
```

**Replace blocking with async:**

```python
# BEFORE (blocking)
import time
time.sleep(1)

# AFTER (async)
import asyncio
await asyncio.sleep(1)

# BEFORE (blocking)
import requests
response = requests.get(url)

# AFTER (async)
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get(url)

# BEFORE (blocking subprocess)
subprocess.run(['model', 'load'])

# AFTER (async)
process = await asyncio.create_subprocess_exec('model', 'load')
await process.wait()
```

**Add validation:**

```python
# utils/async_validator.py
BLOCKING_FUNCTIONS = ['time.sleep', 'requests.get', 'subprocess.run']

def check_event_loop_safety():
    """Verify no blocking calls in async context"""
    # Can run in tests
```

**Deliverable:** No blocking calls in event loop

---

### Week 4: Create RAG Service Boundary

**Goal:** Formalize RAG as independent service

**New File: `zena_mode/rag_service_v2.py`**

```python
# Complete RAG service with:
# - Document ingestion pipeline
# - Query with reranking
# - Cache management
# - Stats/monitoring
# - Graceful degradation
```

**Deliverable:** RAG fully decoupled from UI

---

## Phase 3: Modularity (Weeks 5-6)

### Week 5: Break Up zena.py

**Create new structure:**

```
ui/
├── main.py (page layout only, 150 lines)
├── pages/
│   ├── __init__.py
│   ├── chat_page.py (chat UI)
│   ├── sidebar.py (left drawer)
│   └── settings_page.py (settings)
├── components/
│   ├── __init__.py
│   ├── chat_bubble.py (message display)
│   ├── input_area.py (text input)
│   └── dialogs.py (modal dialogs)
└── state.py (UIState class)
```

**Extract chat page:**

```python
# ui/pages/chat_page.py (200 lines)
from nicegui import ui

async def setup_chat_page(ui_state):
    """Setup chat UI"""
    
    with ui.column().classes('flex-1'):
        # Chat history
        chat_log = ui.column()
        
        # Input area
        input_area = await setup_input_area(ui_state)
        
        # Events
        async def on_send():
            text = input_area.value
            msg = await chat_service.send_message(text, ui_state.session_id)
            display_message(chat_log, msg)
            
            async for chunk in chat_service.stream_response(...):
                update_display(chat_log, chunk)
```

**Extract sidebar:**

```python
# ui/pages/sidebar.py (150 lines)
async def setup_sidebar(ui_state, rag_service):
    """Setup left sidebar"""
    
    with ui.left_drawer() as drawer:
        # RAG controls
        # Settings button
        # History
        # etc.
```

**Deliverable:** zena.py reduced to 200 lines

---

### Week 5: Extract Keyboard Shortcuts

**New File: `ui/services/keyboard_service.py`**

```python
# ui/services/keyboard_service.py (100 lines)
from dataclasses import dataclass
from typing import Callable

@dataclass
class Shortcut:
    keys: str
    description: str
    handler: Callable

SHORTCUTS = [
    Shortcut('Ctrl+Enter', 'Send message', handle_send_message),
    Shortcut('Ctrl+K', 'Focus search', handle_focus_search),
    Shortcut('Escape', 'Close dialogs', handle_close_dialogs),
    Shortcut('Ctrl+,', 'Open settings', handle_open_settings),
]

def register_shortcuts(ui_state):
    """Register all shortcuts"""
    for shortcut in SHORTCUTS:
        ui.keyboard(shortcut.keys, lambda: shortcut.handler(ui_state))
```

**Deliverable:** Shortcuts centralized and documented

---

### Week 6: Improve Test Coverage

**Goal:** Move from 40% to 70%+ coverage

**Create unit tests:**

```python
# tests/unit/test_chat_service.py (100 lines)
@pytest.mark.asyncio
async def test_send_message():
    service = ChatService(
        backend=MockBackend(),
        memory=MockMemory()
    )
    
    msg = await service.send_message("Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"

@pytest.mark.asyncio
async def test_stream_response():
    service = ChatService(...)
    
    chunks = []
    async for chunk in service.stream_response(...):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    assert "".join(chunks).strip() != ""
```

```python
# tests/unit/test_rag_service.py (100 lines)
@pytest.mark.asyncio
async def test_ingest_documents():
    service = RAGService(MockRAGManager(), Path('/tmp'))
    
    docs = [Document("test", "test.txt")]
    result = await service.ingest_documents(docs)
    
    assert result['count'] == 1
    assert result['status'] == 'success'

@pytest.mark.asyncio
async def test_query():
    service = RAGService(...)
    
    query_result = await service.query("test query")
    assert len(query_result.results) >= 0
```

**Deliverable:** 70%+ code coverage

---

## Phase 4: Enhancement (Weeks 7+)

### Week 7: Input Validation & Security

**Create: `zena_mode/prompt_guardian.py`**

```python
# zena_mode/prompt_guardian.py (150 lines)
import re

class PromptGuardian:
    MAX_LENGTH = 10000
    INJECTION_PATTERNS = [
        r'(ignore|disregard|forget).*instruction',
        r'system.*override',
        # Add more patterns
    ]
    
    @staticmethod
    def sanitize(text: str) -> str:
        # Truncate
        if len(text) > PromptGuardian.MAX_LENGTH:
            text = text[:PromptGuardian.MAX_LENGTH]
        
        # Check for injection
        for pattern in PromptGuardian.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Potential injection detected: {pattern}")
        
        return text
```

**Deliverable:** Injection protection added

---

### Week 8: Process Lifecycle State Machine

**Create: `zena_mode/process_lifecycle.py`**

```python
# zena_mode/process_lifecycle.py (150 lines)
from enum import Enum

class ProcessState(Enum):
    STOPPED = 0
    STARTING = 1
    RUNNING = 2
    STOPPING = 3
    CRASHED = 4

class ProcessLifecycle:
    """Formal state machine for process management"""
    
    def __init__(self, name):
        self.name = name
        self.state = ProcessState.STOPPED
        self.transitions = {
            ProcessState.STOPPED: [ProcessState.STARTING],
            ProcessState.STARTING: [ProcessState.RUNNING, ProcessState.CRASHED],
            ProcessState.RUNNING: [ProcessState.STOPPING, ProcessState.CRASHED],
            ProcessState.STOPPING: [ProcessState.STOPPED],
            ProcessState.CRASHED: [ProcessState.STOPPED, ProcessState.STARTING],
        }
    
    def transition(self, new_state: ProcessState):
        """Execute state transition"""
        if new_state not in self.transitions[self.state]:
            raise InvalidTransition(
                f"{self.name}: {self.state.name} → {new_state.name}"
            )
        self.state = new_state
        logger.info(f"[Lifecycle] {self.name} → {new_state.name}")
```

**Deliverable:** Formal process management

---

## Summary

### Effort Breakdown
- **Phase 1 (Weeks 1-2):** 80 hours (modularize, security, services)
- **Phase 2 (Weeks 3-4):** 60 hours (async, boundaries, RAG service)
- **Phase 3 (Weeks 5-6):** 60 hours (split UI, shortcuts, tests)
- **Phase 4 (Weeks 7+):** 40 hours (validation, lifecycle, optional)

**Total:** ~240 hours (~6 weeks full-time, 12 weeks part-time)

### Quality Improvements
- Lines of code consolidated: 1932 → 1200 (monoliths down)
- Test coverage: 40% → 70%+
- Cyclomatic complexity: reduced by 40%
- Modularity score: 4/10 → 8/10
- Overall quality: 5.8/10 → 7.8/10

### Risk Mitigation
- ✅ Keep old code running during transition
- ✅ Full test suite at each phase
- ✅ Gradual migration (don't rewrite all at once)
- ✅ Feature parity before deprecation

---

## Next Steps

1. **Week 1 Sprint Planning**
   - Schedule modularization of server.py
   - Set up new directory structure
   - Create stubs for all new modules

2. **Week 1 Execution**
   - Break out routes (Days 1-6)
   - Add security middleware (Days 7-8)
   - Validate with tests

3. **Week 2 Execution**
   - Extract chat service
   - Extract RAG service
   - Update UI to use services

4. **Ongoing**
   - Track progress against milestones
   - Run full test suite weekly
   - Document completed modules

---

**Action Items for Today:**
- [ ] Review this plan with team
- [ ] Create Jira/GitHub issues for each phase
- [ ] Set up project board
- [ ] Begin Week 1 sprint planning

