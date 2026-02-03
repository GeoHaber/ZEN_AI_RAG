# -*- coding: utf-8 -*-
"""
start_llm.py - ZenAI Orchestrator
=================================
The master control script for ZenAI. Responsibilities:
1. Hardware Profiling & Tuning
2. Atomic Binary Updates
3. Zombie Process Pruning
4. Process Lifecycle Management (Engine + UI)

Strictly follows zena_master_spec.md v3.1.
"""
import os
import sys
import time
import subprocess
import logging
from pathlib import Path

# --- EARLY CRASH CAPTURE (for Windows Explorer "Open with Python") ---
# This captures ANY crash that happens before normal logging is set up.
_SCRIPT_DIR = Path(__file__).parent.resolve()
_CRASH_LOG = _SCRIPT_DIR / "crash_log.txt"

# --- Bootstrapping ---
# CRITICAL: Set working directory to script folder BEFORE any other imports
# This fixes "Open with Python" from Windows 11 File Explorer.
os.chdir(_SCRIPT_DIR)
sys.path.insert(0, str(_SCRIPT_DIR))
BASE_DIR = _SCRIPT_DIR

# --- IMMEDIATE BREADCRUMBS (DIAGNOSTIC) ---
sys.stdout.write("[BOOT] Script starting...\n")
sys.stdout.flush()


def catch_import_errors():
    try:
        from config_system import config, EMOJI
        from utils import (
            safe_print,
            HardwareProfiler,
            prune_zombies,
            kill_process_tree,
            logger,
            DiagnosticRunner
        )
        return config, EMOJI, safe_print, HardwareProfiler, prune_zombies, kill_process_tree, logger, DiagnosticRunner
    except Exception as e:
        # Use try/except for print() as there may be no console in Windows Explorer launches
        try:
            print(f"\n[!] CRITICAL IMPORT ERROR: {e}")
            print("This usually means a dependency is missing or there is a path issue.")
            import traceback
            traceback.print_exc()
            input("\nPress Enter to exit...")
        except OSError:
            # No console attached - write to crash log instead
            import traceback
            with open(_CRASH_LOG, 'w', encoding='utf-8') as f:
                f.write(f"[IMPORT ERROR] {e}\n{traceback.format_exc()}")
        sys.exit(1)

config, EMOJI, safe_print, HardwareProfiler, prune_zombies, kill_process_tree, logger, DiagnosticRunner = catch_import_errors()

# --- DEBUGGING: Add File Logging (Safeguarded) ---
try:
    file_handler = logging.FileHandler(BASE_DIR / "startup_debug.log", mode='w', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)
except Exception as ie:
    try:
        print(f"[!] Warning: Could not set up file logging: {ie}")
    except OSError:
        pass  # No console attached, skip


def atomic_update_check():
    """Checks for _bin/llama-server.exe.new and performs atomic swap."""
    exe_path = config.BIN_DIR / "llama-server.exe"
    new_path = config.BIN_DIR / "llama-server.exe.new"
    bak_path = config.BIN_DIR / "llama-server.exe.bak"
    
    if new_path.exists():
        safe_print(f"{EMOJI['loading']} Found engine update! Performing atomic swap...")
        try:
            if exe_path.exists():
                if bak_path.exists(): os.remove(bak_path)
                os.rename(exe_path, bak_path)
            os.rename(new_path, exe_path)
            safe_print(f"{EMOJI['success']} Engine updated successfully.")
        except Exception as e:
            safe_print(f"{EMOJI['error']} Atomic update failed: {e}")
            # Recovery: if we renamed to bak but new failed, swap back
            if not exe_path.exists() and bak_path.exists():
                os.rename(bak_path, exe_path)

def tune_hardware():
    """Profiles hardware and sets optimal engine parameters."""
    safe_print(f"{EMOJI['search']} Profiling hardware for optimal performance...")
    profile = HardwareProfiler.get_profile()
    
    # Logic: 4 threads min, Cores-2 if plentiful. 
    # Nitro Mode: Increase batch if AVX2/AVX512 (handled by llama-server natively, but we logs it)
    config.threads = max(4, profile['threads'] - 2)
    
    # GPU Offloading
    if profile['type'] == "NVIDIA":
        config.gpu_layers = 33 # Full offload for 7B on most modern cards
        safe_print(f"{EMOJI['robot']} NVIDIA GPU Detected. Enabling hardware acceleration.")
    elif profile['type'] == "AMD":
        config.gpu_layers = 1 # Minimal offload for stability
        safe_print(f"{EMOJI['robot']} AMD GPU Detected. Using Vulkan/ROCm fallback.")
    else:
        config.gpu_layers = 0
        safe_print(f"{EMOJI['robot']} CPU-only mode. Threads optimized to {config.threads}.")

async def main():
    try:
        safe_print(f"\n{EMOJI['sparkles']} ZenAI v3.1 Orchestrator Starting...")
        
        # 1. Clean up "Zombies"
        try:
            if not prune_zombies(auto_confirm=True):
                safe_print(f"{EMOJI['info']} Startup cancelled by user.")
                return
        except Exception as e:
            logger.warning(f"Zombie pruning failed: {e}")

        # 2. System Health Check
        if not await DiagnosticRunner.run_smoke_test():
            safe_print(f"{EMOJI['warning']} Critical System Health Check Failed. Attempting to proceed...")

        # 3. Update Engine if needed
        atomic_update_check()
        
        # 4. Tune Hardware
        tune_hardware()
        
        # 5. Launch Backend Engine
        from zena_mode import server
        safe_print(f"{EMOJI['loading']} Launching Engine on Port {config.llm_port}...")
        
        # This call is blocking and enters the main loop
        server.start_server()
        
    except KeyboardInterrupt:
        safe_print(f"\n{EMOJI['info']} Shutdown requested by user.")
    except SystemExit as se:
        if se.code != 0:
            safe_print(f"{EMOJI['error']} System Exit with code {se.code}")
            time.sleep(5)
            input("Press Enter to exit...")
        sys.exit(se.code)
    except Exception as e:
        logger.error(f"Orchestrator Fatal Error: {e}", exc_info=True)
        safe_print(f"\n{'!'*30}")
        safe_print(f"{EMOJI['error']} FATAL ERROR: {e}")
        safe_print(f"{'!'*30}")
        time.sleep(5)
        try:
            input("\nPress Enter to exit and see full diagnostic logs...")
        except (EOFError, KeyboardInterrupt): pass  # No stdin available
        sys.exit(1)
    finally:
        safe_print(f"{EMOJI['info']} Cleaning up processes...")

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except BaseException as e:
        if not isinstance(e, (KeyboardInterrupt, SystemExit)):
            # Write crash info to file for debugging "Open with Python" issues
            import traceback
            error_msg = f"[CRASH] {type(e).__name__}: {e}\n{traceback.format_exc()}"
            try:
                with open(_CRASH_LOG, 'w', encoding='utf-8') as f:
                    f.write(error_msg)
            except (OSError, IOError):
                pass  # Can't write crash log
            print(f"\n[!] Unexpected Global Error: {e}")
            traceback.print_exc()
            try: input("\nPress Enter to close...")
            except (EOFError, KeyboardInterrupt): pass  # No stdin
        sys.exit(0)
