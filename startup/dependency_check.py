"""
Startup Module - Dependency and Environment Checks
===================================================
Handles:
- Python package dependency checking and installation
- Tesseract OCR setup (Windows automation)
- Hardware capability detection
- Lazy-loaded - NO side effects on import
- All functions are triggered explicitly by app.py, not on startup

Key functions:
    check_and_install_dependencies() -> bool
    setup_tesseract() -> bool
    get_latest_versions() -> dict
    detect_hardware() -> dict
"""

import subprocess
import sys
import os


def _version_tuple(version_str: str) -> tuple:
    """Convert a version string like '1.2.3' to a tuple of ints for proper comparison."""
    try:
        return tuple(int(x) for x in version_str.split("."))
    except (ValueError, AttributeError):
        return (0,)


# =============================================================================
# DEPENDENCY METADATA
# =============================================================================

REQUIRED_PACKAGES = {
    # Package name: (import_name, min_version, description)
    "streamlit": ("streamlit", "1.28.0", "UI Framework"),
    "requests": ("requests", "2.31.0", "HTTP Client"),
    "psutil": ("psutil", "5.9.0", "Hardware Detection"),
    "pymupdf": ("fitz", "1.23.0", "PDF Extraction"),
    "pytesseract": ("pytesseract", "0.3.10", "OCR Engine"),
    "opencv-python": ("cv2", "4.8.0", "Image Processing"),
    "Pillow": ("PIL", "10.0.0", "Image Library"),
    "numpy": ("numpy", "1.24.0", "Numerical Computing"),
    "sentence-transformers": ("sentence_transformers", "2.2.0", "Embeddings"),
    "beautifulsoup4": ("bs4", "4.12.0", "HTML Parsing"),
}

OPTIONAL_PACKAGES = {
    "qdrant-client": ("qdrant_client", "1.7.0", "Vector Database"),
    "faiss-cpu": ("faiss", "1.7.4", "Vector Search"),
    "faster-whisper": ("faster_whisper", "0.10.0", "Speech Recognition"),
}

# =============================================================================
# TESSERACT OCR CONFIGURATION
# =============================================================================

TESSERACT_VERSION = "5.5.0.20241111"
TESSERACT_URL = f"https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-{TESSERACT_VERSION}.exe"
TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


# =============================================================================
# TESSERACT FUNCTIONS
# =============================================================================


def find_tesseract() -> str:
    """Find Tesseract executable.

    Returns:
        Path to tesseract.exe if found, None otherwise
    """
    import shutil

    # Check if in PATH
    tesseract_in_path = shutil.which("tesseract")
    if tesseract_in_path:
        return tesseract_in_path

    # Check common install locations
    for path in TESSERACT_PATHS:
        if os.path.exists(path):
            return path

    return None


def install_tesseract() -> bool:
    """Download and install Tesseract OCR. Requires admin for silent install.

    Returns:
        True if installation succeeded, False otherwise
    """
    import tempfile
    import urllib.request

    print(f"\n🔧 Tesseract OCR not found. Installing v{TESSERACT_VERSION}...")
    print("   (This is a ~75MB download, please wait...)")

    try:
        installer_path = os.path.join(tempfile.gettempdir(), "tesseract-installer.exe")
        print("  → Downloading from GitHub...")
        urllib.request.urlretrieve(TESSERACT_URL, installer_path)
        print("  → Download complete")

        # Try silent install first (requires admin)
        print("  → Attempting silent install...")
        result = subprocess.run(
            [installer_path, "/S"],
            capture_output=True,
            timeout=300,
            shell=False,
        )

        if result.returncode == 0:
            print("  ✓ Tesseract installed successfully")
            try:
                os.remove(installer_path)
            except Exception as exc:
                _ = exc  # suppressed intentionally
            return True
        else:
            # Silent install failed (likely no admin rights)
            # Launch interactive installer instead
            print("  ⚠ Silent install requires admin. Launching installer...")
            subprocess.Popen([installer_path])
            print("  → Please complete the installation manually.")
            print("  → Default path: C:\\Program Files\\Tesseract-OCR")
            print("  → Restart the app after installation.")
            return False

    except Exception as e:
        print(f"  ✗ Installation error: {e}")
        print("  → Download manually: https://github.com/tesseract-ocr/tesseract/releases")
        return False


def setup_tesseract() -> bool:
    """Find or install Tesseract and configure pytesseract.

    Returns:
        True if Tesseract is available and configured, False otherwise
    """
    tesseract_path = find_tesseract()

    if not tesseract_path:
        # Try to install on Windows
        if sys.platform == "win32":
            if install_tesseract():
                tesseract_path = find_tesseract()
        else:
            print("⚠️ Tesseract not found. Install with: sudo apt install tesseract-ocr")

    if tesseract_path:
        try:
            import pytesseract

            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print(f"✓ Tesseract configured: {tesseract_path}")
            return True
        except ImportError as exc:
            _ = exc  # suppressed intentionally

    return False


# =============================================================================
# PACKAGE MANAGEMENT FUNCTIONS
# =============================================================================


def get_installed_version(package_name: str) -> str:
    """Get installed version of a package.

    Args:
        package_name: Name of the package (as shown by pip)

    Returns:
        Version string, or None if not found
    """
    try:
        import importlib.metadata

        return importlib.metadata.version(package_name)
    except Exception:
        return None


def check_import(import_name: str) -> bool:
    """Check if a package can be imported.

    Args:
        import_name: Name to use in __import__()

    Returns:
        True if importable, False otherwise
    """
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False


def install_package(package: str, upgrade: bool = False) -> bool:
    """Install a package using pip.

    Args:
        package: Package name or requirement spec (e.g., "numpy>=1.20")
        upgrade: If True, upgrade existing package

    Returns:
        True if successful, False otherwise
    """
    try:
        cmd = [sys.executable, "-m", "pip", "install"]
        if upgrade:
            cmd.append("--upgrade")
        cmd.append(package)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, shell=False)
        return result.returncode == 0
    except Exception:
        print(f"Failed to install {package}: {e}")
        return False


def check_and_install_dependencies(show_status: bool = True) -> bool:
    """Check all dependencies and install missing ones.

    Args:
        show_status: If True, print status messages

    Returns:
        True if all required packages are available, False otherwise
    """
    missing = []
    outdated = []
    installed = []

    for pkg_name, (import_name, min_version, desc) in REQUIRED_PACKAGES.items():
        installed_ver = get_installed_version(pkg_name)
        can_import = check_import(import_name)

        if not can_import or installed_ver is None:
            missing.append((pkg_name, min_version, desc))
        elif _version_tuple(installed_ver) < _version_tuple(min_version):
            outdated.append((pkg_name, installed_ver, min_version, desc))
        else:
            installed.append((pkg_name, installed_ver, desc))

    # Auto-install missing packages
    if missing:
        print(f"\n🔧 Installing {len(missing)} missing packages...")
        for pkg_name, min_version, desc in missing:
            print(f"  → Installing {pkg_name}>={min_version} ({desc})...")
            if install_package(f"{pkg_name}>={min_version}"):
                print(f"    ✓ {pkg_name} installed")
                pass
            else:
                print(f"    ✗ Failed to install {pkg_name}")
                pass
                # Upgrade outdated packages
                pass
    if outdated:
        print(f"\n📦 Upgrading {len(outdated)} outdated packages...")
        for pkg_name, curr_ver, min_ver, desc in outdated:
            print(f"  → Upgrading {pkg_name} ({curr_ver} → {min_ver}+)...")
            if install_package(f"{pkg_name}>={min_ver}", upgrade=True):
                print(f"    ✓ {pkg_name} upgraded")
                pass
            else:
                print(f"    ✗ Failed to upgrade {pkg_name}")
                pass
    if show_status and (missing or outdated):
        print("\n✅ Dependency check complete. Please restart the app if packages were installed.\n")

    return len(missing) == 0 and len(outdated) == 0


def get_latest_versions() -> dict:
    """Check PyPI for latest versions of our packages.

    Returns:
        Dict mapping package names to latest versions on PyPI
    """
    import requests

    latest = {}
    for pkg_name in REQUIRED_PACKAGES.keys():
        try:
            r = requests.get(f"https://pypi.org/pypi/{pkg_name}/json", timeout=5)
            if r.status_code == 200:
                latest[pkg_name] = r.json()["info"]["version"]
        except Exception as exc:
            _ = exc  # suppressed intentionally
    return latest


__all__ = [
    "check_and_install_dependencies",
    "setup_tesseract",
    "find_tesseract",
    "install_tesseract",
    "get_latest_versions",
    "REQUIRED_PACKAGES",
    "OPTIONAL_PACKAGES",
]
