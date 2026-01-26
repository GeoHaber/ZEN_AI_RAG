"""
verify_environment.py - ZenAI Environment Health Auditor
=======================================================
Run this script to identify "ghosts" and environmental conflicts.
"""
import os
import sys
import platform
import psutil
import socket
from pathlib import Path
import json

# Add parent to path
BASE_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(BASE_DIR))

try:
    from utils import HardwareProfiler, is_port_active, safe_print
    from config import MODEL_DIR, BIN_DIR, PORTS
except ImportError:
    # Fallback if imports fail
    def safe_print(*args, **kwargs):
        kwargs['flush'] = True
        print(*args, **kwargs)
    HardwareProfiler = None
    MODEL_DIR = BASE_DIR / "Models"
    BIN_DIR = BASE_DIR / "BIN"
    PORTS = {"ENGINE": 8001}

def get_cpu_caps():
    try:
        import cpuinfo
        info = cpuinfo.get_cpu_info()
        flags = info.get('flags', [])
        found = []
        for cap in ['avx', 'avx2', 'avx512f', 'fma', 'sse3', 'msse3', 'neon']:
            if cap in flags: found.append(cap.upper())
        return found
    except Exception:
        return ["Unknown"]

def main():
    safe_print("\n" + "="*60)
    safe_print("ZENAI ENVIRONMENT AUDIT REPORT")
    safe_print("="*60)

    # 1. Location & Python
    safe_print(f"\n[1] PLATFORM & LOCATION")
    safe_print(f"    - OS:       {platform.system()} {platform.release()}")
    safe_print(f"    - Python:   {sys.version.split()[0]} ({sys.executable})")
    safe_print(f"    - Root:     {BASE_DIR}")
    safe_print(f"    - Script:   {Path(__file__).absolute()}")

    # 2. Hardware Capabilities
    safe_print(f"\n[2] HARDWARE CAPABILITIES")
    if HardwareProfiler:
        prof = HardwareProfiler.get_profile()
        safe_print(f"    - CPU:      {prof['cpu']}")
        safe_print(f"    - Caps:     {', '.join(get_cpu_caps())}")
        safe_print(f"    - RAM:      {prof['ram_gb']}GB Total")
        if prof['type'] != "CPU":
             safe_print(f"    - GPU:      {prof['type']} ({prof['vram_mb']}MB VRAM)")
    else:
        safe_print("    - Profiler: Unavailable")

    # 3. Storage & Workspace
    safe_print(f"\n[3] STORAGE & WORKSPACE")
    try:
        usage = psutil.disk_usage(str(BASE_DIR))
        safe_print(f"    - Free:     {usage.free // (1024**3)}GB on {BASE_DIR.drive}")
        safe_print(f"    - ModelDir: {'OK (' + str(len(list(MODEL_DIR.glob('*.gguf')))) + ' models)' if MODEL_DIR.exists() else 'MISSING'}")
        safe_print(f"    - BinDir:   {'OK' if BIN_DIR.exists() else 'MISSING'}")
    except Exception as e:
        safe_print(f"    - Error:    {e}")

    # 4. Networking & Ports
    safe_print(f"\n[4] NETWORK & INTERFACES")
    target_port = PORTS.get("ENGINE", 8001)
    # Use a simpler check if utils failed
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    result = sock.connect_ex(('127.0.0.1', target_port))
    sock.close()
    
    port_status = "BUSY (Conflict!)" if result == 0 else "FREE (Ready)"
    safe_print(f"    - Port {target_port}:  {port_status}")
    
    # 5. Background Interference (The "Ghost" Finder)
    safe_print(f"\n[5] BACKGROUND INTERFERENCE")
    conflicts = []
    others = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            name = proc.info['name'].lower()
            if 'llama' in name or 'ollama' in name or 'local_ai' in name:
                conflicts.append(f"{proc.info['name']} (PID: {proc.pid})")
            elif 'python' in name and proc.pid != os.getpid():
                others.append(f"Python (PID: {proc.pid})")
        except: continue
        
    if conflicts: safe_print(f"    - CONFLICTS: {', '.join(conflicts)}")
    else: safe_print("    - CONFLICTS: None")
    
    if others: safe_print(f"    - OTHER PY:  {', '.join(others[:3])}{'...' if len(others)>3 else ''}")

    safe_print("\n" + "="*60)
    safe_print("AUDIT COMPLETE")
    safe_print("="*60 + "\n")

if __name__ == "__main__":
    main()
