# dependency_manager.py
# Centralized Auto-Healing Dependency Manager for ZenAI RAG

import sys
import subprocess
import importlib
import importlib.util
import logging
import os

# Configure a simple logger for this module before the main logger is set up
logging.basicConfig(level=logging.INFO, format='%(asctime)s [Setup] %(message)s')
logger = logging.getLogger("DependencyManager")

# --- Dependency Manifest ---
# Format: "Import Name": "Pip Package Name"
# Note: Only include packages that are strictly required for startup or core functionality.
REQUIRED_PACKAGES = {
    # Core GUI & Async
    "nicegui": "nicegui",
    "websockets": "websockets",
    "aiohttp": "aiohttp",
    "httpx": "httpx",
    
    # System & Hardware
    "psutil": "psutil",
    "numpy": "numpy",
    "tqdm": "tqdm",
    "requests": "requests",
    
    # AI & ML
    "huggingface_hub": "huggingface_hub",
    "sentence_transformers": "sentence-transformers",
    # "faiss": "faiss-cpu",  # faiss import name depends on install, usually 'faiss'
    
    # Media & Processing
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "pypdf": "pypdf",
    # "sounddevice": "sounddevice", # Optional/Heavy
    
    # Utils
    "bs4": "beautifulsoup4",
}

def is_installed(import_name: str) -> bool:
    """Check if a package is installed without importing it."""
    try:
        if import_name in sys.modules:
            return True
        return importlib.util.find_spec(import_name) is not None
    except (ImportError, ValueError):
        return False

def check_and_install():
    """
    Checks all required packages and installs missing ones in a single batch.
    This is faster and cleaner than installing one by one.
    """
    missing_packages = [] # List of pip package names to install
    
    logger.info("Verifying environment dependencies...")
    
    for import_name, install_name in REQUIRED_PACKAGES.items():
        if not is_installed(import_name):
            logger.warning(f"Missing dependency: {import_name} (requires {install_name})")
            missing_packages.append(install_name)
    
    # Special Handling for FAISS (faiss-cpu vs faiss-gpu)
    if not is_installed("faiss"):
        # We default to cpu for safety if missing
        logger.warning("Missing dependency: faiss")
        missing_packages.append("faiss-cpu")

    if missing_packages:
        logger.info(f"Missing {len(missing_packages)} packages: {', '.join(missing_packages)}")
        # By default do not auto-install heavy packages during startup to avoid
        # long blocking network operations. Set env var `ZENAI_AUTO_INSTALL=1`
        # to enable automatic installation when you explicitly want it.
        if os.environ.get("ZENAI_AUTO_INSTALL", "0") != "1":
            logger.warning("Auto-install disabled. Set ZENAI_AUTO_INSTALL=1 to enable installs.")
            logger.info("Please install missing packages manually or run: pip install -r requirements.txt")
            return False

        logger.info(f"Healing environment... Installing {len(missing_packages)} packages.")
        logger.info(f"Targets: {', '.join(missing_packages)}")
        try:
            cmd = [sys.executable, "-m", "pip", "install"] + missing_packages
            subprocess.check_call(cmd)
            logger.info("✅ Dependencies restored successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install dependencies. Error: {e}")
            logger.error("Please try running: pip install -r requirements.txt")
            sys.exit(1)
        except Exception as e:
            logger.error(f"❌ Unexpected error during installation: {e}")
            sys.exit(1)
    else:
        logger.info("✅ Environment looks good.")
    return True

if __name__ == "__main__":
    check_and_install()
