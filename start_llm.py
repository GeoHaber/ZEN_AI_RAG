"""
start_llm.py - ZenAI Launcher
=============================
This is the main entry point for the ZenAI backend.
It delegates all logic to `zena_mode.server` to avoid circular import issues
and maintain a single source of truth.
"""
import sys
import os
from pathlib import Path

# Ensure the current directory is in sys.path so we can import modules
BASE_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    try:
        from utils import safe_print
    except ImportError:
        print("CRITICAL: 'utils' module not found. Check your PYTHONPATH.")
        safe_print = print

    try:
        safe_print("🚀 Initializing ZenAI Orchestrator...")
        
        # 1. Import the actual implementation
        from zena_mode import server
        
        # 2. Run standard pre-flight (Blocking)
        if not server.validate_environment():
            safe_print("❌ Startup Aborted: Pre-flight validation failed.")
            input("Press Enter to Exit...")
            sys.exit(1)
            
        # 3. Clean up any hanging processes
        from zombie_killer import prune_zombies
        if not prune_zombies(auto_confirm=True):
            safe_print("🚫 Startup Aborted: Port or process conflict could not be resolved.")
            input("Press Enter to Exit...")
            sys.exit(0)
            
        safe_print("✨ Environment is GREEN. Launching Engine...")
        
        # 4. Hand off control to the main server loop
        server.start_server()
        
    except KeyboardInterrupt:
        print("\n👋 ZenAI Shutdown Requested.")
        sys.exit(0)
    except Exception as e:
        import traceback
        error_msg = f"\n❌ FATAL ERROR: {e}\n"
        print(error_msg)
        
        # Log to file for silent crashes
        with open("fatal_crash.txt", "w") as f:
            f.write(error_msg)
            traceback.print_exc(file=f)
            
        traceback.print_exc()
        input("⚠️ Application Crashed. Press Enter to Exit...")
        sys.exit(1)
