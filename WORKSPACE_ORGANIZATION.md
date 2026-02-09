# WORKSPACE ORGANIZATION GUIDE

## Quick Reference Map

### 🏠 Root Directory (35 essential files)
**Active Development Files - Only touch these!**

```
zena.py                 - Main NiceGUI application (UI)
start_llm.py           - LLM orchestrator launcher
voice_service.py       - Voice/TTS/STT service
config.py              - Configuration module
utils.py               - Utility functions
ui_state.py            - UI state management
start_zenAI.bat        - Windows quick launcher
config.json            - Configuration data
settings.json          - User settings
settings_test.json     - Test settings
knowledge_base.json    - Knowledge base data
HOW_TO_RUN.md         - Quick start guide
QUICK_START.md        - Getting started
```

### 📚 docs/ (69 files)
**All documentation & logs - Reference only**

```
MICROPHONE_HEALING_GUIDE.md
MICROPHONE_HEALER_IMPLEMENTATION_REPORT.md
MICROPHONE_SOLUTION_COMPLETE.md
MICROPHONE_FIX_CHECKLIST.md
ARCHITECTURE.md
AUDIO_INJECTION_GUIDE.md
... + 33 other markdown docs
... + 36 log files (*.txt, *.log)
```

**Use**: `cd docs/` then open .md files in your editor

### 🧪 tests/ (154 files)
**All test scripts & configurations**

```
test_microphone.py
test_voice_manager.py
test_audio_injection.py
... (12 test scripts)
pytest.ini              - Pytest configuration
run_tests.py           - Test runner
verify_*.py            - Verification scripts
test_payload.json      - Test data
test_history.json      - Test history
```

**Use**: 
```bash
cd tests/
python run_tests.py
# OR
python -m pytest
```

### 🛠️ scripts/ (22 files)
**Setup, installation & utility scripts**

```
install.py             - Python package installer
install.bat            - Windows installer
install.sh             - Linux/Mac installer
cleanup_workspace.py   - File organization script
startup_check.py       - Startup verification
debug_*.bat            - Debug launchers
run_all_tests.ps1      - PowerShell test runner
feature_detection.py   - Feature detection
intelligent_router.py  - Request routing
state_management.py    - State management
```

**Use**:
```bash
cd scripts/
python install.py          # Install dependencies
python cleanup_workspace.py # Re-organize files
python startup_check.py     # Verify installation
```

### 📦 OLD/ (35 files)
**Archived & non-essential code - Do not use!**

```
diagnose_*.py           - Diagnostic tools (7 files)
debug_*.py             - Debug utilities (4 files)
stress_test_*.py       - Load testing (2 files)
streamlit_*.py         - Legacy Streamlit UI (4 files)
benchmark*.py          - Performance testing (2 files)
... and 16 other archived files
```

**Use**: Reference only - these are deprecated

---

## 📂 Core Development Directories (Active)

```
zena_mode/              - Main LLM & voice system
├── production_microphone_healer.py    (NEW - Diagnostics)
├── voice_manager_with_healing.py      (NEW - Auto-healing)
└── ... (core modules)

ui/                     - Web interface components
├── debug_audio_page.py              (Audio testing UI)
├── injectable_voice.py              (Audio injection)
└── ... (other UI pages)

local_llm/              - Local LLM implementations
├── piper_tts.py
├── fast_whisper.py
└── ... (LLM modules)

_bin/                   - Binary executables
└── llama-server.exe    (LLM inference server)

models/                 - AI model files
├── base.en (Whisper)
├── en_US-lessac-medium.onnx (Piper)
└── ... (other models)

qdrant_storage/         - Vector database
├── collections/
└── snapshots/

rag_storage/            - RAG documents
├── documents/
└── indexes/

conversation_cache/     - Chat history & cache
└── ... (conversation data)
```

---

## ✅ COMMON TASKS

### Run the Application
```bash
# From root directory
python start_llm.py     # Starts LLM backend + server
# In another terminal
python zena.py          # Or: Navigate to http://localhost:8080
```

### Run Tests
```bash
cd tests/
python run_tests.py     # Run all tests
# OR
python -m pytest test_microphone.py  # Specific test
```

### Install Dependencies
```bash
cd scripts/
python install.py
```

### Check Microphone Status
```bash
python zena_mode/production_microphone_healer.py
```

### Read Documentation
```bash
cd docs/
# Open any .md file in your editor
# Quick reference: MICROPHONE_HEALING_GUIDE.md
```

### Debug Specific Issue
```bash
cd scripts/
python startup_check.py  # Verify installation
```

### Review Old Code
```bash
cd OLD/
# Safely archived - won't affect active code
```

---

## 🔄 File Organization Rules

**In Root?**
- Only active source code
- Configuration files
- Launchers (.bat files)
- Main README

**In docs/?**
- All .md documentation
- All .txt logs
- All .log files
- Output files

**In tests/?**
- test_*.py files
- run_tests.py
- pytest.ini
- verify_*.py files

**In scripts/?**
- install scripts
- setup scripts
- utility scripts
- debug scripts

**In OLD/?**
- Archived scripts
- Deprecated code
- Diagnostic tools
- Legacy implementations

---

## 📊 Directory Tree (Organized Structure)

```
ZEN_AI_RAG/
├── 📁 zena_mode/               (ACTIVE: Core system)
├── 📁 ui/                      (ACTIVE: Web interface)
├── 📁 local_llm/               (ACTIVE: LLM modules)
├── 📁 _bin/                    (ACTIVE: Binaries)
├── 📁 models/                  (ACTIVE: AI models)
├── 📁 qdrant_storage/          (ACTIVE: Vector DB)
├── 📁 rag_storage/             (ACTIVE: RAG data)
├── 📁 conversation_cache/      (ACTIVE: Chat history)
├── 📁 tools/                   (ACTIVE: Tools)
├── 📁 locales/                 (ACTIVE: i18n)
├── 📁 static/                  (ACTIVE: Assets)
│
├── 📁 docs/                    (NEW: Documentation)
├── 📁 tests/                   (NEW: Test scripts)
├── 📁 scripts/                 (NEW: Utilities)
├── 📁 OLD/                     (NEW: Archived)
│
├── 📄 zena.py                  (Main app)
├── 📄 start_llm.py             (Launcher)
├── 📄 voice_service.py         (Voice system)
├── 📄 config.py                (Config)
├── 📄 utils.py                 (Utils)
├── 📄 ui_state.py              (UI state)
├── 📄 start_zenAI.bat          (Windows launcher)
├── 📄 HOW_TO_RUN.md            (Quick start)
│
└── 📁 ... (other system dirs: .git, .venv, etc.)
```

---

## 🎯 Navigation Tips

| Task | Location | Command |
|------|----------|---------|
| **Develop** | Root directory | `python start_llm.py` |
| **Test** | `tests/` | `python run_tests.py` |
| **Install** | `scripts/` | `python install.py` |
| **Read docs** | `docs/` | Open .md files |
| **Check old code** | `OLD/` | Reference only |
| **Microphone help** | `docs/MICROPHONE_*.md` | Read docs |
| **Debug** | `scripts/` | Run debug scripts |

---

## 🚀 Getting Started

1. **First time?**
   ```bash
   cd scripts/
   python install.py
   cd ..
   python start_llm.py
   ```

2. **Run tests?**
   ```bash
   cd tests/
   python run_tests.py
   ```

3. **Need help?**
   ```bash
   cd docs/
   # Read QUICK_START.md or HOW_TO_RUN.md
   ```

4. **Check microphone?**
   ```bash
   python zena_mode/production_microphone_healer.py
   ```

5. **Want old code?**
   ```bash
   cd OLD/
   # Check deprecated implementations
   ```

---

## ✨ Summary

✅ **Root**: ~35 essential files - focused development  
✅ **docs/**: 69 files - all documentation  
✅ **tests/**: 154 files - all testing  
✅ **scripts/**: 22 files - all setup/utilities  
✅ **OLD/**: 35 files - all archived code  

**Result**: Clean, organized, professional workspace! 🏡✨

---

*Last updated: February 5, 2026*  
*Cleanup script: scripts/cleanup_workspace.py*
