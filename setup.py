#!/usr/bin/env python3
"""
ZenAI Setup Wizard - One-time interactive setup

Automates:
1. Python dependency installation
2. llama.cpp binary download
3. Model directory creation
4. Optional model download
"""

import os
import sys
import subprocess
from pathlib import Path

def safe_print(msg):
    """Print with encoding fallback for Windows."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))

def check_python_version():
    """Ensure Python 3.10+"""
    safe_print("\n" + "=" * 60)
    safe_print("ZENAI SETUP WIZARD")
    safe_print("=" * 60)

    safe_print("\n[CHECK] Python version...")

    if sys.version_info < (3, 10):
        safe_print(f"[ERROR] Python 3.10+ required")
        safe_print(f"[ERROR] You have: Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        safe_print("\n[FIX] Download Python 3.12 from: https://www.python.org/downloads/")
        sys.exit(1)

    safe_print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

def install_dependencies():
    """Install Python packages from requirements.txt"""
    safe_print("\n[STEP 1/4] Installing Python dependencies...")

    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        safe_print("[ERROR] requirements.txt not found!")
        sys.exit(1)

    safe_print("[INFO] This may take 1-2 minutes...")

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        safe_print("[ERROR] Package installation failed")
        safe_print(result.stderr)
        safe_print("\n[MANUAL FIX] Try: pip install -r requirements.txt")
        sys.exit(1)

    safe_print("[OK] Python dependencies installed")

def download_binaries():
    """Download llama.cpp binaries"""
    safe_print("\n[STEP 2/4] Downloading llama.cpp binaries...")

    bin_dir = Path("_bin")
    llama_exe = bin_dir / "llama-server.exe" if sys.platform == "win32" else bin_dir / "llama-server"

    # Check if already downloaded
    if llama_exe.exists():
        size_mb = llama_exe.stat().st_size / (1024 * 1024)
        safe_print(f"[SKIP] Binary already exists: {llama_exe.name} ({size_mb:.1f} MB)")
        return

    safe_print("[INFO] Downloading from GitHub (llama.cpp latest release)...")
    safe_print("[INFO] This may take 1-2 minutes...")

    try:
        import download_deps
        download_deps.download_llama()
    except Exception as e:
        safe_print(f"[ERROR] Download failed: {e}")
        safe_print("\n[MANUAL FIX] Try: python download_deps.py")
        sys.exit(1)

    # Verify
    if llama_exe.exists():
        size_mb = llama_exe.stat().st_size / (1024 * 1024)
        safe_print(f"[OK] Binary downloaded: {llama_exe.name} ({size_mb:.1f} MB)")
    else:
        safe_print("[ERROR] Binary download verification failed")
        safe_print("[MANUAL FIX] Try: python download_deps.py")
        sys.exit(1)

def setup_model_directory():
    """Create model directory if it doesn't exist"""
    safe_print("\n[STEP 3/4] Setting up model directory...")

    # Check config.py for MODEL_DIR
    try:
        from config import MODEL_DIR
        model_dir = Path(MODEL_DIR)
    except ImportError:
        # Fallback to default
        model_dir = Path.home() / "AI" / "Models"

    model_dir.mkdir(parents=True, exist_ok=True)

    safe_print(f"[OK] Model directory ready: {model_dir}")

    # Check if models already exist
    gguf_models = list(model_dir.glob("*.gguf"))
    if gguf_models:
        safe_print(f"[INFO] Found {len(gguf_models)} existing model(s):")
        for model in gguf_models[:3]:
            size_mb = model.stat().st_size / (1024 * 1024)
            safe_print(f"  - {model.name} ({size_mb:.0f} MB)")
        if len(gguf_models) > 3:
            safe_print(f"  ... and {len(gguf_models) - 3} more")
        return True  # Has models

    return False  # No models

def download_model_optional(has_models):
    """Optionally download a model"""
    safe_print("\n[STEP 4/4] AI Model Setup...")

    if has_models:
        safe_print("[SKIP] Models already present, skipping download")
        return

    safe_print("\n[OPTION] Download recommended model:")
    safe_print("  Model: Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf")
    safe_print("  Size:  ~4.5 GB")
    safe_print("  Time:  10-30 minutes (depends on connection)")
    safe_print("\n[NOTE] You can skip this and download later via the Web UI")

    try:
        response = input("\nDownload now? (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        safe_print("\n[SKIP] Model download skipped")
        return

    if response == 'y':
        safe_print("\n[DOWNLOAD] Starting model download...")
        safe_print("[INFO] Progress will be shown below...")
        safe_print("[INFO] You can press Ctrl+C to cancel")

        try:
            # Import model_manager (needs dependencies installed)
            from model_manager import download_model

            # Download recommended model
            download_model(
                "bartowski/Qwen2.5-Coder-7B-Instruct-GGUF",
                "Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf"
            )

            safe_print("\n[OK] Model downloaded successfully!")

        except KeyboardInterrupt:
            safe_print("\n[CANCELLED] Download cancelled by user")
            safe_print("[NOTE] You can download later via the Web UI")
        except Exception as e:
            safe_print(f"\n[ERROR] Download failed: {e}")
            safe_print("[NOTE] You can download later via the Web UI")
    else:
        safe_print("\n[SKIP] Model download skipped")
        safe_print("[NOTE] On first run, start_llm.py will open the Web UI")
        safe_print("[NOTE] You can download a model through the interface")

def print_next_steps():
    """Print next steps after setup"""
    safe_print("\n" + "=" * 60)
    safe_print("SETUP COMPLETE!")
    safe_print("=" * 60)

    safe_print("\nNext steps:")
    safe_print("  1. Run: python start_llm.py")
    safe_print("  2. Open browser at: http://localhost:8080")
    safe_print("  3. Start chatting with Zena!")

    safe_print("\nOptional:")
    safe_print("  - Configure external LLMs (Claude, Gemini, Grok) in Settings")
    safe_print("  - Get FREE API keys - see docs/FREE_API_KEYS_GUIDE.md")
    safe_print("  - Ask Zena: 'How do I configure external LLMs?'")

    safe_print("\n" + "=" * 60)

def main():
    """Main setup flow"""
    try:
        check_python_version()
        install_dependencies()
        download_binaries()
        has_models = setup_model_directory()
        download_model_optional(has_models)
        print_next_steps()

        return 0

    except KeyboardInterrupt:
        safe_print("\n\n[CANCELLED] Setup interrupted by user")
        safe_print("[NOTE] You can run setup.py again anytime")
        return 1
    except Exception as e:
        safe_print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
