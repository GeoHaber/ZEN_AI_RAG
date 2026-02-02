
import sys
import os
import time

print("DEBUG: Importing zombie_killer...")
try:
    from zombie_killer import prune_zombies
    print("DEBUG: Import successful.")
except Exception as e:
    print(f"DEBUG: Import failed: {e}")
    sys.exit(1)

print("DEBUG: Running prune_zombies(auto_confirm=True)...")
try:
    result = prune_zombies(auto_confirm=True)
    print(f"DEBUG: prune_zombies returned: {result}")
except Exception as e:
    print(f"DEBUG: prune_zombies CRASHED: {e}")
    import traceback
    traceback.print_exc()

print("DEBUG: Importing utils...")
try:
    from utils import kill_zombie_process, kill_process_by_name
    print("DEBUG: Utils imported.")
except Exception as e:
    print(f"DEBUG: Utils import failed: {e}")
    sys.exit(1)

print("DEBUG: Running utils.kill_zombie_process for port 8001...")
try:
    kill_zombie_process(8001, allowed_names=['llama-server.exe', 'python.exe'])
    print("DEBUG: kill_zombie_process finished.")
except Exception as e:
    print(f"DEBUG: kill_zombie_process CRASHED: {e}")
    import traceback
    traceback.print_exc()

print("DEBUG: Cleanup test complete.")
