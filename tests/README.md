
# ZenAI Test Suite

This directory contains the comprehensive test suite for ZenAI RAG. Tests are categorized by their function and scope.

## 🎯 Quick Start (Most Important Tests)

If you made UI changes or want to ensure the app is stable, run these first:

### 1. UI Chaos Monkey (Fuzzer)
**File:** `tests/run_ui_fuzzer.py`
**Description:** Randomly interacts with the UI (clicks buttons, types text) to find crashes or unhandled exceptions. requires `python start_llm.py` to be running.
**How to Run:**
```powershell
python tests/run_ui_fuzzer.py
```

### 2. End-to-End Chat UI Test
**File:** `tests/test_chat_ui.py`
**Description:** Verifies the full chat loop: launches browser, types a message, clicks send, and verifies the response appears. Also checks backend API connectivity.
**How to Run:**
```powershell
python tests/test_chat_ui.py
```

---

## 🏗️ Core Application Tests

### Startup & Integration
- **`test_start_llm.py`**: Verifies the main application launch logic, backend service startup, and port binding.
- **`smoke_test_startup.py`**: A quick check to see if essential services can initialize without error.

### RAG & Pipeline
- **`test_rag_pipeline.py`**: Core logic test for the Retrieval Augmented Generation system.
- **`test_rag_precision.py`**: Measures the accuracy of retrieval results against known queries.
- **`benchmark_pipeline.py`**: specific performance test for measuring RAG latency.

### Scrapers
- **`test_scraper_resilience.py`**: Tests the robustness of web scrapers against various page structures.
- **`diagnose_scraper.py`**: Utility to debug specific scraping issues.

---

## 🛠️ Unit Tests

Run these to verify specific components in isolation:
```powershell
# Run all unit tests
pytest tests/
```

- **`test_ui_components.py`**: Unit tests for specific UI elements (GlassCapsule, LivingLogo).
- **`test_conversation_memory.py`**: Verifies context management and history.
- **`test_config_swarm.py`**: Tests configuration loading and swarm parameters.

---

## 📊 Benchmarks & Stress Tests

- **`benchmark_rag_speed.py`**: Measures token processing and retrieval speeds.
- **`stress_test_random_swarm.py`**: Simulates high load on the Swarm architecture.
- **`nightly_soak_test.py`**: Long-running test to detect memory leaks or stability degradation over time.

## 🎤 Voice Lab
- **`experimental_voice_lab/test_voice_stack.py`**: (Located in parent dir) Tests emotional voice synthesis integration.
