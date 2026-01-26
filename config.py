import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
_config_logger = logging.getLogger("ZenAIConfig")

# --- Project Paths ---
BASE_DIR: Path = Path(__file__).resolve().parent
LOG_FILE: Path = BASE_DIR / "nebula_debug.log"
PID_FILE: Path = BASE_DIR / ".nebula_ui.pid"

# --- Load Config from JSON (ZenAI Installer Interface) ---
CONFIG_JSON = BASE_DIR / "config.json"
_external_config: Dict = {}
if CONFIG_JSON.exists():
    try:
        with open(CONFIG_JSON, "r") as f:
            _external_config = json.load(f)
        _config_logger.info(f"Loaded config from {CONFIG_JSON}")
    except json.JSONDecodeError as e:
        _config_logger.warning(f"Failed to parse config.json: {e}, using defaults")
    except (IOError, OSError) as e:
        _config_logger.warning(f"Failed to read config.json: {e}, using defaults")

# --- Ports ---
PORTS = {
    "LLM_API": _external_config.get("llm_port", 8001),      # The main OpenAI-compatible API
    "MGMT_API": _external_config.get("mgmt_port", 8002),     # The management API for upgrades/swaps
    "UI_SERVER": _external_config.get("ui_port", 8080),    # The frontend UI server
    "UI_LOCK": 8081       # Singleton lock for the UI
}
HOST: str = "127.0.0.1"

# --- Directories (Priority: ENV > JSON > Default) ---
_bin_default = BASE_DIR / "_bin"
_model_default = BASE_DIR / "AI_Models"

def _get_dir(env_var: str, json_key: str, default: Path) -> Path:
    """Get directory with priority: ENV > JSON > default."""
    if env_path := os.getenv(env_var):
        _config_logger.info(f"{env_var} override: {env_path}")
        return Path(env_path)
    if json_key in _external_config:
        return Path(_external_config[json_key])
    return default

BIN_DIR = _get_dir("NEBULA_BIN_DIR", "bin_dir", _bin_default)
MODEL_DIR = _get_dir("NEBULA_MODEL_DIR", "model_dir", _model_default)

# Auto-detect common central storage if local is empty
_central_store = Path("C:/AI/Models")
if MODEL_DIR == _model_default:  # Only auto-detect if using default
    if not MODEL_DIR.exists() and _central_store.exists():
        MODEL_DIR = _central_store
        _config_logger.info(f"Auto-detected model dir: {_central_store}")
    elif MODEL_DIR.exists() and not list(MODEL_DIR.glob("*.gguf")) and _central_store.exists():
        if list(_central_store.glob("*.gguf")):
             MODEL_DIR = _central_store

# --- Models ---
# Default Configuration for Qwen 2.5 Coder
MODEL_REPO: str = "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF"
MODEL_FILE: str = "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
DEFAULT_MODEL_PATH: Path = MODEL_DIR / MODEL_FILE

DRAFT_REPO = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
DRAFT_FILE = "qwen2.5-0.5b-instruct-q5_k_m.gguf"

# SHA256 Hashes (Security Hardening)
# If set to None, verification is skipped with a warning.
# TODO: Release v2.1 should populate these with strict values.
HASHES: Dict[str, str] = {
    MODEL_FILE: None,
    DRAFT_FILE: None,
}

# --- Binaries ---
BIN_BASE_URL = "https://github.com/ggerganov/llama.cpp/releases/download/b4445/"
# Format: (Filename, SHA256)
BIN_VARIANTS = {
    "NVIDIA": ("llama-b4445-bin-win-cu12.4-x64.zip", None),
    "AMD": ("llama-b4445-bin-win-vulkan-x64.zip", None),
    "INTEL": ("llama-b4445-bin-win-vulkan-x64.zip", None),
    "CPU": ("llama-b4445-bin-win-avx2-x64.zip", None)
}


# --- Hardware / Performance Defaults ---
DEFAULTS = {
    "CTX_SIZE": 8192,
    "BATCH_SIZE": 1024,
    "THREADS": 4
}

# --- Swarm Settings ---
SWARM_SIZE: int = _external_config.get("swarm_size", 3)
SWARM_ENABLED: bool = _external_config.get("swarm_enabled", False)

# --- UI / Display (Emoji Set) ---
EMOJI = {
    'warning': '⚠️',
    'search': '🔍',
    'success': '✅',
    'error': '❌',
    'thinking': '💭',
    'file': '📄',
    'folder': '📁',
    'database': '💾',
    'web': '🌐',
    'robot': '🤖',
    'sparkles': '✨',
    'check': '✓',
    'info': 'ℹ️',
    'timer': '⏱️',
    'loading': '💡',
    'expert': '🤖',
}
