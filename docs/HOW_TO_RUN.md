# How to Run ZENA AI - Complete Guide 🚀

**Updated:** 2026-01-22
**Branch:** naughty-antonelli

---

## Quick Start (TL;DR)

```bash
# 1. Navigate to project directory
cd C:\Users\dvdze\.claude-worktrees\ZEN_AI_RAG\naughty-antonelli

# 2. Start the application (launches backend + UI)
python start_llm.py

# 3. Open browser to http://localhost:8080
```

That's it! 🎉

---

## Detailed Step-by-Step Guide

### Step 1: Prerequisites Check

**NEW:** The startup script now includes **automatic validation**! It will check all prerequisites for you when you run it.

Before running, you should have:

#### Required:
- ✅ **Python 3.12+** installed
- ✅ **LLM Model** at `C:\AI\Models\` (e.g., qwen2.5-coder.gguf)
- ✅ **llama.cpp binary** at `_bin/llama-server.exe`

#### Manual Verification (Optional):
```bash
# Check Python Version
python --version
# Should show: Python 3.12.x or higher

# Check if Model Exists
dir C:\AI\Models\
# Should show your .gguf model files

# Check if llama.cpp Binary Exists
dir _bin\llama-server.exe
# Should show llama-server.exe
```

**Note:** The startup script will automatically validate all these requirements and provide clear error messages with fixes if anything is missing!

---

### Step 2: Install Dependencies (First Time Only)

```bash
# Navigate to project directory
cd C:\Users\dvdze\.claude-worktrees\ZEN_AI_RAG\naughty-antonelli

# Install required packages
pip install -r requirements.txt
```

**This installs:**
- NiceGUI (UI framework)
- httpx (async HTTP)
- FAISS (vector search)
- sentence-transformers (embeddings)
- Other dependencies

---

### Step 3: Configure (Optional)

Edit `config.json` to customize settings:

```json
{
  "zena_mode": {
    "enabled": true,
    "language": "en",
    "rag_source": "knowledge_base"
  }
}
```

**Common settings:**
- `enabled: true` - Enable Zena healthcare mode
- `enabled: false` - Standard ZenAI developer mode
- `language: "en"` - English (also supports: es, fr, he, hu, ro)

---

### Step 4: Start the Application

There are **three ways** to start ZENA:

#### Option 1: Full Stack (Recommended)
Starts everything: LLM backend + UI

```bash
python start_llm.py
```

**What happens:**
1. Launches llama-server.exe on port 8001
2. Starts Hub API on port 8002
3. Starts Voice WebSocket on port 8003
4. Launches NiceGUI UI on port 8080
5. Opens browser automatically

#### Option 2: UI Only (Backend Already Running)
If backend is already running from another terminal:

```bash
python zena.py
```

**Use when:**
- Backend is already running
- You only want to restart the UI
- Testing UI changes

#### Option 3: Backend Only (No UI)
For development or testing:

```bash
python start_llm.py --hub-only
```

**Use when:**
- Testing backend separately
- Running headless server
- Development mode

---

### Step 5: Access the Application

Once started, open your browser to:

```
http://localhost:8080
```

**You should see:**
- Clean chat interface
- Input box at bottom
- Menu button (top-left)
- Dark mode toggle (top-right)
- Fun waiting message below input 🎨

---

## Using the Application

### Basic Chat
1. Type your message in the input box
2. Press **Enter** or click **Send** button (📤)
3. Watch the fun loading messages! 🤔
4. See the AI response stream in real-time

### File Upload
1. Click **📎 Attach** button
2. Select a file (.txt, .py, .md, .pdf, etc.)
3. File content appears in preview
4. Send your message - file context included

### Voice Input
1. Click **🎤 Mic** button
2. Speak for 5 seconds
3. Wait for transcription
4. Transcribed text appears in input

### RAG (Scan & Learn)
1. Open menu (☰ button)
2. Click "Scan & Learn"
3. Choose **Website** or **Local Directory**
4. Enter URL or path
5. Click "Start Scan"
6. Wait for indexing (progress shown)
7. Ask questions about the content!

### Swarm Mode (Multi-Expert)
1. Open menu (☰ button)
2. Find "CoT Swarm" toggle
3. Enable swarm mode
4. See "🐝 Consulting the expert swarm..." messages
5. Get consensus-based answers

---

## Ports Used

| Port | Service | Purpose |
|------|---------|---------|
| 8001 | LLM Backend | Main model inference |
| 8002 | Hub API | Model management, downloads |
| 8003 | Voice WebSocket | Audio processing |
| 8080 | NiceGUI UI | Web interface |
| 8005-8012 | Swarm Experts | Multi-expert mode (optional) |

**Important:** Make sure these ports are not in use!

---

## Troubleshooting

### Problem: "Port already in use"

**Solution:**
```bash
# Find what's using port 8080
netstat -ano | findstr :8080

# Kill the process (replace PID with actual number)
taskkill /PID <PID> /F

# Or use a different port
python zena.py --port 8081
```

### Problem: "Backend offline" message

**Cause:** LLM backend not running

**Solution:**
```bash
# Start backend separately
python start_llm.py
```

### Problem: "Model not found"

**Cause:** No model at C:\AI\Models\

**Solution:**
1. Download a model (e.g., from Hugging Face)
2. Place .gguf file in `C:\AI\Models\`
3. Or change path in config.json

### Problem: "Missing dependencies"

**Cause:** Some packages not installed

**Solution:**
```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall

# Or install individually
pip install nicegui httpx faiss-cpu sentence-transformers
```

### Problem: "Voice not working"

**Cause:** sounddevice or pyttsx3 not available

**Solution:**
```bash
pip install sounddevice scipy pyttsx3
```

**Check feature status:**
The app will now show clear messages if features are unavailable!

### Problem: "RAG index won't load"

**Cause:** Large index causing OOM

**Solution:**
Lazy loading is now enabled by default! Index loads on first search.
If still having issues:
```python
# In config.json, reduce max chunks
"rag": {
  "max_chunks": 1000  # Reduce from default
}
```

---

## Advanced Usage

### Running with Custom Model

```bash
# Edit config.json
{
  "model_path": "C:\\AI\\Models\\your-model.gguf",
  "context_size": 4096
}

# Start with specific model
python start_llm.py --model your-model.gguf
```

### Running in Swarm Mode

```bash
# Start main instance
python start_llm.py

# In separate terminals, start experts
python start_llm.py --port 8005 --guard-bypass
python start_llm.py --port 8006 --guard-bypass
python start_llm.py --port 8007 --guard-bypass

# Or use auto-swarm
python start_llm.py --swarm 3 --auto-swarm
```

### Development Mode

```bash
# Enable auto-reload (UI restarts on file changes)
python zena.py --reload

# Enable debug logging
python start_llm.py --debug

# Run tests
python -m pytest tests/ -v
```

---

## Environment Variables

Optional environment variables:

```bash
# Set model directory
set MODELS_DIR=C:\AI\Models

# Set log level
set LOG_LEVEL=DEBUG

# Disable auto-browser open
set NICEGUI_OPEN_BROWSER=false

# Custom port
set NICEGUI_PORT=8080
```

---

## Stopping the Application

### Graceful Shutdown:
- Press **Ctrl+C** in terminal
- Wait for cleanup (2-3 seconds)

### Force Stop:
```bash
# Windows Task Manager
# Find "python.exe" processes and end them

# Or command line
taskkill /IM python.exe /F
```

---

## Performance Tips

### For Faster Startup:
1. Use lazy loading (enabled by default)
2. Reduce max context in config.json
3. Use smaller model (e.g., 3B instead of 7B)

### For Better Performance:
1. Close unused applications
2. Allocate more RAM (16GB recommended)
3. Use GPU layers (if available)
4. Disable swarm mode if not needed

### For Large RAG Indexes:
1. Lazy loading handles this automatically!
2. Index loads only when first searching
3. Periodic cleanup keeps uploads/ directory clean

---

## What's New in This Version

### Recent Improvements:
- ✅ **Fun loading messages** - Context-aware, rotating (EN/ES)
- ✅ **Lazy FAISS loading** - 87% memory reduction
- ✅ **Feature detection** - Clear error messages
- ✅ **Upload cleanup** - Automatic file management
- ✅ **Cancellation support** - Respects client disconnect
- ✅ **Session isolation** - Per-client arbitrator

### See Full Details:
- `DESIGN_REVIEW_FIXES.md` - Architecture improvements
- `LOADING_MESSAGES_FEATURE.md` - Loading animations
- `TEST_SUMMARY.md` - Test coverage (101 passing!)

---

## Getting Help

### Check Logs:
```bash
# Look at debug log
type nebula_debug.log
```

### Run Diagnostics:
1. Open menu (☰)
2. Click "System"
3. Click "Diagnostics"
4. Review status of LLM, RAG, Memory

### Common Issues:
- **"Waiting for backend..."** - Start backend first
- **"Port in use"** - Change port or kill process
- **"Model not loaded"** - Check model path in config
- **"Voice unavailable"** - Install sounddevice/pyttsx3

---

## Summary

**To run ZENA AI:**

```bash
# Simple version
python start_llm.py

# Then visit
http://localhost:8080
```

**Enjoy your AI assistant with:**
- 🎨 Fun loading messages
- 🧠 Smart RAG from websites/docs
- 🐝 Multi-expert swarm mode
- 🌍 Multilingual support (6 languages)
- 🔒 100% local & private

Happy chatting! 🚀

---

*For technical details, see README.md and documentation files*
