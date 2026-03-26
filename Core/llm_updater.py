"""
Core/llm_updater.py — ZEN_RAG LLM Package Freshness Checker
=============================================================
Checks PyPI for newer versions of llama-cpp-python (and optionally
other key inference backends) and provides a safe upgrade helper.

Usage (in sidebar.py):
    from Core.llm_updater import check_llamacpp_update, run_upgrade

    installed, latest = check_llamacpp_update()   # cached via Streamlit
    if latest:
        st.sidebar.info(f"llama.cpp {latest} available!")
        if st.sidebar.button("Update"):
            run_upgrade(progress_cb=st.sidebar.empty().text)
"""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Callable, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Optional packaging import ──────────────────────────────────────────────
try:
    from packaging.version import Version

    _PACKAGING = True
except ImportError:
    _PACKAGING = False
    logger.debug("packaging not installed — version comparison uses string split")

# Packages we can check/update
WATCHED_PACKAGES = {
    "llama-cpp-python": {
        "display": "llama.cpp Python",
        "emoji": "🦙",
        "pypi_name": "llama-cpp-python",
    },
    "sentence-transformers": {
        "display": "Sentence Transformers",
        "emoji": "🔢",
        "pypi_name": "sentence-transformers",
    },
    "faster-whisper": {
        "display": "Faster Whisper",
        "emoji": "🎙️",
        "pypi_name": "faster-whisper",
    },
}


# =============================================================================
# VERSION HELPERS
# =============================================================================


def get_installed_version(package: str) -> Optional[str]:
    """Return installed version of a package, or None if not found."""
    try:
        from importlib.metadata import version

        return version(package)
    except Exception as exc:
        logger.debug("%s", exc)
    # Fallback: pip show
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    except Exception as exc:
        logger.debug("%s", exc)
    return None


def get_latest_pypi_version(package: str, timeout: int = 5) -> Optional[str]:
    """Query PyPI JSON API for the latest release version."""
    try:
        import requests  # type: ignore

        resp = requests.get(
            f"https://pypi.org/pypi/{package}/json",
            timeout=timeout,
            headers={"User-Agent": "ZEN_RAG/4.0 version-checker"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["info"]["version"]
    except Exception as e:
        logger.debug(f"PyPI check for {package} failed: {e}")
    return None


def is_newer(installed: str, latest: str) -> bool:
    """Return True if latest > installed."""
    if not installed or not latest:
        return False
    try:
        if _PACKAGING:
            return Version(latest) > Version(installed)

        # Naive tuple comparison
        def _parts(v: str):
            return tuple(int(x) for x in v.split(".")[:3] if x.isdigit())

        return _parts(latest) > _parts(installed)
    except Exception:
        return latest != installed


# =============================================================================
# MAIN CHECKER  (designed to be wrapped in @st.cache_data)
# =============================================================================


def check_llamacpp_update(timeout: int = 5) -> Tuple[Optional[str], Optional[str]]:
    """
    Check if a newer llama-cpp-python is available on PyPI.

    Returns:
        (installed_version, latest_version)
        If no update available or check fails: (installed, None)
    """
    pkg = "llama-cpp-python"
    installed = get_installed_version(pkg)
    if not installed:
        logger.debug("llama-cpp-python not installed — skipping update check")
        return None, None

    latest = get_latest_pypi_version(pkg, timeout=timeout)
    if latest and is_newer(installed, latest):
        logger.info(f"llama-cpp-python update available: {installed} → {latest}")
        return installed, latest

    return installed, None


def check_all_updates(timeout: int = 5) -> dict[str, Tuple[str, str]]:
    """
    Check all WATCHED_PACKAGES for updates.

    Returns:
        dict of package_name → (installed_version, latest_version)
        Only includes packages that have an update available.
    """
    updates: dict[str, Tuple[str, str]] = {}
    for pkg, meta in WATCHED_PACKAGES.items():
        installed = get_installed_version(pkg)
        if not installed:
            continue
        latest = get_latest_pypi_version(pkg, timeout=timeout)
        if latest and is_newer(installed, latest):
            updates[pkg] = (installed, latest)
    return updates


# =============================================================================
# UPGRADE RUNNER
# =============================================================================


def run_upgrade(
    package: str = "llama-cpp-python",
    target_version: Optional[str] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
    extra_pip_args: Optional[list] = None,
) -> Tuple[bool, str]:
    """
    Run pip upgrade for a package.

    Args:
        package:        Package name (default: llama-cpp-python)
        target_version: If set, installs that exact version
        progress_cb:    Called with status strings during install
        extra_pip_args: Extra args passed to pip (e.g. ["--no-deps"])

    Returns:
        (success, message)
    """
    spec = f"{package}=={target_version}" if target_version else f"{package}"
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", spec]
    if extra_pip_args:
        cmd.extend(extra_pip_args)

    if progress_cb:
        progress_cb(f"Running: {' '.join(cmd)}")

    logger.info(f"Running upgrade: {cmd}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            shell=False,
        )

        output_lines = []
        for line in proc.stdout:  # type: ignore
            line = line.rstrip()
            output_lines.append(line)
            if progress_cb:
                progress_cb(line)
            logger.debug(f"pip: {line}")

        proc.wait(timeout=300)  # 5 min max
        success = proc.returncode == 0

        msg = "\n".join(output_lines[-5:])  # Last 5 lines as summary
        if success:
            logger.info(f"Upgrade of {package} succeeded")
            return True, f"✅ {package} upgraded successfully.\n{msg}"
        else:
            logger.error(f"Upgrade of {package} failed (rc={proc.returncode})")
            return False, f"❌ Upgrade failed (exit {proc.returncode}).\n{msg}"

    except subprocess.TimeoutExpired:
        return False, "❌ Upgrade timed out after 5 minutes."
    except Exception as e:
        return False, f"❌ Unexpected error: {e}"


def get_changelog_url(package: str = "llama-cpp-python") -> str:
    """Return a PyPI changelog/release URL for the package."""
    url_map = {
        "llama-cpp-python": "https://github.com/abetlen/llama-cpp-python/releases",
        "sentence-transformers": "https://github.com/UKPLab/sentence-transformers/releases",
        "faster-whisper": "https://github.com/SYSTRAN/faster-whisper/releases",
    }
    return url_map.get(package, f"https://pypi.org/project/{package}/#history")
