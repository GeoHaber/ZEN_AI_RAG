# ZENA AI - Quick Start Guide 🚀

**Updated:** 2026-01-22
**Branch:** naughty-antonelli

---

## First Time Setup (Automatic)

### Option 1: Let start_llm.py Handle Everything (Recommended)

Just run the application - it will detect missing components and offer to install them:

```bash
cd C:\Users\dvdze\.claude-worktrees\ZEN_AI_RAG\naughty-antonelli
python start_llm.py
```

You'll see:

```
============================================================
PRE-FLIGHT VALIDATION
============================================================
[1/4] Checking binary at: ...
[2/4] Checking models in: C:\AI\Models
      [OK] Found 13 model(s):
         - deepseek-coder-6.7b-instruct.Q4_K_M.gguf (3893 MB)
         ...
[3/4] Checking Python dependencies...
      [OK] NiceGUI (UI framework)
      [OK] HTTP client
      [OK] FAISS (vector search)
[4/4] Checking optional features...
      [OK] Voice STT (Whisper)
      ...
============================================================

[X] CRITICAL ISSUES DETECTED:

1. Binary Not Found:
   llama-server.exe not found at: ...

============================================================

[*] AUTOMATIC SETUP AVAILABLE
============================================================

Would you like to run automatic setup?
This will:
  - Detect your CPU/GPU
  - Download optimal llama.cpp binaries

Options:
  Y - Run automatic setup (recommended)
  N - Exit and fix manually
  M - Show manual commands

Your choice [Y/n/m]:
```

**Press Y and Enter** - Setup runs automatically!

---

### Option 2: Manual Setup First

Run the setup manager directly before starting the app:

```bash
python setup_manager.py --auto-install
```

This will:
1. Detect your CPU/GPU
2. Download the best llama.cpp binary for your system
3. Install missing Python packages
4. Update config.json

Then start the app:

```bash
python start_llm.py
```

---

## What Gets Downloaded

The setup manager detects your hardware and downloads the optimal binary:

| Your Hardware | Binary Downloaded | Size |
|--------------|-------------------|------|
| NVIDIA GPU (CUDA 12.x) | `llama-*-cuda-cu12-*.zip` | ~140 MB |
| NVIDIA GPU (CUDA 11.x) | `llama-*-cuda-cu11-*.zip` | ~130 MB |
| CPU with AVX-512 | `llama-*-cpu-avx512-*.zip` | ~120 MB |
| CPU with AVX2 | `llama-*-bin-win-*-x64.zip` | ~120 MB |
| CPU with AVX | `llama-*-bin-win-*-x64.zip` | ~120 MB |
| Basic CPU | `llama-*-bin-win-*-x64.zip` | ~120 MB |

---

## After Setup Completes

You'll see:

```
======================================================================
SETUP COMPLETE! [OK]
======================================================================

You can now run:
  python start_llm.py

To open the UI:
  http://localhost:8080
======================================================================
```

---

## Normal Startup (After Setup)

Once binaries are installed, just run:

```bash
python start_llm.py
```

The app will:
1. Run validation (should pass)
2. Start llama.cpp backend (port 8001)
3. Start Hub API (port 8002)
4. Start Voice WebSocket (port 8003)
5. Launch NiceGUI UI (port 8080)
6. Open browser automatically

You'll see:

```
============================================================
PRE-FLIGHT VALIDATION
============================================================
[1/4] Checking binary at: ...
      [OK] Binary found: llama-server.exe (128 MB)
[2/4] Checking models in: C:\AI\Models
      [OK] Found 13 model(s):
         ...
[3/4] Checking Python dependencies...
      [OK] NiceGUI (UI framework)
      [OK] HTTP client
      [OK] FAISS (vector search)
[4/4] Checking optional features...
      [OK] Voice STT (Whisper)
      [OK] Voice TTS
      [OK] PDF support
============================================================

[OK] ALL CHECKS PASSED - Environment ready!

============================================================

[*] Launching optimized llama.cpp...
    Layers: 0 | Threads: 8 | Ubatch: 512 | Port: 8001
[*] Engine Active (PID: 12345)
[*] ZenAI Hub API listening on Port 8002
[*] Launching Zena AI (NiceGUI)...
```

Browser opens to: **http://localhost:8080**

---

## Using the Application

### Basic Chat
1. Type your message in the input box
2. Press **Enter** or click **📤 Send**
3. See AI response stream in real-time

### File Upload
1. Click **📎 Attach** button
2. Select a file (.txt, .py, .md, .pdf, etc.)
3. Send your message - file context included

### Voice Input
1. Click **🎤 Mic** button
2. Speak for 5 seconds
3. Transcribed text appears in input

### RAG (Scan & Learn)
1. Open menu (☰ button)
2. Click "Scan & Learn"
3. Choose **Website** or **Local Directory**
4. Enter URL or path
5. Click "Start Scan"
6. Ask questions about the content!

### Swarm Mode (Multi-Expert)
1. Open menu (☰ button)
2. Find "CoT Swarm" toggle
3. Enable swarm mode
4. Get consensus-based answers

---

## Ports Used

| Port | Service | Purpose |
|------|---------|---------|
| 8001 | LLM Backend | Main model inference |
| 8002 | Hub API | Model management, downloads |
| 8003 | Voice WebSocket | Audio processing |
| 8080 | NiceGUI UI | Web interface |
| 8005-8012 | Swarm Experts | Multi-expert mode (optional) |

---

## Troubleshooting

### "Binary download failed"
- Check internet connection
- Try manual download from: https://github.com/ggerganov/llama.cpp/releases/latest
- Extract to `_bin/` directory

### "Port already in use"
```bash
# Find what's using port 8080
netstat -ano | findstr :8080

# Kill the process (replace PID)
taskkill /PID <PID> /F
```

### "Backend offline" message
- Binary not running
- Check if `_bin/llama-server.exe` exists
- Run: `python setup_manager.py --binaries-only`

### "Model not found"
- No models in `C:\AI\Models`
- App starts in MANAGER MODE
- Use UI to download a model
- Or place .gguf files in `C:\AI\Models`

---

## Command Line Options

### Skip Validation
```bash
python start_llm.py --skip-validation
```

### Hub Only (No LLM Engine)
```bash
python start_llm.py --hub-only
```

### Custom Model
```bash
python start_llm.py --model your-model.gguf
```

### Swarm Mode
```bash
python start_llm.py --swarm 3
```

### Setup Manager Options
```bash
# Hardware detection only
python setup_manager.py --detect-only

# Download binaries only
python setup_manager.py --binaries-only

# Install dependencies only
python setup_manager.py --deps-only --auto-install

# Full setup
python setup_manager.py --auto-install

# Force reinstall binaries
python setup_manager.py --force --auto-install
```

---

## What's New

### Recent Improvements
- ✅ **Automatic setup** - One command to install everything
- ✅ **Hardware detection** - Downloads optimal binary for your system
- ✅ **Smart validation** - Checks all requirements before startup
- ✅ **Fun loading messages** - Context-aware, rotating (EN/ES)
- ✅ **Lazy FAISS loading** - 87% memory reduction
- ✅ **Feature detection** - Clear error messages
- ✅ **Conversation memory** - LLM-powered summarization
- ✅ **Session isolation** - Per-client arbitrator

---

## Summary

**To run ZENA AI for the first time:**

```bash
# Navigate to project
cd C:\Users\dvdze\.claude-worktrees\ZEN_AI_RAG\naughty-antonelli

# Start the app (automatic setup offered if needed)
python start_llm.py

# Or run setup first
python setup_manager.py --auto-install
python start_llm.py
```

**Then visit:** http://localhost:8080

**Enjoy your AI assistant with:**
- 🤖 Local LLM inference
- 🧠 Smart RAG from websites/docs
- 🐝 Multi-expert swarm mode
- 🌍 Multilingual support (6 languages)
- 🎨 Fun loading animations
- 🔒 100% local & private

Happy chatting! 🚀

---

*For technical details, see:*
- `HOW_TO_RUN.md` - Detailed instructions
- `SETUP_MANAGER.md` - Setup system documentation
- `STARTUP_VALIDATION.md` - Validation details
- `TEST_SUMMARY.md` - Test coverage (101 passing!)
