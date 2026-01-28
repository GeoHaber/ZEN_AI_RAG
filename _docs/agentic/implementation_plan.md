# Implementation Plan: Decoupled Stabilization

This plan outlines a phased approach to stabilize ZenAI by isolating the UI from the Backend, ensuring each component works independently before final integration.

## Proposed Changes

### Phase 1: UI Stability (Mocked) - ✅ COMPLETE

The UI is now stable with mock data and includes robust zombie protection.
- [x] Create `MockAsyncBackend` in `mock_backend.py`.
- [x] Update `zena.py` to support `--mock` mode.
- [x] Resolve all `AttributeError` issues and dependencies.
- [x] Implement 'Zombie Protection' at UI startup.

### Phase 2: Backend Reliability (Headless) - ✅ COMPLETE

Stabilized the "Heart" (LLM Server) and "Brain" (RAG) using automated scripts.
- [x] Align JSON payload with OpenAI specifications.
- [x] Fix Log File Generation.
- [x] Implement `tests/test_backend_full.py`.
- [x] Standardize Central Model Store location.

### Phase 3: Integration - ✅ COMPLETE

Stitched the components together and verified end-to-end.
- [x] Reconnect the real `AsyncZenAIBackend`.
- [x] Add robust error handling.
- [x] Execute `tests/final_smoke_test.py`.

## Verification Plan

### Automated Tests
- **UI Mock Test**: `python zena.py --mock` followed by `tests/monkey_test.py` (simulated clicks).
- **Backend Headless Test**: `python tests/test_backend_full.py`.
- **System Diagnostics**: `python tests/live_diagnostics.py` after integration.

### Manual Verification
- Verify the settings dialog opens without "AttributeError".
- Confirm the drawer shows the correct model list from the real backend.
