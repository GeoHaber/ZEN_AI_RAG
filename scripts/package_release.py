
import os
import zipfile
import shutil
from pathlib import Path

def create_dist_zip():
    print("📦 Packing ZenAI for Release...")
    
    # Define root
    ROOT_DIR = Path(os.getcwd())
    DIST_DIR = ROOT_DIR / "dist"
    DIST_DIR.mkdir(exist_ok=True)
    
    ZIP_NAME = DIST_DIR / "ZenAI_Dist.zip"
    
    # Define what to include
    INCLUDES = [
        "zena.py",
        "requirements.txt",
        "README.md",
        "USER_MANUAL.md",
        "config.json",
        "config.py",
        "utils.py",
        "config_system.py",
        "security.py",
        "async_backend.py",
        "locales",         # Folder
        "ui",              # Folder
        "zena_mode",       # Folder
        "ui_components.py",
        "settings.py",
        "state_management.py",
        "zena_startup.log", # Maybe not needed but okay
        "experimental_voice_lab", # Folder
        "tests"            # Include tests for verification
    ]
    
    # Create Zip
    with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in INCLUDES:
            src_path = ROOT_DIR / item
            
            if not src_path.exists():
                print(f"⚠️ Warning: {item} not found, skipping.")
                continue
                
            if src_path.is_file():
                print(f"  Adding file: {item}")
                zipf.write(src_path, arcname=item)
                
            elif src_path.is_dir():
                print(f"  Adding dir:  {item}")
                for root, dirs, files in os.walk(src_path):
                    # Filter out garbage
                    if "__pycache__" in root: continue
                    if ".venv" in root: continue
                    if ".git" in root: continue
                    if "node_modules" in root: continue
                    
                    for file in files:
                        if file.endswith(".pyc"): continue
                        
                        full_path = Path(root) / file
                        rel_path = full_path.relative_to(ROOT_DIR)
                        zipf.write(full_path, arcname=str(rel_path))

    print(f"\n✅ Release created at: {ZIP_NAME}")
    print(f"📦 Size: {ZIP_NAME.stat().st_size / 1024 / 1024:.2f} MB")
    
    return ZIP_NAME

if __name__ == "__main__":
    create_dist_zip()
