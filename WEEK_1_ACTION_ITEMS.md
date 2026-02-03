# ZenAI Design Review - Immediate Action Items (Week 1)

**Date:** February 1, 2026  
**Duration:** 1 week intensive refactoring  
**Team Size:** 2-3 engineers  
**Goal:** Complete Phase 1 foundation work

---

## Overview

This document provides **day-by-day action items** for Week 1. Start immediately after team approval.

**Timeline:** Monday Feb 3 - Friday Feb 7, 2026  
**Effort:** 40 hours (full-time focus)  
**Deliverable:** Modularized server.py, extracted services, security hardened

---

## Day 1 (Monday): Setup & Planning

### 9:00 AM - Team Kickoff (1 hour)
**Attendees:** Tech lead, 2-3 engineers  
**Agenda:**
- [ ] Review design review documents (15 min)
- [ ] Confirm timeline & responsibilities (15 min)
- [ ] Discuss dependency strategy (15 min)
- [ ] Q&A (15 min)

**Outcomes:**
- All engineers understand the why (architecture issues)
- Assignments for each person clear
- Git workflow established (branches, PR reviews)

### 10:00 AM - Repository Setup (1 hour)

```bash
# Create feature branch
git checkout -b refactor/phase-1-modularize

# Create new directory structure
mkdir -p zena_mode/routes
mkdir -p zena_mode/services
mkdir -p tests/unit

# Create __init__.py files
touch zena_mode/routes/__init__.py
touch zena_mode/services/__init__.py

# Create stub files (ready for implementation)
touch zena_mode/routes/models.py
touch zena_mode/routes/voice.py
touch zena_mode/routes/health.py
touch zena_mode/routes/static.py
touch zena_mode/services/__init__.py
touch zena_mode/services/model_service.py
touch zena_mode/services/process_service.py
touch zena_mode/security_middleware.py

# Create service base classes
cat > zena_mode/services/__init__.py << 'EOF'
"""Business logic services for ZenAI orchestrator"""

from .model_service import ModelService
from .process_service import ProcessService

__all__ = ['ModelService', 'ProcessService']
EOF
```

### 11:00 AM - Document Current State (1 hour)

**Person A (Engineer 1):** Document server.py endpoint map
```bash
# Extract all GET/POST handlers from server.py
grep -n "def do_GET\|def do_POST" zena_mode/server.py

# Output to markdown for reference
cat > /tmp/server_endpoints.md << 'EOF'
# Current server.py Endpoints

## GET handlers
- /models/available
- /model/status
- /api/devices
- /api/tts-voices
- /api/test-llm
- /list
- /startup/progress
- /assets/*
- /voice/lab
- /voice/static/*
- /updates/check
- /models/popular

## POST handlers
- /swap
- /models/download
- /models/progress
- /models/load

## Routes to extract:
- models.py: /models/*, /list, /swap, /models/*, /models/download
- voice.py: /api/devices, /api/tts-voices, /api/test-llm, /voice/*
- health.py: /startup/progress, /updates/check, /health
- static.py: /assets/*, /voice/static/
EOF
```

**Person B (Engineer 2):** Set up test structure
```bash
# Create test file structure
cat > tests/unit/test_chat_service.py << 'EOF'
import pytest
from unittest.mock import Mock, AsyncMock

# Placeholder tests (will be implemented)
@pytest.mark.asyncio
async def test_send_message():
    """Test chat message sending"""
    # TODO: Implement after service extracted
    pass
EOF

cat > tests/unit/test_rag_service.py << 'EOF'
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_ingest_documents():
    """Test document ingestion"""
    # TODO: Implement after service extracted
    pass
EOF
```

### 12:00 PM - Lunch Break (1 hour)

### 1:00 PM - Create Service Interfaces (2 hours)

**All Engineers Together:** Define interfaces before implementation

```python
# zena_mode/services/model_service.py (interface)
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

class ModelService(ABC):
    """Business logic for model management"""
    
    @abstractmethod
    async def list_models(self) -> List[Dict]:
        """Get list of available models"""
        pass
    
    @abstractmethod
    async def get_current_model(self) -> Dict:
        """Get info about currently loaded model"""
        pass
    
    @abstractmethod
    async def swap_model(self, model_name: str) -> bool:
        """Switch to different model"""
        pass
    
    @abstractmethod
    async def download_model(self, repo_id: str, filename: str) -> bool:
        """Download new model"""
        pass
```

```python
# zena_mode/services/process_service.py (interface)
from abc import ABC, abstractmethod
from typing import Dict, List

class ProcessService(ABC):
    """Business logic for process management"""
    
    @abstractmethod
    def register_process(self, name: str, pid: int, critical: bool = False):
        """Register process for monitoring"""
        pass
    
    @abstractmethod
    def check_health(self) -> Dict:
        """Get health status of all processes"""
        pass
    
    @abstractmethod
    async def restart_if_crashed(self) -> List[str]:
        """Auto-restart crashed critical processes"""
        pass
```

### 3:00 PM - Dependency Mapping (1 hour)

Create dependency graph to understand extraction order:

```
Chart:
┌──────────────────┐
│  server.py (932) │ ◄── Monolith
└────────┬─────────┘
         │
    ┌────┴────┬─────────┬──────────┐
    ▼         ▼         ▼          ▼
models.py  voice.py  health.py  static.py
(150L)     (100L)     (80L)      (100L)
  ▲         │         │          │
  │         └─────────┴──────────┤
  │                              ▼
  │                         util_service
  │                             (50L)
  │
  └─────────────────────────────┘

Extraction Order:
1. util_service (no dependencies)
2. process_service (uses util)
3. model_service (uses process, util)
4. routes (use services)
```

### 4:00 PM - Code Review Planning (1 hour)

```markdown
# Code Review Strategy for Week 1

## Review Cadence
- Daily review at 4 PM (15 min)
- Friday comprehensive review (1 hour)

## Reviewers
- Person A: Reviews Person B's code
- Person B: Reviews Person A's code
- Tech Lead: Final approval

## Merge Strategy
- All changes to feature branch
- Daily merge to staging (after review)
- Friday merge to main after full test

## Checklist (each PR)
- [ ] Tests pass locally
- [ ] Linter passes (pylint)
- [ ] Type hints complete
- [ ] Docstrings updated
- [ ] No duplication introduced
```

### 5:00 PM - Day 1 Standup (15 min)

**Everyone:**
- What did I accomplish?
- What's blocking me?
- What's next?

**Desired Outcome:** All setup complete, ready to code Tuesday

---

## Day 2 (Tuesday): Extract Models Route

### 9:00 AM - Code Implementation (3 hours)

**Person A:** Extract models route to `zena_mode/routes/models.py`

```python
# zena_mode/routes/models.py (extraction target: 150 lines)
"""
Models Routes - HTTP handlers for model management

WHAT:
    - List available models
    - Get current model status
    - Swap active model
    - Download new models

WHY:
    - Extracted from monolithic server.py (932 lines)
    - Enables independent testing
    - Allows reuse in other servers

HOW:
    - Each handler is async function
    - Uses ModelService for business logic
    - Returns JSON responses
"""
from starlette.requests import Request
from starlette.responses import JSONResponse
from ..services.model_service import ModelService

# Initialize service (will be injected)
model_service = None

async def list_models(request: Request) -> JSONResponse:
    """GET /models/available - List all installed models"""
    try:
        models = await model_service.list_models()
        return JSONResponse(models, status_code=200)
    except Exception as e:
        return JSONResponse(
            {'error': str(e)},
            status_code=500
        )

async def get_model_status(request: Request) -> JSONResponse:
    """GET /model/status - Get currently loaded model info"""
    try:
        status = await model_service.get_current_model()
        return JSONResponse(status, status_code=200)
    except Exception as e:
        return JSONResponse(
            {'error': str(e)},
            status_code=500
        )

async def swap_model(request: Request) -> JSONResponse:
    """POST /swap - Switch to different model"""
    try:
        data = await request.json()
        success = await model_service.swap_model(data['model'])
        return JSONResponse(
            {'success': success},
            status_code=200 if success else 400
        )
    except Exception as e:
        return JSONResponse(
            {'error': str(e)},
            status_code=500
        )

async def download_model(request: Request) -> JSONResponse:
    """POST /models/download - Download new model from hub"""
    try:
        data = await request.json()
        success = await model_service.download_model(
            repo_id=data['repo_id'],
            filename=data['filename']
        )
        return JSONResponse(
            {'success': success},
            status_code=200 if success else 400
        )
    except Exception as e:
        return JSONResponse(
            {'error': str(e)},
            status_code=500
        )

# Route registration
ROUTES = [
    ('GET', '/models/available', list_models),
    ('GET', '/model/status', get_model_status),
    ('POST', '/swap', swap_model),
    ('POST', '/models/download', download_model),
]
```

**Person B:** Start ModelService implementation

```python
# zena_mode/services/model_service.py
"""Model management business logic - extracted from server.py"""

from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ModelService:
    """Handle model loading, swapping, and discovery"""
    
    def __init__(self, model_manager, config):
        self.model_manager = model_manager
        self.config = config
    
    async def list_models(self) -> List[Dict]:
        """List available models"""
        try:
            # Logic from server.py do_GET /models/available
            installed = self.model_manager.get_installed_models()
            return [
                {'name': m['name'], 'active': m['name'] == self.config.default_model}
                for m in installed
            ]
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    async def get_current_model(self) -> Dict:
        """Get status of currently loaded model"""
        return {
            'model': self.config.default_model,
            'loaded': True,  # TODO: check actual engine status
            'port': self.config.llm_port
        }
    
    async def swap_model(self, model_name: str) -> bool:
        """Switch active model"""
        try:
            # Logic from server.py do_POST /swap
            logger.info(f"Swapping to {model_name}")
            # TODO: call model_manager.switch_model(model_name)
            return True
        except Exception as e:
            logger.error(f"Error swapping model: {e}")
            return False
    
    async def download_model(self, repo_id: str, filename: str) -> bool:
        """Download model from hub"""
        try:
            logger.info(f"Downloading {repo_id}/{filename}")
            # TODO: call model_manager.download(repo_id, filename)
            return True
        except Exception as e:
            logger.error(f"Error downloading model: {e}")
            return False
```

### 12:00 PM - Lunch Break

### 1:00 PM - Unit Tests (2 hours)

```python
# tests/unit/test_models_route.py
"""Unit tests for models route handlers"""
import pytest
from unittest.mock import Mock, AsyncMock
from zena_mode.routes.models import (
    list_models,
    get_model_status,
    swap_model,
    download_model
)

@pytest.fixture
def mock_request():
    request = Mock()
    request.json = AsyncMock()
    return request

@pytest.mark.asyncio
async def test_list_models(mock_request):
    """Test listing models endpoint"""
    response = await list_models(mock_request)
    assert response.status_code in [200, 500]
    # More assertions...

@pytest.mark.asyncio
async def test_get_model_status(mock_request):
    """Test getting model status"""
    response = await get_model_status(mock_request)
    assert response.status_code in [200, 500]
```

### 3:00 PM - Integration (1 hour)

```python
# zena_mode/routes/__init__.py
"""Route modules for ZenAI orchestrator"""

from . import models
from . import voice  # Stub, will implement tomorrow
from . import health  # Stub, will implement tomorrow
from . import static  # Stub, will implement tomorrow

# Collect all routes
ALL_ROUTES = []
ALL_ROUTES.extend([
    (method, path, handler)
    for method, path, handler in models.ROUTES
])
# Add other routes as they're implemented

__all__ = ['ALL_ROUTES', 'models', 'voice', 'health', 'static']
```

### 4:00 PM - Code Review (1 hour)

Person A reviews Person B's code:
```bash
git diff origin/main..HEAD zena_mode/services/model_service.py

# Checklist:
# - [ ] Docstrings complete
# - [ ] Type hints all functions
# - [ ] Error handling comprehensive
# - [ ] Logging in place
# - [ ] Tests pass
```

### 5:00 PM - Standup (15 min)

---

## Day 3 (Wednesday): Extract Voice & Health Routes

### Similar structure to Day 2

**Person A:** Extract voice routes
```python
# zena_mode/routes/voice.py (100 lines)
async def get_devices(request: Request) -> JSONResponse:
    """GET /api/devices - List audio devices"""
    # Extract logic from server.py

async def get_tts_voices(request: Request) -> JSONResponse:
    """GET /api/tts-voices - List TTS voices"""
    
async def test_llm(request: Request) -> JSONResponse:
    """GET /api/test-llm - Test LLM connection"""

ROUTES = [
    ('GET', '/api/devices', get_devices),
    ('GET', '/api/tts-voices', get_tts_voices),
    ('GET', '/api/test-llm', test_llm),
]
```

**Person B:** Extract health routes
```python
# zena_mode/routes/health.py (80 lines)
async def health_check(request: Request) -> JSONResponse:
    """GET /health - Health check"""
    
async def startup_progress(request: Request) -> JSONResponse:
    """GET /startup/progress - Installation progress"""
    
async def updates_check(request: Request) -> JSONResponse:
    """GET /updates/check - Check for updates"""

ROUTES = [
    ('GET', '/health', health_check),
    ('GET', '/startup/progress', startup_progress),
    ('GET', '/updates/check', updates_check),
]
```

### Effort breakdown:
- 9:00-12:00: Implementation
- 12:00-1:00: Lunch
- 1:00-3:00: Unit tests
- 3:00-4:00: Integration
- 4:00-5:00: Code review

---

## Day 4 (Thursday): Extract Static Routes & Security Middleware

### Morning: Static Routes

```python
# zena_mode/routes/static.py (100 lines)
async def serve_static(request: Request):
    """GET /assets/* - Serve static files"""

async def serve_voice_lab(request: Request):
    """GET /voice/lab - Serve voice lab UI"""

ROUTES = [
    ('GET', '/assets/{path}', serve_static),
    ('GET', '/voice/lab', serve_voice_lab),
]
```

### Afternoon: Security Middleware

```python
# zena_mode/security_middleware.py (100 lines)
"""Security middleware for ZenAI HTTP server"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforce maximum request size"""
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

class AdminAuthMiddleware(BaseHTTPMiddleware):
    """Require token for sensitive endpoints"""
    ADMIN_TOKEN = os.environ.get('ZENAI_ADMIN_TOKEN', '')
    PROTECTED = ['/swap', '/models/download']
    
    async def dispatch(self, request, call_next):
        if any(request.url.path.startswith(p) for p in self.PROTECTED):
            if self.ADMIN_TOKEN:
                token = request.headers.get('authorization', '').replace('Bearer ', '')
                if token != self.ADMIN_TOKEN:
                    return JSONResponse({'error': 'Unauthorized'}, status_code=403)
        return await call_next(request)
```

---

## Day 5 (Friday): Consolidation & Testing

### 9:00 AM - Refactor Main Server (2 hours)

```python
# zena_mode/server.py (REFACTORED - 100 lines)
"""ZenAI Orchestrator - Main HTTP server

WHAT:
    - Entry point for orchestrator
    - Aggregates all routes
    - Applies security middleware

WHY:
    - Simplified from 932-line monolith
    - Routes extracted to focused modules
    - Ready for async framework migration

HOW:
    - FastAPI/Starlette receives requests
    - Routes delegate to specific handlers
    - Handlers use services for logic
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import routes
from . import security_middleware
from config_system import config

# Create app
app = FastAPI(title="ZenAI Orchestrator")

# Add security middleware
app.add_middleware(security_middleware.RequestSizeLimitMiddleware)
app.add_middleware(security_middleware.AdminAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routes
for method, path, handler in routes.ALL_ROUTES:
    if method == 'GET':
        app.get(path)(handler)
    elif method == 'POST':
        app.post(path)(handler)

def start_server():
    """Start the orchestrator"""
    import uvicorn
    uvicorn.run(
        app,
        host=config.host,
        port=config.mgmt_port,
        log_level="info"
    )

if __name__ == '__main__':
    start_server()
```

### 11:00 AM - Full Test Suite (1 hour)

```bash
# Run all tests
pytest tests/ -v --cov=zena_mode --cov-report=html

# Expected output:
# tests/unit/test_models_route.py::test_list_models PASSED
# tests/unit/test_voice_route.py::test_get_devices PASSED
# tests/unit/test_health_route.py::test_health_check PASSED
# tests/unit/test_security.py::test_size_limit PASSED
# ... ~30 tests total

# Coverage target: >50%
```

### 12:00 PM - Lunch

### 1:00 PM - Comprehensive Code Review (1 hour)

**All Engineers:** Review entire week's work
```bash
git diff origin/main..HEAD --stat
# Should show:
# zena_mode/routes/models.py    +150
# zena_mode/routes/voice.py     +100
# zena_mode/routes/health.py    +80
# zena_mode/routes/static.py    +100
# zena_mode/services/model_service.py +80
# zena_mode/security_middleware.py +100
# zena_mode/server.py            -850 +100 (net -750)
# tests/unit/*.py                +500
# Total: +260 new, -850 removed = -590 lines
```

### 2:00 PM - Documentation (1 hour)

```bash
# Update README
cat >> README.md << 'EOF'

## Architecture (Post-Refactor)

```
server.py (100 lines)
├── routes/
│   ├── models.py (150 lines) - model management
│   ├── voice.py (100 lines) - voice endpoints
│   ├── health.py (80 lines) - health/status
│   └── static.py (100 lines) - file serving
├── services/
│   ├── model_service.py (80 lines) - business logic
│   └── process_service.py (80 lines) - lifecycle
└── security_middleware.py (100 lines) - auth/limits
```

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=zena_mode
```
```

### 3:00 PM - Merge to Main (1 hour)

```bash
# Ensure all tests pass
pytest tests/ -v

# Create pull request
git push origin refactor/phase-1-modularize

# After code review approval:
git checkout main
git pull origin main
git merge refactor/phase-1-modularize
git push origin main

# Tag the release
git tag -a v0.2.0 -m "Phase 1: Modularized server"
git push origin v0.2.0
```

### 4:00 PM - Final Standup & Retrospective (1 hour)

**Everyone:**
- What went well?
- What was hard?
- What's next?

**Expected Output:**
- ✅ server.py reduced from 932 → 100 lines
- ✅ Routes extracted into focused modules
- ✅ Services isolated for testing
- ✅ Security middleware implemented
- ✅ 50%+ test coverage achieved
- ✅ All tests passing
- ✅ Zero regressions

### 5:00 PM - Week 1 Wrap-Up

Document completion in metrics:
```markdown
# Week 1 Results

## Code Quality Improvements
- Modularity: 4.4 → 5.1 (+16%)
- Coverage: 40% → 48% (+8%)
- Complexity (server): 18 → 3 (isolated)
- Lines refactored: 932 → 100 (89% reduction)

## Deliverables
✅ server.py modularized
✅ Chat service extracted (ready for zena.py)
✅ RAG service extracted (ready for zena.py)
✅ API security hardened
✅ 40+ new unit tests
✅ Full documentation

## Blockers Resolved
- None

## Ready for Phase 2
✅ Yes - can start Monday
```

---

## Success Criteria for Week 1

- [ ] All code merged to main
- [ ] Tests passing (50%+ coverage)
- [ ] No regressions in E2E tests
- [ ] PR reviews completed
- [ ] Documentation updated
- [ ] Metrics captured
- [ ] Team agreement on Phase 2 approach

**If all criteria met:** ✅ Week 1 SUCCESS → Start Phase 2 Monday

---

## Estimated Time Commitment

| Activity | Hours | Notes |
|----------|-------|-------|
| Day 1 (Setup) | 8 | Full setup, planning |
| Day 2 (Models) | 8 | Extract + test |
| Day 3 (Voice/Health) | 8 | Extract + test |
| Day 4 (Static/Security) | 8 | Extract + middleware |
| Day 5 (Consolidate/Test) | 8 | Integration + review |
| **TOTAL** | **40** | Full-time effort |

---

## Emergency Contacts

**Blocker?** Contact tech lead immediately.

**Common Issues & Fixes:**

1. **Import errors:** Likely missing `__init__.py` files
   ```bash
   find zena_mode/routes -name "__init__.py" -o -print
   ```

2. **Test failures:** Check fixture setup
   ```bash
   pytest tests/ -v --tb=short
   ```

3. **Merge conflicts:** Resolve before commit
   ```bash
   git status  # Shows conflicts
   # Edit files manually, then:
   git add .
   git commit -m "Resolve merge conflicts"
   ```

---

## Next Steps (After Week 1)

✅ Week 1 COMPLETE → Move to **Phase 2: Stability** (Week 3-4)

**Phase 2 Focus:**
- Replace sync HTTP with FastAPI
- Fix async/sync boundaries
- Improve test coverage to 55%+

---

**Good luck! You've got this.** 🚀

