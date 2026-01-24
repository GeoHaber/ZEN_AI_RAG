# Function Analysis - start_llm.py

## Executive Summary
**Total Functions: 19**
- **Tested:** 0 ❌
- **Pure Functions:** 4 ✅
- **Side Effects:** 15 ⚠️
- **Duplicates/Similar:** 5 groups identified 🔄

---

## Category 1: VALIDATION & SAFETY (3 functions)

### 1. `validate_environment()` - Line 35
**Purpose:** Pre-flight checks for binaries, models, dependencies
**Category:** Validation
**Side Effects:** File I/O, user input, sys.exit()
**Testable:** ⚠️ Partial (can mock file system)
**Tested:** ❌ No
**Similar To:** None
**Issues:**
- Long function (160+ lines) - should be broken down
- Handles too many responsibilities (validation + user interaction + setup invocation)

**Recommendation:** Split into:
- `check_binaries()` - pure validation
- `check_models()` - pure validation
- `check_dependencies()` - pure validation
- `handle_validation_failures()` - user interaction

---

### 2. `instance_guard()` - Line 199
**Purpose:** Prevent multiple instances of start_llm.py
**Category:** Validation
**Side Effects:** Process enumeration, sys.exit()
**Testable:** ⚠️ Hard (requires process mocking)
**Tested:** ❌ No
**Similar To:** None
**Issues:**
- Debug prints should use a flag
- Complex path resolution logic

**Recommendation:** Add unit tests with psutil mocking

---

### 3. `emergency_handler(signum, frame)` - Line 1351
**Purpose:** Fatal signal handler (SIGTERM, SIGABRT)
**Category:** Error Handling
**Side Effects:** sys.exit()
**Testable:** ⚠️ Hard (signals)
**Tested:** ❌ No
**Similar To:** None
**Issues:** None

---

## Category 2: UTILITIES (4 functions)

### 4. `safe_print(*args, **kwargs)` - Line 267
**Purpose:** Thread-safe print with flush
**Category:** Utility
**Side Effects:** stdout write
**Testable:** ✅ Yes (can capture stdout)
**Tested:** ❌ No
**Similar To:** None
**Issues:** None

**Recommendation:** Add unit test to verify flush=True

---

### 5. `safe_exit(code, delay)` - Line 281
**Purpose:** Graceful exit with buffer flush
**Category:** Utility
**Side Effects:** sys.exit(), sleep
**Testable:** ⚠️ Partial (can't test sys.exit easily)
**Tested:** ❌ No
**Similar To:** None
**Issues:** None

---

### 6. `env_int(name, default)` - Line 1035
**Purpose:** Read integer from environment variable
**Category:** Utility
**Side Effects:** None (pure function)
**Testable:** ✅ Yes
**Tested:** ❌ No
**Similar To:** None
**Issues:** None

**Recommendation:** Add unit tests (easy win)

---

### 7. `self_heal()` - Line 1042
**Purpose:** Error message + exit (NOT actual healing)
**Category:** Error Handling
**Side Effects:** sys.exit()
**Testable:** ❌ No (just exits)
**Tested:** ❌ No
**Similar To:** None
**Issues:** **MISLEADING NAME** - doesn't heal, just exits

**Recommendation:** Rename to `exit_with_repair_message()` or delete (barely used)

---

## Category 3: PROCESS MANAGEMENT (5 functions)

### 8. `register_process(name, process, critical)` - Line 312
**Purpose:** Register subprocess for monitoring
**Category:** Process Management
**Side Effects:** Global state mutation (MONITORED_PROCESSES)
**Testable:** ✅ Yes (can mock globals)
**Tested:** ❌ No
**Similar To:** None
**Issues:** None

**Recommendation:** Add unit tests

---

### 9. `check_processes()` - Line 323
**Purpose:** Poll all monitored processes for crashes
**Category:** Process Management
**Side Effects:** Global state read (MONITORED_PROCESSES)
**Testable:** ✅ Yes
**Tested:** ❌ No
**Similar To:** None
**Issues:** None

**Recommendation:** Add unit tests

---

### 10. `launch_expert_process(port, threads, model_path)` - Line 845
**Purpose:** Spawn llama-server.exe for swarm mode
**Category:** Process Management
**Side Effects:** subprocess.Popen()
**Testable:** ⚠️ Hard (requires binary)
**Tested:** ❌ No
**Similar To:** `start_server()` - **DUPLICATE LOGIC** 🔄
**Issues:**
- Duplicates 90% of start_server() command building
- Hard-coded flags

**Recommendation:** Extract shared logic into `build_llama_cmd(port, threads, ctx, ...)`

---

### 11. `kill_process_tree(pid)` - Line 937
**Purpose:** Kill process and all children
**Category:** Process Management
**Side Effects:** Process termination
**Testable:** ⚠️ Hard (requires real processes)
**Tested:** ❌ No
**Similar To:** None
**Issues:** None

---

### 12. `scale_swarm(target_count)` - Line 880
**Purpose:** Dynamically add/remove expert processes
**Category:** Process Management
**Side Effects:** Global state (EXPERT_PROCESSES), process spawn/kill
**Testable:** ⚠️ Hard
**Tested:** ❌ No
**Similar To:** None
**Issues:**
- Debug prints everywhere
- Uses global EXPERT_PROCESSES

**Recommendation:** Refactor to class-based (SwarmManager) for testability

---

## Category 4: SERVICE MANAGEMENT (3 functions)

### 13. `start_hub()` - Line 1047
**Purpose:** Start Nebula Hub API (HTTP server on 8002)
**Category:** Service Management
**Side Effects:** Thread spawn, network bind
**Testable:** ⚠️ Partial (can test without actual binding)
**Tested:** ❌ No
**Similar To:** `start_voice_stream_server()` - **SIMILAR PATTERN** 🔄
**Issues:**
- Uses bare except (bad practice)
- No return value (can't tell if succeeded)

**Recommendation:** Return success/failure, raise specific exceptions

---

### 14. `start_voice_stream_server()` - Line 1010
**Purpose:** Start WebSocket voice server on 8003
**Category:** Service Management
**Side Effects:** Thread spawn, network bind, kill existing process
**Testable:** ⚠️ Partial
**Tested:** ❌ No
**Similar To:** `start_hub()` - **SIMILAR PATTERN** 🔄
**Issues:**
- Calls `kill_process_by_port(8003)` (where is this function defined?)
- No error handling

**Recommendation:** Consolidate with start_hub into `start_service(name, port, handler)`

---

### 15. `run_ws_server()` - Line 999 (async)
**Purpose:** Async WebSocket server loop
**Category:** Service Management
**Side Effects:** Network I/O
**Testable:** ⚠️ Hard (async + network)
**Tested:** ❌ No
**Similar To:** None
**Issues:** Very short - just calls handler.handle_client

---

## Category 5: LAZY LOADERS (2 functions)

### 16. `get_model_manager()` - Line 354
**Purpose:** Lazy-load model_manager module (avoid import cost)
**Category:** Lazy Loading
**Side Effects:** Module import, global cache mutation
**Testable:** ✅ Yes (can mock import)
**Tested:** ❌ No
**Similar To:** `get_cached_voice_service()` - **DUPLICATE PATTERN** 🔄
**Issues:** None

**Recommendation:** Create generic `lazy_import(module_name, cache_var)` helper

---

### 17. `get_cached_voice_service()` - Line 370
**Purpose:** Lazy-load voice_service module
**Category:** Lazy Loading
**Side Effects:** Module import, global cache mutation
**Testable:** ✅ Yes
**Tested:** ❌ No
**Similar To:** `get_model_manager()` - **DUPLICATE PATTERN** 🔄
**Issues:** None

**Recommendation:** Merge with get_model_manager() into generic helper

---

## Category 6: MAIN ORCHESTRATORS (2 functions)

### 18. `start_server()` - Line 1075 (NO RETURN)
**Purpose:** Main server launch orchestration
**Category:** Main Loop
**Side Effects:** **EVERYTHING** (file I/O, process spawn, network, loops forever)
**Testable:** ❌ No (too complex, no return)
**Tested:** ❌ No
**Similar To:** None (but contains duplicate logic from launch_expert_process)
**Issues:**
- **MASSIVE FUNCTION** (280+ lines)
- Mixes concerns: validation, command building, process spawn, monitoring loop
- Never returns (NoReturn type)
- Hard to test ANY part of it

**Recommendation:** **CRITICAL REFACTOR NEEDED**
1. Extract `build_llama_cmd()` - pure function, easily testable
2. Extract `monitor_server_loop()` - can mock process
3. Extract `handle_server_crash()` - can test restart logic
4. Make start_server() a simple orchestrator

---

### 19. `restart_with_model(name)` - Line 835
**Purpose:** Hot-swap model (update global MODEL_PATH)
**Category:** Configuration
**Side Effects:** Global state mutation (MODEL_PATH)
**Testable:** ✅ Yes (can test global mutation)
**Tested:** ❌ No
**Similar To:** None
**Issues:**
- Returns dict with "model" key (inconsistent API)
- Doesn't actually restart - just changes global

**Recommendation:** Rename to `set_model_path()` for clarity

---

## DUPLICATE/SIMILAR FUNCTION GROUPS

### 🔄 Group 1: Command Building (HIGH PRIORITY)
- `start_server()` lines 1182-1203 - builds llama-server.exe command
- `launch_expert_process()` lines 847-875 - builds llama-server.exe command

**Duplicated Logic:** ~90% overlap
**Fix:** Extract `build_llama_cmd(port, threads, ctx, gpu_layers, batch, ubatch, model_path) -> List[str]`

---

### 🔄 Group 2: Service Starters
- `start_hub()` - starts HTTP server on 8002
- `start_voice_stream_server()` - starts WebSocket on 8003

**Similar Pattern:** Both start background services
**Fix:** Create `start_background_service(name, port, handler_class, protocol='http')`

---

### 🔄 Group 3: Lazy Loaders
- `get_model_manager()` - lazy import with cache
- `get_cached_voice_service()` - lazy import with cache

**Duplicate Pattern:** 100% same pattern
**Fix:** Create `lazy_import(module_name: str, cache_dict: dict, cache_key: str)`

---

### 🔄 Group 4: Print Wrappers (MINOR)
- `safe_print()` - wrapper around print
- `logger.info()`, `logger.error()` - similar but different backend

**Observation:** Code inconsistently uses safe_print vs logger
**Fix:** Create unified `log(level, message, also_print=True)` function

---

### 🔄 Group 5: Exit Functions
- `safe_exit(code)` - exit with flush
- `self_heal()` - just calls safe_exit(1) with message

**Duplicate:** self_heal() is unnecessary
**Fix:** Delete self_heal(), inline the message where it's called

---

## TESTABILITY MATRIX

| Function | Pure? | Testable? | Priority |
|----------|-------|-----------|----------|
| `env_int()` | ✅ | ✅ | 🟢 HIGH (easy win) |
| `safe_print()` | ❌ | ✅ | 🟢 HIGH (easy) |
| `restart_with_model()` | ❌ | ✅ | 🟢 HIGH (easy) |
| `register_process()` | ❌ | ✅ | 🟡 MEDIUM |
| `check_processes()` | ❌ | ✅ | 🟡 MEDIUM |
| `get_model_manager()` | ❌ | ✅ | 🟡 MEDIUM |
| `get_cached_voice_service()` | ❌ | ✅ | 🟡 MEDIUM |
| `safe_exit()` | ❌ | ⚠️ | 🟡 MEDIUM (hard to test exit) |
| `validate_environment()` | ❌ | ⚠️ | 🔴 LOW (complex) |
| `instance_guard()` | ❌ | ⚠️ | 🔴 LOW (requires mocking) |
| `kill_process_tree()` | ❌ | ⚠️ | 🔴 LOW (requires processes) |
| `start_hub()` | ❌ | ⚠️ | 🔴 LOW (network) |
| `start_voice_stream_server()` | ❌ | ⚠️ | 🔴 LOW (network) |
| `launch_expert_process()` | ❌ | ⚠️ | 🔴 LOW (requires binary) |
| `scale_swarm()` | ❌ | ⚠️ | 🔴 LOW (complex) |
| `start_server()` | ❌ | ❌ | ⛔ UNTESTABLE (refactor first) |
| `run_ws_server()` | ❌ | ⚠️ | 🔴 LOW (async + network) |
| `emergency_handler()` | ❌ | ⚠️ | 🔴 LOW (signals) |
| `self_heal()` | ❌ | ❌ | ⛔ DELETE (useless) |

---

## RECOMMENDED REFACTORING PRIORITY

### Phase 1: Quick Wins (Extract Duplicates)
1. ✅ **Extract `build_llama_cmd()`** from start_server() and launch_expert_process()
2. ✅ **Extract `lazy_import()`** to replace get_model_manager() and get_cached_voice_service()
3. ✅ **Delete `self_heal()`** - inline the message
4. ✅ **Rename `restart_with_model()` → `set_model_path()`** for clarity

### Phase 2: Break Down Monoliths
5. ✅ **Split `validate_environment()`** into:
   - `check_binaries()` → testable
   - `check_models()` → testable
   - `check_dependencies()` → testable
   - `handle_validation_ui()` → keeps user interaction separate

6. ✅ **Refactor `start_server()`** into:
   - `build_llama_cmd()` → pure, testable ✅
   - `spawn_server_process()` → testable with mocking
   - `monitor_server_loop()` → testable
   - `handle_server_restart()` → testable

### Phase 3: Add Tests (TDD)
7. ✅ Write tests for all pure functions first (env_int, build_llama_cmd)
8. ✅ Write tests for simple stateful functions (register_process, check_processes)
9. ✅ Write integration tests for complex flows (validate_environment, start_server)

### Phase 4: Class-Based Refactor (Optional)
10. ✅ Convert to OOP:
    - `ProcessMonitor` class (handles MONITORED_PROCESSES)
    - `SwarmManager` class (handles EXPERT_PROCESSES)
    - `ServerOrchestrator` class (handles start_server logic)

This would make dependency injection possible → much easier testing!

---

## CRITICAL FINDINGS

### 🚨 Issue 1: `start_server()` is Untestable
**Line 1075** - 280+ line function that never returns
**Impact:** Can't test ANY of the core server logic
**Fix:** Extract smaller functions (see Phase 2 above)

### 🚨 Issue 2: Duplicate Command Building
**Lines 1182-1203 & 847-875** - Same command logic repeated
**Impact:** Bug fixes must be applied twice
**Fix:** Extract build_llama_cmd()

### 🚨 Issue 3: Inconsistent Logging
**Throughout file** - Mix of safe_print(), logger.info(), logger.error()
**Impact:** Hard to filter logs, inconsistent formatting
**Fix:** Unified logging strategy

### 🚨 Issue 4: Global State Everywhere
**MONITORED_PROCESSES, EXPERT_PROCESSES, MODEL_PATH, SERVER_PROCESS**
**Impact:** Race conditions, hard to test, unclear ownership
**Fix:** Move to class-based design with dependency injection

### 🚨 Issue 5: Silent Failures
**start_hub(), start_voice_stream_server()** - No return values
**Impact:** Can't tell if services started successfully
**Fix:** Return True/False or raise exceptions

---

## CONCLUSION

**Current State:** ⚠️ Code works but is **unmaintainable and untestable**

**Root Causes:**
1. No TDD - code written without tests from the start
2. Monolithic functions - start_server() does too much
3. Duplicate logic - command building repeated
4. Global state - makes testing impossible

**Next Steps:**
1. ✅ Extract duplicate logic (Phase 1)
2. ✅ Break down monoliths (Phase 2)
3. ✅ Write comprehensive test suite (Phase 3)
4. ✅ Consider OOP refactor for long-term maintainability (Phase 4)

**Estimated Effort:**
- Phase 1: 2-3 hours (high ROI)
- Phase 2: 4-6 hours (critical for testability)
- Phase 3: 6-8 hours (proper TDD coverage)
- Phase 4: 8-10 hours (optional, long-term investment)

---

**Generated:** 2026-01-23
**Analyzed File:** start_llm.py (1556 lines)
**Functions Analyzed:** 19
**Critical Issues:** 5
**Duplicate Groups:** 5
