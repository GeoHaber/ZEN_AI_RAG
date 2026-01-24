# Startup Validation Feature

**Date:** 2026-01-22
**Status:** ✅ Complete & Tested

---

## Overview

Added comprehensive pre-flight validation to `start_llm.py` that checks for binaries, models, and dependencies **before** attempting to start services. This prevents confusing error messages and provides clear remediation steps.

---

## What Gets Validated

### 1. **Binary Existence** (Critical)
Checks if `llama-server.exe` exists at the configured path.

**If missing:**
- Shows error with exact path
- Provides fix: "Run 'python download_deps.py' to download binaries"
- Exits with error code 1

### 2. **Model Availability** (Warning)
Checks if `.gguf` model files exist in configured `model_dir`.

**If missing:**
- Shows warning (non-blocking)
- App starts in MANAGER MODE (Hub only)
- User can download models via UI

**If found:**
- Lists first 3 models with sizes
- Shows total count

### 3. **Required Python Packages** (Critical)
Checks for essential dependencies:
- `nicegui` - UI framework
- `httpx` - HTTP client
- `faiss` - Vector search (FAISS)

**If missing:**
- Shows error with package names
- Provides fix: "Run 'pip install -r requirements.txt'"
- Exits with error code 1

### 4. **Optional Features** (Informational)
Checks for optional dependencies:
- `torch` - Voice STT (Whisper)
- `pyttsx3` - Voice TTS
- `PyPDF2` - PDF support

**If missing:**
- Shows `[SKIP]` message (non-blocking)
- App continues without those features

---

## Example Output

### All Checks Pass ✅
```
============================================================
PRE-FLIGHT VALIDATION
============================================================
[1/4] Checking binary at: C:\...\llama-server.exe
      [OK] Binary found: llama-server.exe (128 MB)
[2/4] Checking models in: C:\AI\Models
      [OK] Found 13 model(s):
         - deepseek-coder-6.7b-instruct.Q4_K_M.gguf (3893 MB)
         - DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf (8571 MB)
         - gemma-2-9b-it-Q4_K_M.gguf (5494 MB)
         ... and 10 more
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
```

### Binary Missing ❌
```
============================================================
PRE-FLIGHT VALIDATION
============================================================
[1/4] Checking binary at: C:\...\llama-server.exe
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

[X] CRITICAL ISSUES DETECTED:

1. Binary Not Found:
   llama-server.exe not found at:
       C:\Users\...\llama-server.exe

       Fix: Run 'python download_deps.py' to download binaries

============================================================

[!] Cannot start application due to critical issues.
[!] Please fix the issues above and try again.
```

### No Models (Warning Only) ⚠️
```
============================================================
PRE-FLIGHT VALIDATION
============================================================
[1/4] Checking binary at: C:\...\llama-server.exe
      [OK] Binary found: llama-server.exe (128 MB)
[2/4] Checking models in: C:\AI\Models
[3/4] Checking Python dependencies...
      [OK] NiceGUI (UI framework)
      [OK] HTTP client
      [OK] FAISS (vector search)
[4/4] Checking optional features...
      [OK] Voice STT (Whisper)
      [SKIP] Voice TTS - not available
      [OK] PDF support
============================================================

[!] WARNINGS:

1. No Models Found:
   No .gguf models in C:\AI\Models
       App will start in MANAGER MODE (Hub only)
       Use the UI to download a model

============================================================

[*] Continuing with warnings...
```

---

## Usage

### Normal Startup (with validation)
```bash
python start_llm.py
```

### Skip Validation (for testing)
```bash
python start_llm.py --skip-validation
```

### Hub Only Mode (with validation)
```bash
python start_llm.py --hub-only
```

---

## Benefits

### Before (No Validation)
- App would start and fail mysteriously
- Error messages buried in logs
- User confused about what's missing
- No clear remediation steps

### After (With Validation)
- **Clear status report** before startup
- **Exact file paths** shown for missing components
- **Specific fix commands** provided
- **Exit early** if critical issues detected
- **Continue with warnings** for optional features

---

## Implementation Details

### File Modified
- `start_llm.py` - Added `validate_environment()` function (lines 28-128)

### Function Structure
```python
def validate_environment():
    """Pre-flight validation: Check binaries, models, and dependencies."""

    issues = []      # Critical - blocks startup
    warnings = []    # Non-critical - continue with message

    # Check 1: Binary
    # Check 2: Models
    # Check 3: Required packages
    # Check 4: Optional packages

    if issues:
        # Display issues and exit
        sys.exit(1)

    if warnings:
        # Display warnings and continue
        pass

    return True
```

### Integration Point
```python
if __name__ == "__main__":
    # Run pre-flight validation (unless bypassed)
    if "--skip-validation" not in sys.argv:
        validate_environment()

    # Continue with normal startup...
```

---

## Error Handling

### Critical Issues (Exit with Error)
- Binary not found
- Required Python packages missing
- Model directory not accessible (if created)

### Warnings (Continue with Message)
- No models found (Manager Mode)
- Optional features unavailable

---

## Windows Console Compatibility

**Issue:** Original version used Unicode emojis (🔍, ✅, ❌, ⚠️) which don't render in Windows `cmd.exe` or PowerShell with default codepage (cp1252).

**Solution:** Changed to ASCII-safe markers:
- `🔍` → `PRE-FLIGHT VALIDATION`
- `✅` → `[OK]`
- `❌` → `[X]`
- `⚠️` → `[!]` or `[SKIP]`

This ensures validation output works on all Windows terminals without UnicodeEncodeError.

---

## Future Enhancements (Optional)

1. **Auto-download missing binaries** - Offer to run `download_deps.py` automatically
2. **Check disk space** - Warn if insufficient space for models
3. **Network connectivity** - Test if able to download models
4. **Port availability** - Check if ports 8001, 8002, 8003, 8080 are free
5. **Version checks** - Verify Python version, package versions
6. **GPU detection** - Show CUDA/ROCm availability

---

## Testing

All validation scenarios tested:

✅ All components present - passes validation
✅ Binary missing - exits with error
✅ Packages missing - exits with error
✅ Models missing - shows warning, continues
✅ Optional features missing - shows info, continues
✅ Skip validation flag works

---

## User Experience Improvement

### Before
```
User: python start_llm.py
...
[!] Server binary not found at C:\...\llama-server.exe
[Cryptic subprocess error]
User: "What? Where do I get it?"
```

### After
```
User: python start_llm.py

============================================================
PRE-FLIGHT VALIDATION
============================================================
[1/4] Checking binary at: C:\...\llama-server.exe
...

[X] CRITICAL ISSUES DETECTED:

1. Binary Not Found:
   llama-server.exe not found at:
       C:\Users\...\llama-server.exe

       Fix: Run 'python download_deps.py' to download binaries

============================================================

User: "Oh, I need to run download_deps.py first!"
```

---

## Conclusion

The startup validation feature provides **proactive error detection** with **clear remediation steps**, improving the user experience and reducing support burden.

**Status:** ✅ Production ready
**Location:** start_llm.py:28-128
**Flag to skip:** --skip-validation

---

*Feature implemented in response to user request: "downloading and library model checking should be in the start file dont you think so ??"*
