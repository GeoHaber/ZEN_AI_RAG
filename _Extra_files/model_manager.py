import os
import json
import re
import requests
import time
from pathlib import Path
from typing import List, Dict, Optional
from huggingface_hub import hf_hub_download, list_repo_files
from tqdm import tqdm

from config import BASE_DIR, MODEL_DIR
from utils import logger

# Enable Fast Downloads (Rust-based)
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
try:
    import hf_transfer
    logger.info("[ModelManager] 🚀 hf_transfer enabled for max speed")
except ImportError:
    pass # hf_hub_download will just ignore the env var if not installed

def parse_model_info(model_name: str, file_size_gb: float = 0) -> Dict:
    """
    Intelligently parse model name to extract useful information.
    Returns user-friendly explanations for casual users.
    """
    info = {
        "name": model_name,
        "parameters": "Unknown",
        "parameters_human": "Unknown size",
        "quantization": "Unknown",
        "quantization_human": "Unknown quality",
        "ram_estimate": "Unknown",
        "speed_rating": "⚡",
        "quality_rating": "⭐⭐⭐",
        "best_for": "General chat",
        "explanation": ""
    }
    
    # Extract parameter count (7B, 13B, 70B, etc.)
    param_match = re.search(r'(\d+\.?\d*)\s*[BbMm](?![a-z])', model_name)
    if param_match:
        param_num = float(param_match.group(1))
        unit = param_match.group(0)[-1].upper()
        
        # Normalize to Billions for consistent logic
        if unit == 'M':
            param_num_b = param_num / 1000
        else:
            param_num_b = param_num
            
        info["parameters"] = f"{param_num}{unit}"
        
        # Generate Human Readable string
        if unit == 'M':
             info["parameters_human"] = f"{param_num} million parameters (Lightweight)"
        else:
             info["parameters_human"] = f"{param_num} billion parameters"

        # Universal RAM Estimation (Roughly 0.6-0.8 GB per Billion params at Q4)
        # Using a conservative 0.7 GB/B baseline + 0.5 GB overhead
        est_ram = (param_num_b * 0.7) + 0.5
        
        if est_ram < 1:
             info["ram_estimate"] = "~512MB RAM"
             info["speed_rating"] = "⚡⚡⚡⚡ Ultra Fast"
             info["best_for"] = "Embedded / Low-power devices"
        elif est_ram < 4:
             info["ram_estimate"] = f"~{int(est_ram)}GB RAM"
             info["speed_rating"] = "⚡⚡⚡ Fast"
             info["best_for"] = "Coding assistants, fast chat"
        elif est_ram < 8:
             info["ram_estimate"] = f"~{int(est_ram)}GB RAM"
             info["speed_rating"] = "⚡⚡ Balanced"
             info["best_for"] = "General purpose, reasoning"
        elif est_ram < 16:
             info["ram_estimate"] = f"~{int(est_ram)}GB RAM"
             info["speed_rating"] = "⚡ Moderate"
             info["best_for"] = "Complex instructions, creative writing"
        else:
             info["ram_estimate"] = ">16GB RAM"
             info["speed_rating"] = "🐢 Heavy"
             info["best_for"] = "Server-grade tasks"
    
    # Extract quantization (Q4, Q5, Q8, etc.)
    quant_match = re.search(r'[Qq](\d+)(?:_K_M|_K_S|_K_L)?', model_name)
    if quant_match:
        quant_level = int(quant_match.group(1))
        info["quantization"] = quant_match.group(0).upper()
        
        if quant_level <= 3:
            info["quantization_human"] = "Very compressed (fastest, lower quality)"
            info["quality_rating"] = "⭐⭐"
        elif quant_level == 4:
            info["quantization_human"] = "Balanced (good speed + quality) ⭐ RECOMMENDED"
            info["quality_rating"] = "⭐⭐⭐⭐"
        elif quant_level == 5:
            info["quantization_human"] = "High quality (slower, better responses)"
            info["quality_rating"] = "⭐⭐⭐⭐⭐"
        elif quant_level >= 8:
            info["quantization_human"] = "Maximum quality (slow, huge file)"
            info["quality_rating"] = "⭐⭐⭐⭐⭐⭐"
    
    # Detect model specialty from name
    name_lower = model_name.lower()
    if 'coder' in name_lower or 'code' in name_lower:
        info["best_for"] = "💻 Coding & programming"
    elif 'instruct' in name_lower:
        info["best_for"] = "💬 Following instructions, Q&A"
    elif 'chat' in name_lower:
        info["best_for"] = "💬 Conversation & chat"
    elif 'math' in name_lower:
        info["best_for"] = "🔢 Math & reasoning"
    
    # Create friendly explanation
    info["explanation"] = f"{info['parameters_human']} • {info['quantization_human']} • Needs {info['ram_estimate']}"
    
    return info

# Popular GGUF model repositories with enhanced info
POPULAR_MODELS = [
    {
        **parse_model_info("qwen2.5-coder-7b-instruct-q4_k_m", 4.4),
        "name": "Qwen 2.5 Coder 7B",
        "repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        "file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        "size_gb": 4.4,
        "description": "🏆 Top coding model - beats GPT-4 on many tasks",
        "downloads": "2.5M+",
        "stars": "12K+",
        "released": "Dec 2024",
        "context_window": "32K tokens (~24,000 words)",
        "strengths": ["Code generation", "Debugging", "Code explanation", "Multi-language coding"],
        "weaknesses": ["Creative writing", "General knowledge (focused on code)"],
        "examples": ["Write a Python web scraper", "Debug SQL query", "Explain code", "Refactor legacy code"],
        "license": "Apache 2.0 (Commercial OK)",
        "languages": "90+ programming languages, English",
        "benchmark": "HumanEval: 88% (top tier)",
    },
    {
        **parse_model_info("Llama-3.2-3B-Instruct-Q4_K_M", 2.0),
        "name": "Llama 3.2 3B",
        "repo": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "size_gb": 2.0,
        "description": "⚡ Lightning fast with huge 128K context - great for long docs",
        "downloads": "1.8M+",
        "stars": "8K+",
        "released": "Sep 2024",
        "context_window": "128K tokens (~96,000 words) 🔥",
        "strengths": ["Speed", "Long documents", "Following instructions", "Reasoning"],
        "weaknesses": ["Complex code", "Deep technical knowledge"],
        "examples": ["Summarize long article", "Answer questions", "Write email", "Brainstorm ideas"],
        "license": "Llama 3.2 License (Commercial OK with limits)",
        "languages": "English primary, 70+ languages supported",
        "benchmark": "MMLU: 72% (excellent for size)",
    },
    {
        **parse_model_info("Mistral-7B-Instruct-v0.3.Q4_K_M", 4.1),
        "name": "Mistral 7B v0.3",
        "repo": "MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF",
        "file": "Mistral-7B-Instruct-v0.3.Q4_K_M.gguf",
        "size_gb": 4.1,
        "description": "🎯 Jack of all trades - solid at everything",
        "downloads": "3.2M+",
        "stars": "15K+",
        "released": "May 2024",
        "context_window": "32K tokens (~24,000 words)",
        "strengths": ["Balanced performance", "Reasoning", "Math", "Writing"],
        "weaknesses": ["Specialized tasks (use focused models)"],
        "examples": ["Research assistant", "Content writing", "Problem solving", "General Q&A"],
        "license": "Apache 2.0 (Commercial OK)",
        "languages": "English, French, German, Spanish, Italian",
        "benchmark": "MMLU: 62% (solid all-around)",
    },
    {
        **parse_model_info("Phi-3-mini-4k-instruct-q4", 2.4),
        "name": "Phi-3 Mini 4K",
        "repo": "microsoft/Phi-3-mini-4k-instruct-gguf",
        "file": "Phi-3-mini-4k-instruct-q4.gguf",
        "size_gb": 2.4,
        "description": "🚀 Tiny powerhouse from Microsoft - punches above its weight",
        "downloads": "850K+",
        "stars": "6K+",
        "released": "Apr 2024",
        "context_window": "4K tokens (~3,000 words)",
        "strengths": ["Efficiency", "Math & STEM", "Mobile/edge devices", "Low RAM"],
        "weaknesses": ["Small context", "Long conversations", "Creative writing"],
        "examples": ["Quick calculations", "Code snippets", "Technical Q&A", "Mobile apps"],
        "license": "MIT (Commercial OK)",
        "languages": "English only",
        "benchmark": "MMLU: 69% (amazing for 3.8B params!)",
    },
    {
        **parse_model_info("deepseek-coder-6.7b-instruct.Q4_K_M", 4.0),
        "name": "DeepSeek Coder 6.7B",
        "repo": "bartowski/deepseek-coder-6.7b-instruct-GGUF",
        "file": "deepseek-coder-6.7b-instruct-Q4_K_M.gguf",
        "size_gb": 4.0,
        "description": "💻 Code specialist - excellent for algorithms & debugging",
        "downloads": "620K+",
        "stars": "4.5K+",
        "released": "Nov 2023",
        "context_window": "16K tokens (~12,000 words)",
        "strengths": ["Code completion", "Bug fixing", "Algorithm design", "Data structures"],
        "weaknesses": ["Non-code tasks", "General chat"],
        "examples": ["Implement algorithm", "Fix production bug", "Code review", "System design"],
        "license": "DeepSeek License (Research + Commercial)",
        "languages": "86 programming languages",
        "benchmark": "HumanEval: 78% (excellent)",
    },
    {
        **parse_model_info("gemma-2-9b-it-Q4_K_M", 5.5),
        "name": "Gemma 2 9B",
        "repo": "bartowski/gemma-2-9b-it-GGUF",
        "file": "gemma-2-9b-it-Q4_K_M.gguf",
        "size_gb": 5.5,
        "description": "🧠 Google's powerful model - great reasoning & safety",
        "downloads": "410K+",
        "stars": "3.8K+",
        "released": "Jun 2024",
        "context_window": "8K tokens (~6,000 words)",
        "strengths": ["Safety", "Reasoning", "Instruction following", "Multitask"],
        "weaknesses": ["Needs 6GB+ RAM", "Smaller context window"],
        "examples": ["Safe content generation", "Educational Q&A", "Tutoring", "Analysis"],
        "license": "Gemma License (Commercial OK)",
        "languages": "English, some multilingual",
        "benchmark": "MMLU: 71% (very capable)",
    },
    {
        **parse_model_info("Meta-Llama-3.1-8B-Instruct-Q4_K_M", 4.9),
        "name": "Llama 3.1 8B",
        "repo": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "file": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "size_gb": 4.9,
        "description": "🦙 Meta's versatile model - strong at reasoning",
        "downloads": "2.1M+",
        "stars": "11K+",
        "released": "Jul 2024",
        "context_window": "128K tokens (~96,000 words) 🔥",
        "strengths": ["Long context", "Reasoning", "Creative writing", "Multilingual"],
        "weaknesses": ["Not specialized for code"],
        "examples": ["Long document analysis", "Creative stories", "Multilingual chat", "Reasoning tasks"],
        "license": "Llama 3.1 License (Commercial OK)",
        "languages": "8 languages (EN, DE, FR, IT, PT, HI, ES, TH)",
        "benchmark": "MMLU: 69% (well-rounded)",
    },
    {
        **parse_model_info("Qwen2.5-14B-Instruct-Q4_K_M", 8.5),
        "name": "Qwen 2.5 14B",
        "repo": "bartowski/Qwen2.5-14B-Instruct-GGUF",
        "file": "Qwen2.5-14B-Instruct-Q4_K_M.gguf",
        "size_gb": 8.5,
        "description": "⚡ Flagship Qwen - exceptional quality if you have RAM",
        "downloads": "520K+",
        "stars": "5.2K+",
        "released": "Sep 2024",
        "context_window": "128K tokens (~96,000 words)",
        "strengths": ["Top quality", "Multilingual", "Long context", "Math & reasoning"],
        "weaknesses": ["Needs 10GB+ RAM", "Slower inference"],
        "examples": ["Complex analysis", "Research", "Multilingual docs", "Advanced reasoning"],
        "license": "Apache 2.0 (Commercial OK)",
        "languages": "29 languages",
        "benchmark": "MMLU: 79% (flagship tier)",
    }
]

def list_available_models() -> List[Dict]:
    """Get list of curated models available for download."""
    return POPULAR_MODELS

def search_huggingface(query: str, limit: int = 10) -> List[Dict]:
    """Search Hugging Face for GGUF models."""
    if not query or not query.strip():
        return []
    try:
        url = "https://huggingface.co/api/models"
        params = {
            "search": query,
            "filter": "gguf",
            "limit": limit,
            "sort": "downloads",
            "direction": -1
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        models = response.json()
        results = []
        
        for model in models:
            results.append({
                "name": model.get("id", "Unknown"),
                "repo": model.get("id", ""),
                "downloads": model.get("downloads", 0),
                "likes": model.get("likes", 0),
                "description": model.get("cardData", {}).get("description", "")[:100]
            })
        
        return results
    except Exception as e:
        logger.error(f"[ModelManager] Search error: {e}")
        return []

def list_repo_gguf_files(repo_id: str) -> List[str]:
    """List all GGUF files in a repository."""
    try:
        files = list_repo_files(repo_id)
        gguf_files = [f for f in files if f.endswith('.gguf')]
        return sorted(gguf_files)
    except Exception as e:
        logger.error(f"[ModelManager] Error listing files in {repo_id}: {e}")
        return []

# Global download progress tracker
import threading
_download_progress = {}  # {filename: {"current": bytes, "total": bytes, "speed": bytes/s, "eta": seconds}}
_progress_lock = threading.Lock()

def get_download_progress(filename: str) -> Optional[Dict]:
    """Get current download progress for a file"""
    with _progress_lock:
        data = _download_progress.get(filename)
        return data.copy() if data else None

def _update_progress(filename: str, current: int, total: int):
    """Internal progress update callback"""
    import time
    
    with _progress_lock:
        now = time.time()
        
        # Initialize if missing (should be init in download_model, but safe fallback)
        if filename not in _download_progress:
            _download_progress[filename] = {
                "start_time": now,
                "initial_size": 0,
                "last_update": now,
                "last_log_percent": -1
            }
        
        progress = _download_progress[filename]
        
        # Calculate SESSION speed (bytes downloaded THIS session / time elapsed THIS session)
        initial_size = progress.get("initial_size", 0)
        downloaded_session = current - initial_size
        time_elapsed = now - progress.get("start_time", now)
        
        # Avoid division by zero
        if time_elapsed < 0.1: time_elapsed = 0.1
            
        speed = downloaded_session / time_elapsed if downloaded_session > 0 else 0
        
        # Calculate ETA
        bytes_remaining = total - current
        eta = bytes_remaining / speed if speed > 0 else 0
        
        percent = (current / total * 100) if total > 0 else 0
        
        # Update progress
        progress.update({
            "downloaded_bytes": current,
            "total_bytes": total,
            "speed_bytes_per_sec": speed,
            "eta_seconds": eta,
            "percent": percent,
            "last_update": now
        })
        
        # Log only on meaningful changes (every 5%) to prevent spam
        last_log = progress.get("last_log_percent", -1)
        if percent - last_log >= 5 or percent == 100:
            progress["last_log_percent"] = percent
            logger.info(f"[Download] {filename}: {percent:.1f}% ({current}/{total} bytes) @ {speed/1024/1024:.2f} MB/s")

def download_model(repo_id: str, filename: str, progress_callback=None) -> Optional[Path]:
    """
    Download a GGUF model from Hugging Face.
    """
    try:
        logger.info(f"[ModelManager] Downloading {filename} from {repo_id}...")
        
        # Ensure model directory exists
        MODEL_DIR.mkdir(exist_ok=True, parents=True)
        
        # Initialize progress tracking - FRESH START
        with _progress_lock:
             _download_progress[filename] = {
                "start_time": time.time(),
                 "initial_size": 0, # Will be updated if we resume
                 "status": "downloading",
                 "percent": 0,
                 "last_log_percent": -1
             }
        
        # Download with progress using tqdm hook
        # Validate inputs
        if not re.match(r'^[\w\-\.]+/[\w\-\.]+$', repo_id):
            raise ValueError("Invalid repo_id format")
        if not re.match(r'^[\w\-\.]+\.gguf$', filename):
             raise ValueError("Invalid filename. Must be a .gguf file")

        # Get URL using hf_hub_url
        # Get URL using hf_hub_url
        from huggingface_hub import hf_hub_url
        logger.info(f"[ModelManager] Resolving URL for {repo_id}/{filename}...")
        url = hf_hub_url(repo_id, filename)
        logger.info(f"[ModelManager] URL Resolved: {url}")
        
        file_path = MODEL_DIR / filename
        logger.info(f"[ModelManager] Output path: {file_path}")
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resume_header = {}
                file_mode = 'wb'
                current_size = 0
                
                # Check if partial file exists for resume
                if file_path.exists():
                    current_size = file_path.stat().st_size
                    # Update initial size for accurate speed calc
                    with _progress_lock:
                        _download_progress[filename]["initial_size"] = current_size

                    if current_size > 0:
                        resume_header = {'Range': f'bytes={current_size}-'}
                        file_mode = 'ab'
                        print(f"DEBUG: Resuming download from {current_size} bytes", flush=True)
                    else:
                        print(f"DEBUG: Overwriting empty file", flush=True)

                print(f"DEBUG: Sending Request to {url}", flush=True)
                response = requests.get(url, stream=True, headers=resume_header, allow_redirects=True, timeout=30)
                
                # Handle 416 Range Not Satisfiable
                if response.status_code == 416: 
                    print("DEBUG: Received 416 - File likely complete.", flush=True)
                    if current_size > 0:
                         with _progress_lock:
                            _download_progress[filename]["status"] = "complete"
                            _download_progress[filename]["percent"] = 100
                         return file_path
                    else:
                        # Retry without resume
                        resume_header = {}
                        file_mode = 'wb'
                        current_size = 0
                        # Reset initial size
                        with _progress_lock:
                            _download_progress[filename]["initial_size"] = 0
                        response = requests.get(url, stream=True, allow_redirects=True, timeout=30)

                response.raise_for_status()
                
                total_size_response = int(response.headers.get('content-length', 0))
                total_size = total_size_response + current_size
                
                print(f"DEBUG: Content-Length: {total_size_response}, Total Linked: {total_size}", flush=True)
                
                _update_progress(filename, current_size, total_size)
                
                block_size = 1024 * 1024  # 1MB chunks
                
                with open(file_path, file_mode) as f:
                    for chunk in response.iter_content(chunk_size=block_size):
                        if chunk:
                            f.write(chunk)
                            current_size += len(chunk)
                            _update_progress(filename, current_size, total_size)
                            if progress_callback:
                                progress_callback(current_size, total_size)
                
                # If we get here, download was successful
                print(f"DEBUG: Download Loop Finished. Total: {current_size}", flush=True)
                break
                
            except (requests.exceptions.RequestException, IOError) as e:
                logger.warning(f"[ModelManager] Download attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2 ** attempt)  # Exponential backoff
        
        # Mark as complete
        with _progress_lock:
            if filename in _download_progress:
                _download_progress[filename]["status"] = "complete"
                _download_progress[filename]["percent"] = 100
        
        logger.info(f"[ModelManager] Downloaded to: {file_path}")
        return Path(file_path)
        
    except Exception as e:
        logger.error(f"[ModelManager] Download failed: {e}")
        with _progress_lock:
            if filename in _download_progress:
                _download_progress[filename]["status"] = "failed"
                _download_progress[filename]["error"] = str(e)
        return None

def get_installed_models() -> List[Dict]:
    """Get list of locally installed GGUF models."""
    if not MODEL_DIR.exists():
        return []
    
    models = []
    for gguf_file in MODEL_DIR.glob("*.gguf"):
        stat = gguf_file.stat()
        models.append({
            "name": gguf_file.name,
            "path": str(gguf_file),
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 1)
        })
    
    return sorted(models, key=lambda x: x['name'])

def delete_model(model_name: str) -> bool:
    """Delete a locally installed model."""
    try:
        model_path = MODEL_DIR / model_name
        if not model_path.exists():
             raise FileNotFoundError(f"Model {model_name} not found")
        
        model_path.unlink()
        logger.info(f"[ModelManager] Deleted: {model_name}")
        return True
    except Exception as e:
        logger.error(f"[ModelManager] Delete failed: {e}")
        raise e  # Propagate error to caller for UI handling

if __name__ == "__main__":
    # Test the model manager with intelligent info display
    print("=== ZenAI Model Manager ===\n")
    
    print("📚 Popular Models (with smart info):\n")
    for model in list_available_models():
        print(f"🔹 {model['name']}")
        print(f"   {model['explanation']}")
        print(f"   {model['speed_rating']} | {model['quality_rating']}")
        print(f"   Best for: {model['best_for']}")
        print(f"   {model['description']}")
        print(f"   Download: {model['size_gb']}GB\n")
    
    print(f"\n💾 Installed Models ({MODEL_DIR}):")
    installed = get_installed_models()
    if installed:
        for model in installed:
            info = parse_model_info(model['name'])
            print(f"  ✅ {model['name']}")
            print(f"     {info['explanation']}")
    else:
        print("  (none)")
