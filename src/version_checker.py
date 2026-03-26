"""
src/version_checker.py — Version checking utility for ZEN_RAG

Checks for updates to:
1. llama-cpp-python library (via PyPI)
2. GGUF models on HuggingFace
"""

import json
import logging
import urllib.request
from typing import Optional, Dict, Any
from packaging import version

logger = logging.getLogger("ZEN_RAG.VersionChecker")


def get_latest_pypi_version(package_name: str) -> Optional[str]:
    """Fetch the latest version of a package from PyPI."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data["info"]["version"]
    except Exception as e:
        logger.warning(f"Failed to fetch PyPI version for {package_name}: {e}")
        return None


def check_library_update(current_version: str) -> Dict[str, Any]:
    """Check if llama-cpp-python has an update."""
    package = "llama-cpp-python"
    latest = get_latest_pypi_version(package)
    if not latest:
        return {"update_available": False, "error": "Could not fetch latest version"}

    has_update = version.parse(latest) > version.parse(current_version)
    return {
        "current": current_version,
        "latest": latest,
        "update_available": has_update,
        "message": f"Update available: {latest}" if has_update else "Up to date",
    }


def get_hf_model_metadata(repo_id: str) -> Optional[Dict[str, Any]]:
    """Fetch metadata for a HuggingFace repository."""
    url = f"https://huggingface.co/api/models/{repo_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ZEN_RAG/4.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        logger.warning(f"Failed to fetch HF metadata for {repo_id}: {e}")
        return None


def check_model_update(repo_id: str, local_last_modified: str) -> Dict[str, Any]:
    """
    Check if a model in a HF repo has been updated since local download.
    local_last_modified should be in ISO format or YYYY-MM-DD.
    """
    meta = get_hf_model_metadata(repo_id)
    if not meta:
        return {"update_available": False, "error": "Could not fetch repo metadata"}

    remote_last_modified = meta.get("lastModified", "")
    if not remote_last_modified:
        return {"update_available": False, "error": "No lastModified date in remote"}

    # Simple string comparison for ISO dates works for "later than"
    has_update = remote_last_modified > local_last_modified

    return {
        "repo": repo_id,
        "remote_date": remote_last_modified,
        "local_date": local_last_modified,
        "update_available": has_update,
    }
