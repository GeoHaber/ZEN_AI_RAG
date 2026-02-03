
import sys
import os
import subprocess
import time
from pathlib import Path

# Setup logging
log_file = Path("startup_diag.txt")
def log(msg):
    print(msg)
    with open(log_file, "a", encoding='utf-8') as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")

log("=== DIAGNOSTIC START ===")
log(f"CWD: {os.getcwd()}")
log(f"Python: {sys.executable}")

# Check Imports
try:
    import config_system
    log("✅ config_system imported")
    log(f"Config LLM Port: {config_system.config.llm_port}")
    log(f"Config Context Size: {config_system.config.context_size}")
    log(f"Config Bin Dir: {config_system.config.bin_dir}")
except Exception as e:
    log(f"❌ config_system failed: {e}")
    import traceback
    log(traceback.format_exc())

# Check Binaries
try:
    bin_dir = Path(config_system.config.bin_dir)
    server_exe = bin_dir / "llama-server.exe"
    if server_exe.exists():
        log(f"✅ Server binary found: {server_exe}")
    else:
        log(f"❌ Server binary MISSING: {server_exe}")
except Exception as e:
    log(f"❌ Binary check error: {e}")

# Check Dependencies
try:
    import psutil
    log("✅ psutil available")
except ImportError:
    log("⚠️ psutil MISSING")

try:
    import nicegui
    log("✅ nicegui available")
except ImportError:
    log("❌ nicegui MISSING")

# Try Launching Server Check
log("Testing LLM Server Launch (Dry Run)...")
try:
    cmd = [str(server_exe), "--help"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    if p.returncode == 0:
        log("✅ LLM Server binary works (Help output received)")
    else:
        log(f"❌ LLM Server binary failed with code {p.returncode}")
        log(f"Error: {p.stderr[:200]}")
except Exception as e:
    log(f"❌ LLM Server launch exception: {e}")

log("=== DIAGNOSTIC END ===")
