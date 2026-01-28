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

# --- Bootstrapping ---
BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from config_system import config, EMOJI
from utils import (
    safe_print, 
    HardwareProfiler, 
    prune_zombies, 
    kill_process_tree, 
    logger,
    DiagnosticRunner
)

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
        if not prune_zombies(auto_confirm=True):
            sys.exit(0)
            
        # 2. System Health Check
        if not await DiagnosticRunner.run_smoke_test():
            safe_print(f"{EMOJI['error']} Critical System Health Check Failed. Attempting to proceed...")
            # Remove interactive block for automated launch

        # 3. Update Engine if needed
        atomic_update_check()
        
        # 3. Tune Hardware
        tune_hardware()
        
        # 4. Launch Backend Engine
        from zena_mode import server
        # We don't call server.start_server() directly here because it's blocking
        # We use the implementation in server.py but start it in a way that allows monitoring
        
        safe_print(f"{EMOJI['loading']} Launching Engine on Port {config.llm_port}...")
        # Note: server.py main() handles the engine subprocess
        # We will hand off control to server.py but ensure we can catch the shutdown
        server.start_server()
        
    except KeyboardInterrupt:
        safe_print(f"\n{EMOJI['info']} Shutdown requested by user.")
    except Exception as e:
        logger.error(f"Orchestrator Fatal Error: {e}", exc_info=True)
        safe_print(f"{EMOJI['error']} FATAL ERROR: {e}")
        time.sleep(5)
        sys.exit(1)
    finally:
        safe_print(f"{EMOJI['info']} Cleaning up processes...")
        # Emergency cleanup if server.py didn't catch it
        sys.exit(0)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
