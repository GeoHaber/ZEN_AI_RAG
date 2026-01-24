# Bootstrap Improvements for Zero-Config Distribution

**Date:** 2026-01-23
**Current Status:** Manual setup required
**Proposed:** Automatic setup

---

## Current Behavior

### What `start_llm.py` Does Now:

**When llama-server.exe is MISSING:**
```
❌ Shows error: "Please run: python download_deps.py"
❌ Exits (no auto-download)
```

**When models are MISSING:**
```
❌ Starts in MANAGER MODE (Hub Only)
❌ Shows: "Please open the Web UI to download a model"
❌ User must manually download via UI
```

**When Python packages are MISSING:**
```
❌ Shows error: "Run 'pip install -r requirements.txt'"
❌ Exits (no auto-install)
```

---

## User Experience Issues

### Scenario: New User Extracts Zip

**Step 1:** User extracts `ZenAI_RAG_Complete.zip`

**Step 2:** User runs `python start_llm.py`

**Step 3:** User sees errors:
```
[!] Server binary not found at _bin/llama-server.exe
    Please run: python download_deps.py
```

**Step 4:** User runs `python download_deps.py`

**Step 5:** User runs `python start_llm.py` again

**Step 6:** User sees:
```
[!] No models found in: C:/AI/Models
[*] Starting in MANAGER MODE (Hub Only)
    Please open the Web UI to download a model.
```

**Step 7:** User opens browser, downloads model (4-8 GB download)

**Step 8:** User restarts `python start_llm.py`

**Step 9:** Finally works!

**Result:** 9 steps, multiple runs, confusing

---

## Proposed Improvements

### Option 1: Auto-Download Everything (Recommended)

**Enhanced `start_llm.py` behavior:**

```python
def start_server():
    # Check 1: Binary
    if not SERVER_EXE.exists():
        print("[AUTO-SETUP] llama-server.exe not found")
        print("[AUTO-SETUP] Downloading llama.cpp binaries...")

        # Auto-run download_deps.py
        import download_deps
        download_deps.download_llama()

        if not SERVER_EXE.exists():
            print("[ERROR] Auto-download failed")
            print("[MANUAL] Please run: python download_deps.py")
            sys.exit(1)

    # Check 2: Models
    if not list(MODEL_DIR.glob("*.gguf")):
        print("[AUTO-SETUP] No models found")
        print("[AUTO-SETUP] Would you like to download Qwen2.5-Coder-7B? (4.5 GB)")

        response = input("Download now? (y/n): ").strip().lower()

        if response == 'y':
            print("[AUTO-SETUP] Downloading model...")
            # Auto-download default model
            from model_manager import download_model
            download_model("bartowski/Qwen2.5-Coder-7B-Instruct-GGUF",
                          "Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf")
        else:
            print("[MANAGER MODE] Starting Hub for manual download...")
            start_hub()
            return
```

**User Experience:**
```
User: python start_llm.py

[AUTO-SETUP] llama-server.exe not found
[AUTO-SETUP] Downloading llama.cpp binaries...
[OK] Downloaded 9 MB binary

[AUTO-SETUP] No models found
[AUTO-SETUP] Would you like to download Qwen2.5-Coder-7B? (4.5 GB)
Download now? (y/n): y

[AUTO-SETUP] Downloading model...
[PROGRESS] 1.2 GB / 4.5 GB (27%)...
[OK] Model downloaded

[SUCCESS] Starting ZenAI...
```

**Result:** 1 run, user prompted once, works!

---

### Option 2: Interactive Setup Script

Create `setup.py`:

```python
#!/usr/bin/env python3
"""
ZenAI Setup Wizard
One-time interactive setup for new installations
"""

def main():
    print("="*60)
    print("ZENAI SETUP WIZARD")
    print("="*60)

    # Step 1: Python dependencies
    print("\n[1/3] Installing Python dependencies...")
    os.system("pip install -r requirements.txt")

    # Step 2: llama.cpp binaries
    print("\n[2/3] Downloading llama.cpp binaries...")
    import download_deps
    download_deps.download_llama()

    # Step 3: Model
    print("\n[3/3] Downloading AI model...")
    print("Recommended: Qwen2.5-Coder-7B (4.5 GB)")

    response = input("Download now? (y/n): ").strip().lower()

    if response == 'y':
        from model_manager import download_model
        download_model("bartowski/Qwen2.5-Coder-7B-Instruct-GGUF",
                      "Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf")

    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("\nRun: python start_llm.py")
```

**User Experience:**
```
User: python setup.py

[1/3] Installing Python dependencies...
[OK] Installed 12 packages

[2/3] Downloading llama.cpp binaries...
[OK] Downloaded llama-server.exe (9 MB)

[3/3] Downloading AI model...
Download now? (y/n): y
[OK] Downloaded Qwen2.5-Coder-7B (4.5 GB)

SETUP COMPLETE!

Run: python start_llm.py
```

---

### Option 3: Batch/Shell Scripts

Create `setup.bat` (Windows) and `setup.sh` (Linux/Mac):

**setup.bat:**
```batch
@echo off
echo ====================================
echo ZENAI SETUP
echo ====================================

echo [1/3] Installing Python packages...
pip install -r requirements.txt

echo [2/3] Downloading llama.cpp binaries...
python download_deps.py

echo [3/3] Setup complete!
echo Run: python start_llm.py
pause
```

**User Experience:**
```
User: Double-click setup.bat

[Automatic execution]
[1/3] Installing Python packages...
[2/3] Downloading llama.cpp binaries...
[3/3] Setup complete!

Press any key to continue...
```

---

## Recommended Solution

### Hybrid Approach (Best of All Options)

1. **Create `setup.py`** - One-time interactive setup
2. **Enhance `start_llm.py`** - Auto-download binaries if missing
3. **Keep MANAGER MODE** - For model downloads (large files)

**Package includes:**
```
ZenAI_RAG_Complete.zip
├── setup.py          (NEW - one-time setup wizard)
├── start_llm.py      (ENHANCED - auto-download binaries)
├── download_deps.py  (existing)
├── requirements.txt
└── ... (rest of files)
```

**First-time user flow:**
```
Step 1: Extract zip
Step 2: Run setup.py (installs packages, downloads binaries)
Step 3: Run start_llm.py (auto-downloads model if needed)
Step 4: Working!
```

**Subsequent runs:**
```
Step 1: Run start_llm.py
Step 2: Working!
```

---

## Implementation Plan

### Phase 1: Create setup.py

```python
#!/usr/bin/env python3
"""
ZenAI Setup Wizard - One-time interactive setup
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Ensure Python 3.10+"""
    if sys.version_info < (3, 10):
        print("[ERROR] Python 3.10+ required")
        print(f"[ERROR] You have: Python {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)

def install_dependencies():
    """Install Python packages from requirements.txt"""
    print("\n[1/4] Installing Python dependencies...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                          capture_output=True, text=True)

    if result.returncode != 0:
        print("[ERROR] Package installation failed")
        print(result.stderr)
        sys.exit(1)

    print("[OK] Python dependencies installed")

def download_binaries():
    """Download llama.cpp binaries"""
    print("\n[2/4] Downloading llama.cpp binaries...")

    import download_deps
    download_deps.download_llama()

    # Verify
    bin_dir = Path("_bin")
    llama_exe = bin_dir / "llama-server.exe" if sys.platform == "win32" else bin_dir / "llama-server"

    if llama_exe.exists():
        print(f"[OK] Binary ready: {llama_exe}")
    else:
        print("[WARNING] Binary may not have downloaded correctly")

def setup_model_directory():
    """Create model directory if it doesn't exist"""
    print("\n[3/4] Setting up model directory...")

    model_dir = Path.home() / "AI" / "Models"
    model_dir.mkdir(parents=True, exist_ok=True)

    print(f"[OK] Model directory: {model_dir}")

def download_model_optional():
    """Optionally download a model"""
    print("\n[4/4] Downloading AI model (optional)...")
    print("Recommended: Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf (4.5 GB)")
    print("You can skip this and download later via the UI")

    response = input("\nDownload now? (y/n): ").strip().lower()

    if response == 'y':
        print("[DOWNLOAD] Starting model download...")
        print("[NOTE] This may take 10-30 minutes depending on your connection")

        try:
            from model_manager import download_model
            download_model("bartowski/Qwen2.5-Coder-7B-Instruct-GGUF",
                          "Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf")
            print("[OK] Model downloaded successfully")
        except Exception as e:
            print(f"[ERROR] Download failed: {e}")
            print("[NOTE] You can download manually via the UI later")
    else:
        print("[SKIP] Model download skipped")
        print("[NOTE] On first run, start_llm.py will open the UI for model download")

def main():
    print("=" * 60)
    print(" " * 20 + "ZENAI SETUP WIZARD")
    print("=" * 60)

    check_python_version()
    install_dependencies()
    download_binaries()
    setup_model_directory()
    download_model_optional()

    print("\n" + "=" * 60)
    print(" " * 20 + "SETUP COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Run: python start_llm.py")
    print("  2. Open browser at: http://localhost:8080")
    print("  3. Start chatting with Zena!")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
```

### Phase 2: Update README.md

```markdown
# ZenAI - Quick Start

## Installation (3 Easy Steps)

### Step 1: Extract
```bash
unzip ZenAI_RAG_Complete.zip
cd ZenAI
```

### Step 2: Run Setup (First Time Only)
```bash
python setup.py
```

This will:
- Install Python dependencies
- Download llama.cpp binaries (9 MB)
- Optionally download AI model (4.5 GB)

### Step 3: Start ZenAI
```bash
python start_llm.py
```

Open browser at: http://localhost:8080

## That's It!

For subsequent runs, just: `python start_llm.py`
```

---

## Summary

### Current State: ❌ Manual Setup Required
- User must run 3+ commands
- Multiple restarts needed
- Confusing error messages

### Proposed State: ✅ Automated Setup
- User runs `setup.py` once
- Everything auto-downloads
- Clear progress messages
- Single restart

### Files to Add/Modify:
1. ✅ Create `setup.py` (new file)
2. ✅ Update `README.md` (with setup instructions)
3. ⏳ Optional: Enhance `start_llm.py` (auto-download binaries)
4. ⏳ Optional: Create `setup.bat` (Windows double-click)

---

**Recommendation:** Implement `setup.py` for next version to achieve true zero-config distribution!
