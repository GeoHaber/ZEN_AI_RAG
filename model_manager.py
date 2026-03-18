# -*- coding: utf-8 -*-
"""
model_manager.py - Hugging Face model search, download, and management.

Provides helpers used by the management API for browsing, downloading,
and activating GGUF models from Hugging Face Hub.
"""

import logging
import threading
from pathlib import Path
from config_system import config

logger = logging.getLogger(__name__)

# Popular curated GGUF models
_POPULAR_MODELS = [
    {
        "repo_id": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        "filename": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        "name": "Qwen2.5-Coder-7B (Q4_K_M)",
        "size_gb": 4.4,
        "description": "Fast coding assistant, good balance of quality and speed",
    },
    {
        "repo_id": "bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF",
        "filename": "DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
        "name": "DeepSeek-Coder-V2-Lite (Q4_K_M)",
        "size_gb": 9.0,
        "description": "Strong coding model with MoE architecture",
    },
]


def get_popular_models():
    """Return a curated list of popular GGUF models."""
    return _POPULAR_MODELS


def search_hf_models(query: str, limit: int = 10):
    """Search Hugging Face Hub for GGUF models."""
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        results = api.list_models(
            search=query,
            filter="gguf",
            sort="downloads",
            direction=-1,
            limit=limit,
        )
        return [
            {"repo_id": m.id, "downloads": m.downloads, "likes": m.likes}
            for m in results
        ]
    except ImportError:
        logger.warning("huggingface_hub not installed — search unavailable")
        return []
    except Exception as e:
        logger.error(f"HF search failed: {e}")
        return []


def download_model_async(repo_id: str, filename: str):
    """Download a model file in a background thread."""

    def _download():
        try:
            from huggingface_hub import hf_hub_download
            logger.info(f"Downloading {filename} from {repo_id}...")
            path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=str(config.MODEL_DIR),
            )
            logger.info(f"Download complete: {path}")
        except ImportError:
            logger.error("huggingface_hub not installed — cannot download models")
        except Exception as e:
            logger.error(f"Download failed: {e}")

    t = threading.Thread(target=_download, daemon=True, name=f"dl-{filename}")
    t.start()
    return t
