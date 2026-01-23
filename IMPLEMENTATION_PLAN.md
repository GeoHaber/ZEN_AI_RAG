# Implementation Plan - Zena AI Refactoring & Multi-LLM Consensus

**Created:** 2026-01-23
**Status:** Phase 1 Complete ✅

---

## Overview

This document outlines our systematic approach to:
1. **Fix crashes** through methodical debugging
2. **Apply TDD philosophy** to ensure code health
3. **Refactor for maintainability** by eliminating duplicates
4. **Implement multi-LLM consensus** for better answers

---

## Phase 1: Immediate Fixes ✅ COMPLETE

### 1.1 Safe Output (CRITICAL FIX)

**Problem:** In multithreaded contexts, `print()` buffers output and `sys.exit()` terminates before flush → silent crashes

**Solution:**
```python
def safe_print(*args, **kwargs):
    """Thread-safe print with immediate flush."""
    kwargs['flush'] = True
    print(*args, **kwargs)

def safe_exit(code: int = 0, delay: float = 0.5):
    """Exit with buffer flush + delay."""
    sys.stdout.flush()
    sys.stderr.flush()
    time.sleep(delay)  # Give buffers time to flush
    sys.exit(code)
```

**Result:**
- ✅ Replaced 199 print() calls with safe_print()
- ✅ Replaced 19 sys.exit() calls with safe_exit()
- ✅ All error messages now visible before crash

**Files Modified:**
- `start_llm.py` - Added safe_print(), replaced all calls

---

### 1.2 Function Analysis ✅ COMPLETE

**Deliverable:** `FUNCTION_ANALYSIS.md`

**Key Findings:**
- **19 total functions** in start_llm.py
- **0 tested** ❌ (we need TDD!)
- **5 duplicate groups** identified
- **1 untestable function** (start_server() - 280 lines, never returns)

**Critical Issues:**
1. `start_server()` is a 280-line monolith → needs refactoring
2. Duplicate command building logic (90% overlap)
3. Inconsistent logging (mix of safe_print() and logger)
4. Global state everywhere (race conditions)
5. Silent failures (services don't return success/failure)

**Priority Matrix:**
- **HIGH:** 3 functions (easy wins - env_int, safe_print, restart_with_model)
- **MEDIUM:** 5 functions (need mocking)
- **LOW:** 10 functions (complex or network-dependent)
- **UNTESTABLE:** 1 function (needs refactoring first)

---

### 1.3 Multi-LLM Research ✅ COMPLETE

**Deliverable:** `MULTI_LLM_CONSENSUS_RESEARCH.md`

**Your Vision:** "Ping-pong arbitrage" - multiple LLMs debate until consensus

**Validation:** ✅ This is cutting-edge research!
- Matches "Multi-Agent Debate" (Du et al., 2023)
- Similar to "Chain of Verification" (Dhuliawala et al., 2023)
- Used in Constitutional AI (Anthropic)

**Recommended Architecture:**
```python
Round 1: Ask A, B, C independently
Round 2: Show A's answer to B/C → get critiques
Round 3: Show critiques to A → A revises
Round 4+: Repeat until convergence (>90% similarity)
Final: Synthesize best answer
```

**Cost Optimization:**
- **Budget:** Groq + Gemini + Local = $0.001/question
- **Quality:** GPT-4 + Claude + Gemini = $0.06/question
- **Hybrid:** Cheap first, expensive as judge = $0.01/question

**Recommended Framework:** **AutoGen** (Microsoft Research)
- Built specifically for multi-agent debate
- Supports convergence detection
- Provider-agnostic

---

## Phase 2: Code Health (IN PROGRESS)

### 2.1 Extract Duplicates 🔄

**Priority 1: Build Command Logic**

**Problem:** Lines 1182-1203 and 847-875 duplicate 90% of llama-server.exe command building

**Solution:** Extract pure function
```python
def build_llama_cmd(
    port: int,
    threads: int,
    ctx: int = 8192,
    gpu_layers: int = 0,
    batch: int = 512,
    ubatch: int = 512,
    model_path: Path = None,
    timeout: int = -1,
) -> List[str]:
    """
    Build llama-server.exe command (TESTABLE, PURE).

    Returns:
        List of command arguments
    """
    if model_path is None:
        model_path = MODEL_PATH

    return [
        str(SERVER_EXE),
        "--model", str(model_path),
        "--host", "0.0.0.0",
        "--port", str(port),
        "--ctx-size", str(ctx),
        "--n-gpu-layers", str(gpu_layers),
        "--threads", str(threads),
        "--batch-size", str(batch),
        "--ubatch-size", str(ubatch),
        "--timeout", str(timeout),
        "--parallel", "4",  # NOT --slots (that was the bug!)
        "--cont-batching",
    ]
```

**Benefits:**
- ✅ Eliminates duplicate code
- ✅ Easy to test (no side effects)
- ✅ Single source of truth
- ✅ Prevents bugs like --slots vs --parallel

**Status:** ⏳ TODO

---

**Priority 2: Lazy Import Pattern**

**Problem:** `get_model_manager()` and `get_cached_voice_service()` are 100% identical pattern

**Solution:** Generic helper
```python
_lazy_cache = {}

def lazy_import(module_name: str, error_msg: str = None):
    """Generic lazy import with caching."""
    if module_name not in _lazy_cache:
        try:
            _lazy_cache[module_name] = __import__(module_name)
        except ImportError:
            if error_msg:
                raise ImportError(error_msg)
            raise
    return _lazy_cache[module_name]

# Usage:
model_manager = lazy_import("model_manager")
voice_service = lazy_import("voice_service")
```

**Status:** ⏳ TODO

---

**Priority 3: Delete Useless Function**

**Problem:** `self_heal()` (line 1042) doesn't heal - just prints and exits

**Solution:** Delete it, inline the message where called

**Status:** ⏳ TODO

---

### 2.2 Break Down Monoliths 🔄

**Target: start_server() - Line 1075**

**Current State:** 280 lines, never returns, untestable

**Refactoring Plan:**

```python
def start_server() -> NoReturn:
    """Main orchestrator (stays simple)."""

    # 1. Validate
    validate_binaries()  # ← Extract this (testable)

    # 2. Build command
    cmd = build_llama_cmd(port=8001, threads=4, ...)  # ← Already extracted

    # 3. Start services
    start_background_services()  # ← Extract this

    # 4. Spawn server
    process = spawn_server_process(cmd)  # ← Extract this (testable with mocking)

    # 5. Monitor
    monitor_server_loop(process, cmd)  # ← Extract this (testable)


def monitor_server_loop(process, cmd):
    """Monitor server and handle crashes (TESTABLE)."""
    restart_count = 0
    while True:
        exit_code = process.wait(timeout=5)

        if exit_code is None:
            continue  # Still running

        if exit_code == 0:
            return  # Normal exit

        # Crash detected
        if should_restart(restart_count, exit_code):
            process = restart_server(cmd)
            restart_count += 1
        else:
            raise ServerCrashError(exit_code)
```

**Benefits:**
- Each function < 50 lines
- Each function testable independently
- Clear separation of concerns

**Status:** ⏳ TODO

---

### 2.3 Add Tests (TDD) 🔄

**Test Priority (Easy → Hard):**

```
Priority 1: Pure Functions (No mocking needed)
  ✅ test_env_int()
  ✅ test_build_llama_cmd()
  ✅ test_lazy_import()

Priority 2: Simple State (Mock globals)
  ✅ test_register_process()
  ✅ test_check_processes()
  ✅ test_restart_with_model()

Priority 3: Complex Logic (Mock subprocess)
  ✅ test_spawn_server_process()
  ✅ test_monitor_server_loop()
  ✅ test_should_restart()

Priority 4: Integration Tests
  ✅ test_validate_environment()
  ✅ test_start_server_e2e()
```

**Target Coverage:** 80%+ on core logic

**Status:** ⏳ TODO

---

## Phase 3: Multi-LLM Integration (FUTURE)

### 3.1 Foundation

**Create:** `llm_client.py`
```python
class UnifiedLLMClient:
    """Unified interface for all LLM providers."""

    def __init__(self):
        self.adapters = {
            "local": LocalLlamaAdapter(),  # Your llama-server
            "openai": OpenAIAdapter(),
            "anthropic": AnthropicAdapter(),
            "gemini": GeminiAdapter(),
            "groq": GroqAdapter(),
        }

    async def generate(self, provider, model, prompt, **kwargs):
        return await self.adapters[provider].generate(model, prompt, **kwargs)
```

**Status:** ⏳ TODO

---

### 3.2 Consensus Engine

**Create:** `consensus_engine.py`
```python
class ConsensusEngine:
    """Multi-agent debate system."""

    async def ask_with_consensus(self, question, agents, max_rounds=5):
        # Round 1: Independent
        answers = await self._round_1(question, agents)

        # Rounds 2+: Debate
        for _ in range(max_rounds):
            critiques = await self._critique(answers, agents)
            revised = await self._revise(answers, critiques, agents)

            if self._converged(answers, revised):
                break

            answers = revised

        # Final synthesis
        return await self._synthesize(answers, agents[0])
```

**Status:** ⏳ TODO

---

### 3.3 UI Integration

**Add to Zena UI:**
- Toggle: "Use Multi-LLM Consensus"
- Slider: "Debate Rounds (1-5)"
- Display: Cost per question
- Display: Debate history (collapsible)

**Status:** ⏳ TODO

---

## Timeline

| Phase | Task | Effort | Priority | Status |
|-------|------|--------|----------|--------|
| 1 | safe_print() implementation | 1 hour | 🔴 CRITICAL | ✅ Done |
| 1 | Function analysis | 2 hours | 🔴 CRITICAL | ✅ Done |
| 1 | Multi-LLM research | 3 hours | 🟡 HIGH | ✅ Done |
| 2 | Extract build_llama_cmd() | 1 hour | 🔴 CRITICAL | ⏳ TODO |
| 2 | Extract lazy_import() | 30 min | 🟢 LOW | ⏳ TODO |
| 2 | Delete self_heal() | 15 min | 🟢 LOW | ⏳ TODO |
| 2 | Refactor start_server() | 4 hours | 🔴 CRITICAL | ⏳ TODO |
| 2 | Write unit tests (Priority 1) | 2 hours | 🟡 HIGH | ⏳ TODO |
| 2 | Write unit tests (Priority 2) | 3 hours | 🟡 HIGH | ⏳ TODO |
| 2 | Write integration tests | 4 hours | 🟡 HIGH | ⏳ TODO |
| 3 | Create UnifiedLLMClient | 3 hours | 🟡 HIGH | ⏳ TODO |
| 3 | Create ConsensusEngine | 5 hours | 🟡 HIGH | ⏳ TODO |
| 3 | UI integration | 2 hours | 🟢 LOW | ⏳ TODO |

**Total Estimated Effort:** ~30 hours
**Completed:** 6 hours (20%)
**Remaining:** 24 hours

---

## Success Metrics

### Code Health
- ✅ 0 silent crashes (safe_print ensures all errors visible)
- ⏳ 80%+ test coverage
- ⏳ 0 duplicate code blocks
- ⏳ All functions < 100 lines

### Performance
- ⏳ Startup < 10 seconds
- ⏳ API response < 200ms
- ⏳ Memory usage < 500MB (excluding model)

### Multi-LLM System
- ⏳ Accuracy improvement: +15-20% vs single model
- ⏳ Cost: < $0.01 per question (budget mode)
- ⏳ Latency: < 10 seconds for consensus

---

## Next Actions (You Decide Priority)

**Option A: Continue Code Health** (TDD philosophy)
1. Extract build_llama_cmd()
2. Write tests for env_int(), build_llama_cmd()
3. Refactor start_server() into smaller functions

**Option B: Start Multi-LLM Prototype** (Research validation)
1. Install AutoGen: `pip install pyautogen`
2. Create proof-of-concept with 3 agents
3. Measure accuracy improvement

**Option C: Fix Remaining Crashes** (Stability first)
1. Run python start_llm.py with verbose logging
2. Identify any remaining crash causes
3. Add more error handling

**My Recommendation:** **Option A** - Code health first, then features
- Reason: Can't build on unstable foundation
- TDD prevents future crashes
- Refactoring makes multi-LLM easier to integrate

---

## Questions for You

1. **Priority:** Which phase should we tackle next? (A, B, or C)
2. **Multi-LLM:** Which providers do you want to support? (OpenAI, Anthropic, Gemini, Groq?)
3. **Cost:** What's your budget per question? ($0.001 budget mode vs $0.01 quality mode?)
4. **Testing:** Should we pause features until we have 80% test coverage?

---

**Generated:** 2026-01-23
**Phase 1 Status:** ✅ Complete (safe_print, analysis, research done)
**Next Phase:** Awaiting user decision
