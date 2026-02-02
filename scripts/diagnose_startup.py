
import sys
import os
import time
from pathlib import Path

# Setup trace log
TRACE_FILE = Path("startup_trace.log")

def log(msg):
    timestamp = time.strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(TRACE_FILE, "a", encoding='utf-8') as f:
            f.write(line + "\n")
    except:
        pass

if __name__ == "__main__":
    if TRACE_FILE.exists():
        try: os.remove(TRACE_FILE)
        except: pass
        
    log("🚀 DIAGNOSTIC STARTUP INITIATED")
    log(f"Current Directory: {os.getcwd()}")
    log(f"Python: {sys.executable}")
    
    BASE_DIR = Path(__file__).parent.parent.absolute()
    log(f"Adding to sys.path: {BASE_DIR}")
    sys.path.insert(0, str(BASE_DIR))
    
    try:
        log("Importing utils...")
        from utils import safe_print
        log("Utils imported successfully.")
    except Exception as e:
        log(f"❌ Failed to import utils: {e}")
        sys.exit(1)

    try:
        log("Importing zena_mode.server...")
        from zena_mode import server
        log("Server module imported.")
        
        log("Running server.validate_environment()...")
        if not server.validate_environment():
            log("❌ validate_environment() FAILED")
            sys.exit(1)
        log("✅ validate_environment() PASSED")
        
        log("Importing zombie_killer...")
        from zombie_killer import prune_zombies
        log("zombie_killer imported.")
        
        log("Running prune_zombies(auto_confirm=True)...")
        # Capture stdout/stderr of prune_zombies?
        res = prune_zombies(auto_confirm=True)
        log(f"prune_zombies returned: {res}")
        
        if not res:
            log("❌ prune_zombies returned False (Abort)")
            sys.exit(0)
            
        log("✅ Zombies pruned/checked.")
        
        log("Calling server.start_server()...")
        server.start_server()
        log("❌ server.start_server() returned! (Should be infinite loop)")
        
    except KeyboardInterrupt:
        log("👋 KeyboardInterrupt caught.")
    except BaseException as e:
        log(f"🔥 CRASH CAUGHT: {type(e).__name__}: {e}")
        import traceback
        with open(TRACE_FILE, "a") as f:
            traceback.print_exc(file=f)
    
    log("Diagnostic finished.")
    input("Press Enter to close diagnostic...")
