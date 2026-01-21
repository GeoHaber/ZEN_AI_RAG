
import os
import zipfile
from pathlib import Path

def create_zena_zip():
    base_dir = Path(os.getcwd())
    output_zip = base_dir / "ZenAI_RAG_Source.zip"
    
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
        "model_manager.py",
        "voice_service.py",
        "requirements.txt",
        "zena_master_spec.md",
        "README.md",
        "config.json",
        "download_deps.py",
        "package_zena.py",
        ".gitignore"
    ]
    
    # Directories to include recursively
    include_dirs = [
        "zena_mode",
        "tests"
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
                        if file == "__init__.py" or file.endswith((".py", ".md", ".json")):
                            abs_path = Path(root) / file
                            rel_path = abs_path.relative_to(base_dir)
                            if "__pycache__" not in str(rel_path):
                                print(f"Adding {rel_path}")
                                zipf.write(abs_path, arcname=str(rel_path))
    
    print("Done!")

if __name__ == "__main__":
    create_zena_zip()
