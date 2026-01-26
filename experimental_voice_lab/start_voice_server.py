
import subprocess
import sys
import os
import signal
from pathlib import Path

import json

# Config
PORT = 8005
PROJECT_ROOT = Path(__file__).parent.parent
BIN_DIR = PROJECT_ROOT / "bin"
# Load Config
CONFIG_FILE = PROJECT_ROOT / "config.json"
try:
    with open(CONFIG_FILE) as f:
        config = json.load(f)
        MODEL_DIR = Path(config.get("model_dir", "models"))
        BIN_DIR = Path(config.get("bin_dir", "_bin"))
        # Changed to 1.5B for Voice Lab Speed
        DEFAULT_MODEL_NAME = config.get("default_model", "qwen2.5-1.5b-instruct-q4_k_m.gguf")
except Exception as e:
    print(f"⚠️ Config load failed: {e}")
    MODEL_DIR = PROJECT_ROOT / "models"
    BIN_DIR = PROJECT_ROOT / "_bin"
    DEFAULT_MODEL_NAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"

SERVER_EXE = BIN_DIR / "llama-server.exe"

MODEL_PATH = MODEL_DIR / DEFAULT_MODEL_NAME

# Fallback model selection
if not MODEL_PATH.exists():
    if MODEL_DIR.exists():
        candidates = list(MODEL_DIR.glob("*.gguf"))
        if candidates:
            MODEL_PATH = max(candidates, key=lambda x: x.stat().st_size)
            print(f"⚠️ Default model not found, using: {MODEL_PATH.name}")
        else:
            print(f"❌ No models found in {MODEL_DIR}")
            sys.exit(1)
    else:
         print(f"❌ Model directory not found: {MODEL_DIR}")
         sys.exit(1)

def detect_amd_gpu():
    """Simple check for AMD GPU presence on Windows."""
    try:
        # Check WMI for Video Controller
        result = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get", "Name"], 
            capture_output=True, text=True
        )
        if "AMD" in result.stdout or "Radeon" in result.stdout:
            print("✨ AMD GPU Detected! Enabling GPU Offload.")
            return True
    except Exception as e:
        print(f"⚠️ GPU Check failed: {e}")
    return False

def main():
    if not SERVER_EXE.exists():
        print(f"❌ Server binary not found: {SERVER_EXE}")
        sys.exit(1)

    has_amd = detect_amd_gpu()
    gpu_layers = "999" if has_amd else "0" # 999 = Offload Everything

    cmd = [
        str(SERVER_EXE),
        "--model", str(MODEL_PATH),
        "--port", str(PORT),
        "--ctx-size", "2048",
        "-np", "4",
        "--n-gpu-layers", gpu_layers 
    ]
    
    print(f"🚀 VOICE LAB: Starting Lightweight Server on Port {PORT}")
    print(f"📂 Model: {MODEL_PATH.name}")
    print(f"⚡ GPU Layers: {gpu_layers} (AMD Detected: {has_amd})")
    
    # Launch
    p = subprocess.Popen(cmd, cwd=BIN_DIR)
    
    try:
        p.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping Server...")
        p.terminate()

if __name__ == "__main__":
    main()
