# Setup Manager - Comprehensive Setup System

**Date:** 2026-01-22
**Status:** ✅ Complete & Ready for PyInstaller

---

## Overview

The **Setup Manager** is a comprehensive, standalone Python module that handles:
- CPU/GPU hardware detection
- Automatic binary downloads (llama.cpp)
- Dependency installation
- Configuration validation

**Key Feature:** Designed to be bundled into executables (PyInstaller, Nuitka) for distribution.

---

## Why This Was Created

### Problem
The user requested:
> "the CPU detection and downloading the proper llama.cpp and or other necessary components should be in a Python file so that if in the future we create an executable its all included"

### Solution
All setup logic is now in a single, self-contained `setup_manager.py` module that:
1. Detects hardware capabilities (CPU features, GPU)
2. Downloads optimal binaries for the detected hardware
3. Installs missing dependencies
4. Can be bundled into executables

---

## Architecture

### Components

#### 1. **HardwareDetector** (Lines 18-122)
Detects system hardware capabilities.

**Methods:**
- `detect_cpu_features()` - Detects AVX, AVX2, AVX512, FMA, SSE4.1/4.2
- `detect_gpu()` - Detects NVIDIA CUDA, AMD ROCm
- `get_optimal_binary_type()` - Returns best binary variant

**Detection Logic:**
```
Priority 1: CUDA 12 (if NVIDIA GPU with CUDA 12+)
Priority 2: CUDA 11 (if NVIDIA GPU with CUDA 11)
Priority 3: CPU AVX512 (if CPU supports AVX-512)
Priority 4: CPU AVX2 (if CPU supports AVX2)
Priority 5: CPU AVX (if CPU supports AVX)
Fallback:   CPU (basic)
```

**Platform Support:**
- Windows: Uses `wmic` or `py-cpuinfo` package
- Linux: Reads `/proc/cpuinfo`
- macOS: Uses `sysctl`

#### 2. **BinaryDownloader** (Lines 125-258)
Downloads and installs llama.cpp binaries from GitHub.

**Methods:**
- `get_latest_release()` - Fetches latest release from GitHub API
- `find_best_asset()` - Matches binary to system (platform, arch, CPU/GPU)
- `download_and_extract()` - Downloads ZIP with progress, extracts to `_bin/`
- `install()` - Main installation orchestrator

**Download Pattern Matching:**
```python
# For CUDA builds
"llama-.*cuda-cu12.*win.*x64.*\\.zip"

# For CPU builds
"llama-.*bin-win.*x64.*\\.zip"
```

**Progress Display:**
```
[Setup] Downloading llama-b3942-bin-win-cuda-cu12-x64.zip...
[Setup] Size: 145 MB
[Setup] Progress: 47.3%
```

#### 3. **DependencyChecker** (Lines 261-307)
Checks and installs Python packages.

**Required Packages:**
- `nicegui` - UI framework
- `httpx` - HTTP client
- `faiss-cpu` - Vector search
- `sentence-transformers` - Embeddings
- `numpy` - Numerical computation
- `PyPDF2` - PDF support

**Optional Packages:**
- `torch` - PyTorch for Whisper STT
- `pyttsx3` - Text-to-speech
- `sounddevice` - Audio input
- `scipy` - Scientific computing
- `py-cpuinfo` - CPU detection

**Methods:**
- `check_package()` - Check if package installed
- `install_package()` - Install via pip
- `check_and_install_dependencies()` - Check all and auto-install

#### 4. **SetupManager** (Lines 310-412)
Main orchestrator that ties everything together.

**Methods:**
- `detect_hardware()` - Display hardware info
- `setup_binaries()` - Download binaries
- `check_dependencies()` - Check/install packages
- `verify_config()` - Update config.json paths
- `run_full_setup()` - Run complete setup process

---

## Usage

### Interactive Mode (Recommended for First-Time Setup)

```bash
python setup_manager.py --auto-install
```

**What it does:**
1. Detects your CPU/GPU
2. Shows hardware capabilities
3. Downloads optimal llama.cpp binary
4. Installs missing Python packages
5. Updates config.json

**Example Output:**
```
======================================================================
               ZENA AI - SETUP MANAGER
======================================================================

============================================================
HARDWARE DETECTION
============================================================
Platform: win32
Architecture: AMD64
CPU Features:
  ✓ AVX
  ✓ AVX2
  ✗ AVX512
  ✓ FMA
  ✓ SSE4_1
  ✓ SSE4_2

GPU: NVIDIA GeForce RTX 3080
CUDA Version: 12.3

Recommended Build: cuda-cu12
============================================================

============================================================
BINARY SETUP
============================================================
[Setup] Fetching latest llama.cpp release...
[Setup] Latest version: b3942
[Setup] Detected optimal build: cuda-cu12
[Setup] Downloading llama-b3942-bin-win-cuda-cu12-x64.zip...
[Setup] Size: 145 MB
[Setup] Progress: 100.0%
[Setup] Extracting binaries...
[Setup] Extracted 23 files
[Setup] ✓ Binary installed: llama-server.exe
============================================================

============================================================
DEPENDENCY CHECK
============================================================
[Setup] Checking Python dependencies...
  ✓ nicegui
  ✓ httpx
  ✓ faiss-cpu
  ✓ sentence-transformers
  ✓ numpy
  ✓ PyPDF2

[Setup] ✓ All required dependencies available!
============================================================

======================================================================
SETUP COMPLETE! ✓
======================================================================

You can now run:
  python start_llm.py

To open the UI:
  http://localhost:8080
======================================================================
```

### Command-Line Options

#### Detect Hardware Only
```bash
python setup_manager.py --detect-only
```
Shows CPU/GPU info without installing anything.

#### Download Binaries Only
```bash
python setup_manager.py --binaries-only
```
Only downloads llama.cpp binaries (no dependency check).

#### Check/Install Dependencies Only
```bash
python setup_manager.py --deps-only --auto-install
```
Only checks and installs Python packages.

#### Force Reinstall Binaries
```bash
python setup_manager.py --force --auto-install
```
Re-downloads binaries even if they already exist.

---

## Integration with start_llm.py

The validation in `start_llm.py` now offers **automatic setup** when issues are detected:

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
      ...
============================================================

[X] CRITICAL ISSUES DETECTED:

1. Binary Not Found:
   llama-server.exe not found at:
       C:\Users\...\llama-server.exe

       Fix: Run 'python download_deps.py' to download binaries

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

**User presses 'Y':**
- Runs `SetupManager.run_full_setup()`
- Downloads binaries
- Installs dependencies
- Updates config.json
- Prompts user to restart application

---

## PyInstaller Compatibility

### Design Decisions for Executable Bundling

1. **No External Scripts**
   - All logic in single Python file
   - No dependencies on shell scripts or batch files

2. **Self-Contained Logic**
   - Hardware detection uses Python libraries or system calls
   - Downloads binaries to `_bin/` directory relative to executable

3. **Graceful Fallbacks**
   - If `py-cpuinfo` not available, uses `wmic` (Windows) or `/proc/cpuinfo` (Linux)
   - If GPU detection fails, defaults to CPU mode

4. **Standard Library First**
   - Uses `subprocess`, `platform`, `sys` for detection
   - Only external dependency: `requests` (for downloads)

### Example PyInstaller Spec

```python
# zena_ai.spec
a = Analysis(
    ['start_llm.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('setup_manager.py', '.'),  # Include setup manager
    ],
    hiddenimports=[
        'setup_manager',
        'requests',
        'py-cpuinfo',
    ],
    ...
)
```

---

## Hardware Detection Details

### CPU Feature Detection

**Windows:**
```
1. Try py-cpuinfo package (if installed)
2. Fallback to wmic command:
   wmic cpu get caption
3. Assume modern CPU (AVX2) if Intel/AMD detected
```

**Linux:**
```
1. Read /proc/cpuinfo
2. Search for flags: avx, avx2, avx512, fma, sse4_1, sse4_2
```

**macOS:**
```
1. Run sysctl -a
2. Search for: avx1.0, avx2.0
```

### GPU Detection

**NVIDIA (Windows/Linux):**
```
1. Run nvidia-smi --query-gpu=name,driver_version
2. Parse CUDA version from nvidia-smi output
3. Determine CUDA 11 vs 12 for binary selection
```

**AMD ROCm (Linux):**
```
1. Check for rocm-smi command
2. Parse GPU info
```

**Fallback:**
```
If no GPU detected, use CPU binary
```

---

## Binary Selection Logic

```python
def get_optimal_binary_type() -> str:
    gpu_info = detect_gpu()
    cpu_features = detect_cpu_features()

    # Priority 1: CUDA
    if gpu_info['has_nvidia']:
        cuda_major = int(gpu_info['cuda_version'].split('.')[0])
        if cuda_major >= 12:
            return 'cuda-cu12'  # CUDA 12.x
        elif cuda_major >= 11:
            return 'cuda-cu11'  # CUDA 11.x

    # Priority 2: CPU with best instruction set
    if cpu_features['avx512']:
        return 'cpu-avx512'
    elif cpu_features['avx2']:
        return 'cpu-avx2'
    elif cpu_features['avx']:
        return 'cpu-avx'

    # Fallback
    return 'cpu'
```

---

## Error Handling

### Network Errors
```python
try:
    response = requests.get(GITHUB_API, timeout=10)
    response.raise_for_status()
except requests.RequestException as e:
    print(f"[Setup] Network error: {e}")
    print("[Setup] Please check your internet connection")
    sys.exit(1)
```

### Extraction Errors
```python
try:
    with zipfile.ZipFile(temp_path, 'r') as zip_ref:
        zip_ref.extractall(self.install_dir)
except zipfile.BadZipFile:
    print("[Setup] Downloaded file is corrupted")
    print("[Setup] Please try again")
    sys.exit(1)
```

### Permission Errors
```python
try:
    self.install_dir.mkdir(parents=True, exist_ok=True)
except PermissionError:
    print(f"[Setup] Permission denied: {self.install_dir}")
    print("[Setup] Try running as administrator")
    sys.exit(1)
```

---

## Testing

### Test Hardware Detection
```bash
python setup_manager.py --detect-only
```

Expected output shows CPU features and GPU info.

### Test Binary Download (Dry Run)
```bash
python setup_manager.py --binaries-only
```

Verifies GitHub API access and binary matching logic.

### Test Full Setup
```bash
# Clean slate
rm -rf _bin/
python setup_manager.py --auto-install
```

Should complete successfully and create `_bin/llama-server.exe`.

---

## Comparison with Legacy download_deps.py

### Old System (download_deps.py)
```python
# Hardcoded priority order
if "cuda-12" in name:
    # Use this
elif "cpu" in name:
    # Use this
```

**Issues:**
- No hardware detection
- Downloads same binary for all users
- No dependency checking
- Manual fallback required

### New System (setup_manager.py)
```python
# Dynamic detection
binary_type = HardwareDetector.get_optimal_binary_type()
# Returns: cuda-cu12, cpu-avx512, cpu-avx2, etc.
```

**Benefits:**
- Detects user's hardware
- Downloads optimal binary
- Checks all dependencies
- Fully automated
- PyInstaller-ready

---

## Future Enhancements

1. **Multi-GPU Support**
   - Detect multiple GPUs
   - Allow user to select GPU

2. **Model Downloads**
   - Integrate model downloads into setup
   - Recommend models based on RAM

3. **Offline Mode**
   - Bundle common binaries in executable
   - Extract appropriate binary without download

4. **Update Checker**
   - Check for newer llama.cpp releases
   - Offer to upgrade existing installation

5. **Uninstaller**
   - Clean removal of binaries and config
   - Reset to fresh state

---

## Files

### Created
- `setup_manager.py` (415 lines) - Complete setup system

### Modified
- `start_llm.py` - Added automatic setup offer in validation
- `STARTUP_VALIDATION.md` - Updated with setup manager integration

### Deprecated
- `download_deps.py` - Still works but `setup_manager.py` is preferred

---

## Summary

The **Setup Manager** provides:

✅ **Hardware detection** - CPU/GPU capabilities
✅ **Optimal binary selection** - Best binary for user's system
✅ **Automatic downloads** - From GitHub with progress
✅ **Dependency management** - Check and install Python packages
✅ **PyInstaller ready** - Self-contained, no external scripts
✅ **User-friendly** - Interactive prompts, clear messages
✅ **Integrated validation** - Works with start_llm.py validation

**Result:** Users can run `python start_llm.py`, get prompted for setup if needed, press 'Y', and have everything installed automatically!

---

*Feature created in response to: "the CPU detection and downloading the proper llama.cpp and or other necessary components should be in a Python file so that if in the future we create an executable its all included"*
