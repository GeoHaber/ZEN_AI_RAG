
import os
import zipfile
from pathlib import Path

def create_zena_zip():
    base_dir = Path(os.getcwd())
    output_zip = base_dir / "ZenAI_RAG_Complete.zip"

    # Core application files
    include_files = [
        # Main application
        "zena.py",
        "start_llm.py",

        # Backend & LLM
        "async_backend.py",
        "model_manager.py",
        "swarm_arbitrator.py",

        # Configuration
        "config.py",
        "config_system.py",
        "settings.py",

        # Core utilities
        "security.py",
        "state_management.py",
        "decorators.py",
        "utils.py",

        # UI
        "ui_components.py",

        # Features
        "voice_service.py",
        "feature_detection.py",
        "setup_manager.py",
        "cleanup_policy.py",
        "benchmark.py",

        # Setup & deployment
        "setup.py",           # NEW: One-time setup wizard
        "requirements.txt",
        "download_deps.py",
        "package_zena.py",
        "run_tests.py",

        # Config files
        "config.json",
        ".gitignore",

        # Documentation
        "README.md",
        "zena_master_spec.md",
        "QUICK_START.md",
        "HOW_TO_RUN.md"
    ]

    # Directories to include recursively
    include_dirs = [
        "zena_mode",       # RAG, scraper, arbitrage
        "tests",           # All test files
        "ui",              # UI components (settings dialog, etc.)
        "docs",            # User documentation for RAG indexing
        "locales"          # Internationalization (if exists)
    ]
    
    print(f"Creating {output_zip}...")
    print("=" * 60)

    file_count = 0
    dir_count = 0

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add individual files
        print("\n[FILES] Adding core files...")
        for filename in include_files:
            file_path = base_dir / filename
            if file_path.exists():
                print(f"  [OK] {filename}")
                zipf.write(file_path, arcname=filename)
                file_count += 1
            else:
                print(f"  [WARN] {filename} not found (skipping)")

        # Add directories
        print("\n[DIRS] Adding directories...")
        for dirname in include_dirs:
            dir_path = base_dir / dirname
            if dir_path.exists():
                print(f"\n  [DIR] {dirname}/")
                dir_count += 1
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        # Include Python files, markdown docs, JSON config
                        if file == "__init__.py" or file.endswith((".py", ".md", ".json", ".txt")):
                            abs_path = Path(root) / file
                            rel_path = abs_path.relative_to(base_dir)
                            # Skip __pycache__ and .pyc files
                            if "__pycache__" not in str(rel_path) and not file.endswith(".pyc"):
                                print(f"    [OK] {rel_path}")
                                zipf.write(abs_path, arcname=str(rel_path))
                                file_count += 1
            else:
                print(f"  [WARN] {dirname}/ not found (skipping)")

    print("\n" + "=" * 60)
    print(f"[SUCCESS] Package created: {output_zip}")
    print(f"[STATS] Statistics:")
    print(f"   - Files: {file_count}")
    print(f"   - Directories: {dir_count}")

    # Get file size
    size_bytes = output_zip.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    print(f"   - Size: {size_mb:.2f} MB ({size_bytes:,} bytes)")
    print("=" * 60)
    print("\n[DONE] Ready for distribution!")

if __name__ == "__main__":
    create_zena_zip()
