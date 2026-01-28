import os
import logging
import httpx
import re
from pathlib import Path
from typing import List, Dict, Optional
from config_system import config
from huggingface_hub import HfApi

logger = logging.getLogger("AutoUpdater")

class ModelScout:
    """
    Intelligence layer to discover high-performing GGUF models on Hugging Face.
    """
    def __init__(self):
        self.api = HfApi()
        self.categories = {
            "coding": ["qwen", "codellama", "deepseek-coder"],
            "reasoning": ["meta-llama", "mistral", "phi-3"],
            "creative": ["gemma", "command-r"]
        }

    def find_shiny_models(self, category: str = "coding", limit: int = 3) -> List[Dict]:
        """
        Scour Hugging Face for trending/best models in a given category.
        """
        try:
            keywords = self.categories.get(category.lower(), ["llama"])
            models = self.api.list_models(
                task="text-generation",
                library="gguf",
                tags=keywords,
                sort="downloads",
                direction=-1,
                limit=limit * 3 # Fetch more to filter manually
            )
            
            shiny_list = []
            for m in models:
                # Basic quality filtering: must have many downloads and recent updates
                if m.downloads > 1000:
                    shiny_list.append({
                        "id": m.modelId,
                        "downloads": m.downloads,
                        "likes": m.likes,
                        "last_modified": m.lastModified
                    })
            
            return sorted(shiny_list, key=lambda x: x['downloads'], reverse=True)[:limit]
        except Exception as e:
            logger.error(f"Model Scout failed for category {category}: {e}")
            return []

def is_newer(remote_tag: str, local_tag: str) -> bool:
    """
    Compare llama.cpp version tags (e.g., 'b4100' or 'v1.2.3').
    Returns True if remote_tag is logically strictly greater than local_tag.
    """
    def parse_version(tag: str):
        # Extract digits: b4100 -> 4100, v1.2.3 -> (1, 2, 3)
        digits = re.findall(r'\d+', tag)
        return tuple(map(int, digits))
    
    try:
        remote_val = parse_version(remote_tag)
        local_val = parse_version(local_tag)
        return remote_val > local_val
    except Exception:
        return False

def check_for_updates(current_tag: str = "unknown") -> dict:
    """
    Queries GitHub API for the latest llama.cpp release.
    Returns update info dict if a newer version is found, else None.
    """
    url = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    try:
        with httpx.Client() as client:
            resp = client.get(url, headers=headers, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                latest_tag = data.get("tag_name", "")
                
                if is_newer(latest_tag, current_tag):
                    logger.info(f"✨ Shiny new version found: {latest_tag} (Current: {current_tag})")
                    return {
                        "tag": latest_tag,
                        "url": data.get("html_url"),
                        "assets": data.get("assets", [])
                    }
    except Exception as e:
        logger.error(f"Failed to check for llama.cpp updates: {e}")
    
    return None

def perform_swap(target_path: str, new_path: str):
    """
    Safely swaps binary files with backup.
    """
    target = Path(target_path)
    new_bin = Path(new_path)
    backup = target.with_suffix(".bak")
    
    if not new_bin.exists():
        raise FileNotFoundError(f"New binary not found at {new_path}")
    
    # 1. Backup current (if exists)
    if target.exists():
        if backup.exists():
            backup.unlink() # Delete old backup
        os.rename(target, backup)
        logger.info(f"Backed up current binary to {backup.name}")
    
    # 2. Move new binary into place
    os.rename(new_bin, target)
    logger.info(f"Successfully swapped binary: {target.name}")

async def get_local_version() -> str:
    """Attempt to get local llama-server version using --version."""
    import subprocess
    import asyncio
    
    bin_path = Path(config.bin_dir) / "llama-server.exe"
    if not bin_path.exists():
        return "none"
        
    try:
        proc = await asyncio.create_subprocess_exec(
            str(bin_path), "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        version_str = stdout.decode().strip() or stderr.decode().strip()
        # Extract something like 'b4000'
        match = re.search(r'b\d+', version_str)
        return match.group(0) if match else version_str[:10]
    except Exception:
        return "unknown"
