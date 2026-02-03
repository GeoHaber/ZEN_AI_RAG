
import sys
import os
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
ZENA_SCRIPT = BASE_DIR / "zena.py"

print(f"Launching {ZENA_SCRIPT}...")

env = os.environ.copy()
env["ZENA_SKIP_PRUNE"] = "1"

try:
    process = subprocess.Popen(
        [sys.executable, str(ZENA_SCRIPT)],
        cwd=str(BASE_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print(f"Process launched with PID {process.pid}")
    
    # Read output for 10 seconds
    start = time.time()
    while time.time() - start < 10:
        ret = process.poll()
        if ret is not None:
            print(f"❌ Process crashed with exit code {ret}!")
            stdout, stderr = process.communicate()
            print("--- STDOUT ---")
            print(stdout)
            print("--- STDERR ---")
            print(stderr)
            sys.exit(1)
        time.sleep(1)
        
    print("✅ Process survived 10 seconds.")
    process.terminate()
    
except Exception as e:
    print(f"❌ Launch failed: {e}")
