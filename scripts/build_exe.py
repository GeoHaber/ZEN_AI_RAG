
import PyInstaller.__main__
import os
import shutil
from pathlib import Path

# Configuration
APP_NAME = "ZenAI"
ENTRY_POINT = "start_llm.py"
ICON_PATH = "ui/static/favicon.ico" # Adjust if you have a specific icon
DIST_DIR = "dist"
WORK_DIR = "build"

def clean_build_dirs():
    """Wipe previous build artifacts."""
    if os.path.exists(DIST_DIR): shutil.rmtree(DIST_DIR)
    if os.path.exists(WORK_DIR): shutil.rmtree(WORK_DIR)

def build():
    clean_build_dirs()
    
    # Define imports to force include
    hidden_imports = [
        "nicegui",
        "uvicorn",
        "fastapi",
        "starlette",
        "pypdf",
        "sentence_transformers",
        "numpy",
        "requests",
        "zena_mode",
        "ui",
        # Add any other dynamic imports here
    ]
    
    # Construct PyInstaller arguments
    args = [
        ENTRY_POINT,
        f"--name={APP_NAME}",
        "--onedir",  # Directory mode (External Binaries)
        "--windowed", # No console window (optional, maybe keep console for beta?)
        # Let's keep console for now based on "stability" - easier to debug
        "--console", 
        "--clean",
        "--noconfirm",
    ]
    
    # Add hidden imports
    for hidden in hidden_imports:
        args.append(f"--hidden-import={hidden}")
        
    # Add Data (NiceGUI Assets)
    # NiceGUI needs its static and template files
    import nicegui
    nicegui_path = Path(nicegui.__file__).parent
    args.append(f"--add-data={nicegui_path}{os.pathsep}nicegui")
    
    # Add UI folder
    args.append(f"--add-data=ui{os.pathsep}ui")
    
    # Add Zena Mode
    args.append(f"--add-data=zena_mode{os.pathsep}zena_mode")

    # Run PyInstaller
    print("🔨 Starting PyInstaller Build...")
    PyInstaller.__main__.run(args)
    
    print("✅ Build Complete.")
    
    # Post-Build: Copy External Binaries
    print("📦 Copying External Assets...")
    target_dir = Path(DIST_DIR) / APP_NAME
    
    # 1. _bin folder (Atomic Updates)
    src_bin = Path("_bin")
    if src_bin.exists():
        shutil.copytree(src_bin, target_dir / "_bin", dirs_exist_ok=True)
        print("   + Copied _bin/")
        
    # 2. Config & Env
    if Path("config.json").exists():
        shutil.copy("config.json", target_dir)
        print("   + Copied config.json")
        
    if Path(".env").exists():
        shutil.copy(".env", target_dir)
        print("   + Copied .env")

    print(f"🚀 Release ready at: {target_dir.absolute()}")

if __name__ == "__main__":
    build()
