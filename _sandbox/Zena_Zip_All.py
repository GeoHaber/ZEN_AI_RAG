import os
import zipfile
from pathlib import Path
try:
    import dependency_manager
except ImportError:
    dependency_manager = None

import datetime

def create_zena_zip():
    base_dir = Path(os.getcwd())
    
    # Auto-generate requirements before packing
    if dependency_manager:
        print("🔄 Updating requirements.txt...")
        dependency_manager.generate_requirements(base_dir)
    
    # Date-stamped filename
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    output_zip = base_dir / f"ZenAI_RAG_Source_{date_str}.zip"
    
    # Files to explicitly include
    include_files = [
        "zena.py",
        "start_llm.py",
        "async_backend.py",
        "config.py",
        "config_system.py",
        "security.py",
        "state_management.py",
        "decorators.py",
        "utils.py",
        "ui_components.py",
        "ui_state.py",
        "model_manager.py",
        "voice_service.py",
        "requirements.txt",
        "zena_master_spec.md",
        "README.md",
        "USER_MANUAL.md",
        "ARCHITECTURE_V2.md",
        "walkthrough.md",
        "config.json",
        "download_deps.py",
        "dependency_manager.py",
        "Zena_Zip_All.py", # Self-reference updated
        "model_router.py",
        "settings.py",
        "settings.json",
        ".gitignore"
    ]
    
    # Directories to include recursively
    include_dirs = [
        "zena_mode",
        "tests",
        "locales",
        "ui",
        "_bin"
    ]
    
    print(f"Creating {output_zip}...")
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add individual files
        for filename in include_files:
            file_path = base_dir / filename
            if file_path.exists():
                print(f"Adding {filename}")
                zipf.write(file_path, arcname=filename)
            else:
                print(f"Warning: {filename} not found!")

        # Add directories
        for dirname in include_dirs:
            dir_path = base_dir / dirname
            if dir_path.exists():
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        # Modified filter: Include .exe and .dll for _bin folder
                        is_bin = "_bin" in str(Path(root))
                        if file == "__init__.py" or file.endswith((".py", ".md", ".json")) or (is_bin and file.endswith((".exe", ".dll"))):
                            abs_path = Path(root) / file
                            rel_path = abs_path.relative_to(base_dir)
                            if "__pycache__" not in str(rel_path):
                                print(f"Adding {rel_path}")
                                zipf.write(abs_path, arcname=str(rel_path))
    
    print("Done!")

if __name__ == "__main__":
    create_zena_zip()
