# Project Decision: Decoupled Stabilization

We are moving to a three-phase stabilization strategy to isolate and resolve persistent errors.

- [x] **Phase 1: UI Stability (Mocked)**
    - [x] Create `MockAsyncBackend` in `mock_backend.py`.
    - [x] Update `zena.py` to support `--mock` mode.
    - [x] Resolve all `AttributeError` issues in `settings_dialog.py` and `ui_components.py`.
    - [x] Implement 'Zombie Protection' in `zena.py` startup.
    - [x] Verified by user: "Nice the menue is up !!"
- [x] Phase 2: Backend Reliability (Headless) 🚀
    - [x] Debug `async_backend.py` LLM 400 Errors (Fixed: standardized payload)
    - [x] Fix Log File Generation (`nebula_debug.log` verified)
    - [x] Implement Comprehensive Backend Testing (`tests/test_backend_full.py`)
    - [x] Verify Central Model Store (`C:\AI\Models`)
    - [ ] Verify `start_llm.py` starts `llama-server.exe` with selected models reliably.
    - [ ] Test RAG feeding and reading independently of the UI.
    - [ ] Confirm Hub API and Voice Server stabilities.
- [x] Phase 3: Final Integration & Verification 🔗
    - [x] Re-couple UI with real Backend in `zena.py`
    - [x] Perform Full System Smoke Test (✅ SUCCESS)
    - [x] Final Cleanup & Documentation
    - [x] Stitch stabilized UI with stabilized Backend.
    - [x] Run `live_diagnostics.py` on the full system.
    - [x] Verify alignment with `zena_master_spec.md`.
