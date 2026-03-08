# -*- coding: utf-8 -*-
# This is a new section for auto-install and self-check logic

import subprocess
import sys
import os


def check_and_install_requirements(requirements_path):
    """Ensure all requirements are installed before app startup."""
    try:
        # Check if pip is available
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True, stdout=subprocess.DEVNULL, shell=False)
    except Exception:
        print("❌ FATAL: pip not found. Please install pip.")
        sys.exit(1)

    # [X-Ray auto-fix] print(f"🔍 Checking and installing dependencies from {requirements_path}...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_path], check=True, shell=False)
        print("✅ Dependencies are up to date.")
    except subprocess.CalledProcessError:
        print("❌ FATAL: Failed to install dependencies from requirements.txt.")
        sys.exit(1)


# Find requirements.txt (prefer _sandbox/requirements.txt)
def find_requirements_file():
    """Find requirements file."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "requirements.txt"),
        os.path.join(os.path.dirname(__file__), "_sandbox", "requirements.txt"),
        os.path.join(os.path.dirname(__file__), "_legacy_audit", "requirements.txt"),
        os.path.join(os.path.dirname(__file__), "docs", "requirements.txt"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    print("❌ FATAL: requirements.txt not found.")
    sys.exit(1)


# Run self-check before app startup
from zena_mode.resource_detect import HardwareProfiler

profile = HardwareProfiler.get_profile()
print(
    f"[Hardware] Detected: {profile['type']} | RAM: {profile['ram_gb']}GB | VRAM: {profile['vram_mb']}MB | Threads: {profile['threads']}"
)

# Select requirements file or patch requirements for hardware
requirements_path = find_requirements_file()


# Patch requirements for GPU/CPU-specific libraries
def patch_requirements_for_hardware(req_path, hw_type):
    """Patch requirements for hardware."""
    with open(req_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    patched = []
    for line in lines:
        pkg = line.strip().lower()
        # Remove irrelevant GPU/NPU packages
        if hw_type == "AMD":
            if "cuda" in pkg or "nvidia" in pkg:
                continue
        elif hw_type == "NVIDIA":
            if "rocm" in pkg or "amd" in pkg:
                continue
        elif hw_type == "CPU":
            if "cuda" in pkg or "nvidia" in pkg or "rocm" in pkg or "amd" in pkg or "directml" in pkg:
                continue
        patched.append(line)

    # Add best acceleration library for detected hardware
    accel_libs = []
    if hw_type == "NVIDIA":
        accel_libs = ["onnxruntime-gpu", "torch", "torchvision", "torchaudio"]
    elif hw_type == "AMD":
        # onnxruntime-rocm is Linux-only; on Windows use directml (added below)
        if sys.platform == "win32":
            accel_libs = ["onnxruntime", "torch", "torchvision", "torchaudio"]
        else:
            accel_libs = ["onnxruntime-rocm", "torch", "torchvision", "torchaudio"]
    elif hw_type == "CPU":
        accel_libs = ["onnxruntime", "torch", "torchvision", "torchaudio"]
    # DirectML: Windows, any GPU/NPU
    if sys.platform == "win32" and hw_type in ["NVIDIA", "AMD", "CPU"]:
        accel_libs.append("onnxruntime-directml")

    # Avoid duplicates
    patched_pkgs = set([l.strip().lower() for l in patched if l.strip() and not l.strip().startswith("#")])
    for lib in accel_libs:
        if lib not in patched_pkgs:
            patched.append(lib + "\n")

    # Write patched requirements to a temp file
    patched_path = req_path + ".patched"
    with open(patched_path, "w", encoding="utf-8") as f:
        f.writelines(patched)
    return patched_path


patched_requirements = patch_requirements_for_hardware(requirements_path, profile["type"])
check_and_install_requirements(patched_requirements)
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
# import os
# import sys
import time

# import subprocess
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
    """Catch import errors."""
    try:
        from config_system import config, EMOJI
        from utils import safe_print, HardwareProfiler, prune_zombies, kill_process_tree, logger, DiagnosticRunner

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

            with open(_CRASH_LOG, "w", encoding="utf-8") as f:
                f.write(f"[IMPORT ERROR] {e}\n{traceback.format_exc()}")
        sys.exit(1)


config, EMOJI, safe_print, HardwareProfiler, prune_zombies, kill_process_tree, logger, DiagnosticRunner = (
    catch_import_errors()
)

# --- DEBUGGING: Add File Logging (Safeguarded) ---
try:
    file_handler = logging.FileHandler(BASE_DIR / "startup_debug.log", mode="w", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
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
                if bak_path.exists():
                    os.remove(bak_path)
                os.rename(exe_path, bak_path)
            os.rename(new_path, exe_path)
            safe_print(f"{EMOJI['success']} Engine updated successfully.")
        except Exception as e:
            safe_print(f"{EMOJI['error']} Atomic update failed: {e}")
            # Recovery: if we renamed to bak but new failed, swap back
            if not exe_path.exists() and bak_path.exists():
                os.rename(bak_path, exe_path)


# Hardware tuning moved to zena_mode.heart_and_brain.ZenHeart


async def main():
    """Main."""
    try:
        safe_print(f"\n{EMOJI['sparkles']} ZenAI v3.1 Orchestrator Starting...\n")

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

        # 4. Tune Hardware (Handled by ZenHeart)

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
            # Keep the window open if running in a standalone terminal
            if sys.stdin and sys.stdin.isatty():
                try:
                    input("Press Enter to exit...")
                except (EOFError, KeyboardInterrupt):
                    pass
            else:
                # If no terminal (e.g. background process), just log and exit
                logger.info("Non-interactive mode detected, exiting.")
        sys.exit(se.code)
    except Exception as e:
        logger.error(f"Orchestrator Fatal Error: {e}", exc_info=True)
        safe_print(f"\n{'!' * 30}")
        safe_print(f"{EMOJI['error']} FATAL ERROR: {e}")
        safe_print(f"{'!' * 30}")
        time.sleep(5)
        try:
            input("\nPress Enter to exit and see full diagnostic logs...")
        except (EOFError, KeyboardInterrupt):
            pass  # No stdin available
        sys.exit(1)
    finally:
        safe_print(f"{EMOJI['info']} Cleaning up processes...")


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()

    import asyncio

    try:
        asyncio.run(main())
    except BaseException as e:
        if not isinstance(e, (KeyboardInterrupt, SystemExit)):
            # Write crash info to file for debugging "Open with Python" issues
            import traceback

            error_msg = f"[CRASH] {type(e).__name__}: {e}\n{traceback.format_exc()}"
            try:
                with open(_CRASH_LOG, "w", encoding="utf-8") as f:
                    f.write(error_msg)
            except (OSError, IOError):
                pass  # Can't write crash log
            print(f"\n[!] Unexpected Global Error: {e}")
            traceback.print_exc()
            try:
                input("\nPress Enter to close...")
            except (EOFError, KeyboardInterrupt):
                pass  # No stdin
        sys.exit(0)
