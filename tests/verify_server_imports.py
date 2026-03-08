import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))


def test_import(module_name):
    """Test import."""
    try:
        # [X-Ray auto-fix] print(f"Testing import: {module_name}...", end="", flush=True)
        __import__(module_name)
        print(" OK")
        return True
    except Exception:
        # [X-Ray auto-fix] print(f" FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


print("\n--- ZenAI Deep Import Verification ---\n")

modules = [
    "config_system",
    "utils",
    "nicegui",
    "zena_mode.server",
    "model_manager",
    "voice_service",
    "async_backend",
    "security",
]

all_ok = True
for m in modules:
    if not test_import(m):
        all_ok = False

if all_ok:
    print("\n✅ All core modules import successfully.")
else:
    print("\n❌ some imports FAILED. Check the errors above.")
