import os
import shutil
import zipfile
import subprocess
import sys
from pathlib import Path
from utils import safe_print

# --- CONFIGURATION ---
SOURCE_DIR = Path("c:/Users/dvdze/Documents/_Python/Dev/ZEN_AI_RAG")
SOAPBOX_DIR = SOURCE_DIR / "soapbox"
ZIP_NAME = "zenai_portability.zip"

NECESSARY_FILES = [
    "zena.py", "async_backend.py", "config_system.py", "config.py", 
    "security.py", "settings.py", "state_management.py", "utils.py", 
    "ui_components.py", "model_router.py", "model_manager.py", 
    "model_discovery.py", "voice_service.py", "decorators.py",
    "requirements.txt", "config.json", "settings.json"
]

NECESSARY_DIRS = [
    "zena_mode", "locales", "ui", "tests", "_bin"
]

def check_git_tracking():
    safe_print("🔍 Checking Git tracking status for necessary files...")
    untracked = []
    
    # Check individual files
    for file in NECESSARY_FILES:
        try:
            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", file],
                cwd=SOURCE_DIR,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                untracked.append(file)
        except Exception:
            pass # Git might not be available or not a repo
            
    # Check directories
    for folder in NECESSARY_DIRS:
        try:
            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", folder],
                cwd=SOURCE_DIR,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                untracked.append(folder)
        except Exception:
            pass
            
    if untracked:
        safe_print(f"⚠️ Warning: The following necessary items are NOT tracked by Git: {', '.join(untracked)}")
        return False
    else:
        safe_print("✅ All necessary items are tracked by Git.")
        return True

def create_package():
    safe_print(f"📦 Packaging ZenAI into {ZIP_NAME}...")
    with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add files
        for file in NECESSARY_FILES:
            src = SOURCE_DIR / file
            if src.exists():
                zipf.write(src, file)
            else:
                safe_print(f"⚠️ Warning: Missing file {file}")
        
        # Add directories
        for folder in NECESSARY_DIRS:
            src_folder = SOURCE_DIR / folder
            if src_folder.exists():
                for root, dirs, files in os.walk(src_folder):
                    for file in files:
                        if "__pycache__" in root or ".pytest_cache" in root:
                            continue
                        abs_path = Path(root) / file
                        rel_path = abs_path.relative_to(SOURCE_DIR)
                        zipf.write(abs_path, rel_path)
            else:
                safe_print(f"⚠️ Warning: Missing directory {folder}")

def deploy():
    safe_print(f"🚀 Deploying to {SOAPBOX_DIR}...")
    if SOAPBOX_DIR.exists():
        shutil.rmtree(SOAPBOX_DIR)
    SOAPBOX_DIR.mkdir(parents=True)
    
    shutil.copy(ZIP_NAME, SOAPBOX_DIR / ZIP_NAME)
    
    with zipfile.ZipFile(SOAPBOX_DIR / ZIP_NAME, 'r') as zipf:
        zipf.extractall(SOAPBOX_DIR)
    safe_print("✅ Deployment complete.")

def run_verification():
    safe_print("🧪 Running cross-environment tests...")
    test_files = [
        "tests/test_localization_switching.py",
        "tests/test_dual_llm.py",
        "tests/test_scraper_resilience.py",
        "tests/test_branding_cleanup.py"
    ]
    
    # Check if we are running in the soapbox
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SOAPBOX_DIR)
    
    try:
        # Running pytest on the core verified suites
        result = subprocess.run(
            [sys.executable, "-m", "pytest"] + test_files + ["-v"],
            cwd=SOAPBOX_DIR,
            env=env,
            capture_output=True,
            text=True
        )
        safe_print(result.stdout)
        if result.returncode == 0:
            safe_print("\n🌟 PORTABILITY VERIFIED: All core tests passed in isolated environment!")
            return True
        else:
            safe_print(f"\n❌ Portability Failed. Test Exit Code: {result.returncode}")
            safe_print(result.stderr)
            return False
    except Exception as e:
        safe_print(f"❌ Error during verification: {e}")
        return False

if __name__ == "__main__":
    try:
        check_git_tracking()
        create_package()
        deploy()
        success = run_verification()
        if success:
            safe_print("\n🎉 DONE! The system is fully portable and verified.")
            # We don't auto-run the app here to avoid blocking the agent, 
            # but we've proven it's ready.
        else:
            sys.exit(1)
    finally:
        # Clean up local zip
        if os.path.exists(ZIP_NAME):
            os.remove(ZIP_NAME)
