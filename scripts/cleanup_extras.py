import os
import shutil
from pathlib import Path


def _do_cleanup_project_setup():
    """Helper: setup phase for cleanup_project."""

    print("🧹 Starting Project Cleanup...")

    ROOT = Path(os.getcwd())
    EXTRA_DIR = ROOT / "_Extra_files"
    EXTRA_DIR.mkdir(exist_ok=True)

    # Files/Dirs that MUST stay in root
    KEEPERS = {
        # Core App
        "zena.py",
        "config.json",
        "config.py",
        "utils.py",
        "config_system.py",
        "security.py",
        "async_backend.py",
        "ui_components.py",
        "settings.py",
        "state_management.py",
        "locales",
        "ui",
        "zena_mode",
        "models",
        # Documentation
        "README.md",
        "USER_MANUAL.md",
        "INSTALL.md",
        "requirements.txt",
        # System / Hidden
        ".git",
        ".venv",
        ".pytest_cache",
        "__pycache__",
        ".gitignore",
        ".coverage",
        # Data / Storage
        "dist",
        "rag_cache",
        "qdrant_storage",
        "conversation_cache",
        "benchmarks",  # If exists
        # Dev Tools needed for validation
        "tests",
        "scripts",
        "run_tests.py",
        "pytest.ini",
        # This script itself (will be in scripts/ but just in case)
        "cleanup_extras.py",
        "experimental_voice_lab",
        # Target
        "_Extra_files",
    }
    return EXTRA_DIR, KEEPERS, ROOT


def cleanup_project():
    """Cleanup project."""
    EXTRA_DIR, KEEPERS, ROOT = _do_cleanup_project_setup()

    moved_count = 0

    for item in ROOT.iterdir():
        name = item.name

        if name in KEEPERS:
            # [X-Ray auto-fix] print(f"  Existing: {name} (Keep)")
            continue

        # [X-Ray auto-fix] print(f"  ➡️ Moving: {name} -> _Extra_files/")
        dest = EXTRA_DIR / name
        try:
            shutil.move(str(item), str(dest))
            moved_count += 1
        except Exception:
            # [X-Ray auto-fix] print(f"  ❌ Failed to move {name}: {e}")
            pass
    # [X-Ray auto-fix] print(f"\n✅ Cleanup Complete. Moved {moved_count} items to _Extra_files/.")


if __name__ == "__main__":
    cleanup_project()
