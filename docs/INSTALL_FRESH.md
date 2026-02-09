# ZEN_AI_RAG - Complete Installation Guide

## Quick Start (Fresh System)

### Windows
```batch
install.bat
```

### Linux / macOS
```bash
bash install.sh
```

That's it! The script will:
1. ✓ Check Python installation
2. ✓ Create virtual environment
3. ✓ Upgrade pip, setuptools, wheel
4. ✓ Install all dependencies
5. ✓ Ready to use!

---

## Manual Installation (if scripts don't work)

### Step 1: Check Python
```bash
python --version  # Should be 3.12+
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate.bat

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Upgrade pip
```bash
python -m pip install --upgrade pip setuptools wheel
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Verify Installation
```bash
python verify_install.py
```

---

## Verify Installation

After setup, run the verification script:

```bash
python verify_install.py
```

This checks all required packages and reports any issues.

**Expected Output:**
```
✓ NiceGUI - Web UI Framework          [REQUIRED]
✓ Uvicorn - ASGI Server              [REQUIRED]
✓ Requests - HTTP Client             [REQUIRED]
✓ BeautifulSoup4 - HTML Parsing      [REQUIRED]
✓ Faster Whisper - STT               [REQUIRED]
✓ Piper TTS - Text-to-Speech         [REQUIRED]
...

✓ Installation Verified - Ready to Use!
```

---

## Running the Application

### Start the ZEN_AI_RAG UI
```bash
python zena.py
```

This launches the NiceGUI interface on `http://127.0.0.1:8080`

### Running Tests
```bash
pytest tests/
```

Or run specific tests:
```bash
python -m pytest tests/test_voice_manager.py
python -m pytest tests/test_zen_integration.py
```

---

## Troubleshooting

### Problem: "Python not found"
**Solution:** Install Python 3.12+ from https://www.python.org
- Check "Add Python to PATH" during installation
- Restart terminal after installation

### Problem: "BeautifulSoup not found"
**Solution:**
```bash
pip install beautifulsoup4 --upgrade
```

### Problem: "Virtual environment already exists"
**Solution:** Delete it and start fresh
```bash
# Windows
rmdir /s venv

# Linux / macOS
rm -rf venv
```
Then run `install.bat` or `install.sh` again

### Problem: Pip install fails / network timeout
**Solution:** Try with a different PyPI mirror
```bash
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

### Problem: Missing voice device support
**Solution:** Ensure SoundDevice is installed
```bash
pip install sounddevice --upgrade
```

Check available devices:
```python
python -c "import sounddevice as sd; print(sd.query_devices())"
```

---

## Key Dependencies

### Core Framework
- **NiceGUI** - Modern Python web UI framework
- **Uvicorn** - ASGI web server

### LLM & RAG
- **Qdrant** - Vector database for embeddings
- **Sentence Transformers** - Embedding generation
- **BM25** - Ranking algorithm

### Voice I/O
- **Faster Whisper** - Speech-to-text (STT)
- **Piper TTS** - Text-to-speech synthesis
- **SoundDevice** - Audio hardware interface

### Document Processing
- **BeautifulSoup4** - HTML parsing
- **PyPDF2** - PDF reading
- **PyMuPDF** - Advanced PDF processing

### Data Science
- **NumPy** - Numerical computing
- **SciPy** - Scientific computing
- **FAISS** - Vector similarity search

---

## Environment Variables

Create a `.env` file in the project root:

```env
# LLM Configuration
LLM_PORT=8001
MODEL_DIR=C:\AI\Models
BIN_DIR=C:\AI\_bin

# Application
DEBUG=False
NICEGUI_HOST=127.0.0.1
NICEGUI_PORT=8080

# Voice
STT_MODEL=base.en
TTS_VOICE=en_US-lessac-medium
AUDIO_DEVICE=default
```

---

## Project Structure

```
ZEN_AI_RAG/
├── install.bat              ← Run this on Windows
├── install.sh               ← Run this on Linux/macOS
├── verify_install.py        ← Verify installation
├── requirements.txt         ← All dependencies
├── zena.py                  ← Main application
├── config.py                ← Configuration
├── voice_service.py         ← Voice I/O
├── zena_mode/              ← Core modules
│   ├── heart_and_brain.py   ← LLM management
│   ├── voice_manager.py     ← Voice orchestration
│   ├── handlers/            ← API endpoints
│   └── ...
├── ui/                      ← UI components
├── local_llm/               ← LLM detection
└── models/                  ← GGUF model storage
```

---

## First Run Checklist

- [ ] Run `install.bat` or `install.sh`
- [ ] Run `python verify_install.py` - all green ✓
- [ ] Check `models/` directory has GGUF files
- [ ] Check `_bin/` has `llama-server.exe` (Windows) or `llama-server` (Linux)
- [ ] Run `python zena.py`
- [ ] Open http://127.0.0.1:8080 in browser
- [ ] Test voice recording
- [ ] Test text-to-speech playback

---

## Getting Help

1. Check `PHASE5_COMPLETION.md` for architecture details
2. Read `README.md` for project overview
3. Run `verify_install.py` to check all dependencies
4. Check logs in `docs/` directory
5. Run tests: `pytest tests/ -v`

---

## Production Deployment

For production use:

1. **Use `requirements.txt`** with pinned versions (already done)
2. **Set environment variables** for your deployment
3. **Test with `verify_install.py`** before deploying
4. **Run full test suite** before production
5. **Monitor logs** in `docs/` directory

---

**Last Updated:** February 5, 2026  
**Status:** Production Ready  
**Python Version:** 3.12+
