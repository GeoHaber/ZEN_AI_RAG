# -*- coding: utf-8 -*-
"""
config_system.py - ZenAI Configuration System
Centralized configuration for all application constants
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Set, Dict, Optional
import json
import logging
import os

logger = logging.getLogger(__name__)


# =============================================================================
# Nested Config Dataclasses
# =============================================================================


@dataclass
class EmbeddingConfig:
    """Configuration for embedding models used in RAG."""

    MODELS: Dict[str, str] = field(
        default_factory=lambda: {
            "fast": "all-MiniLM-L6-v2",
            "balanced": "all-mpnet-base-v2",
            "accurate": "BAAI/bge-large-en-v1.5",
        }
    )
    fallback_model: str = "fast"


@dataclass
class RAGConfig:
    """Configuration for the RAG pipeline."""

    embedding_model: str = "balanced"
    use_gpu: bool = False
    chunk_strategy: str = "recursive"
    chunk_size: int = 500
    chunk_overlap: int = 50
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    max_context_chars: int = 12000
    semantic_cache_ttl: int = 3600
    semantic_cache_max: int = 1000
    similarity_threshold: float = 0.95
    contextual_retrieval: bool = True
    mmr_diversity: float = 0.3


# =============================================================================
# Main Application Config
# =============================================================================


@dataclass
class AppConfig:
    """Application configuration with sensible defaults."""

    # --- LLM Engine ---
    LLM_API_URL: str = "http://127.0.0.1:8001"
    llm_port: int = 8001
    HUB_API_URL: str = "http://127.0.0.1:8002"
    VOICE_API_URL: str = "http://127.0.0.1:8003"

    # --- Ports (referenced by server.py, utils.py) ---
    mgmt_port: int = 8002
    ui_port: int = 8080
    voice_port: int = 8003
    UI_PORT: int = 8080  # Legacy alias

    # --- LLM Model Settings (referenced by heart_and_brain.py) ---
    host: str = "127.0.0.1"
    default_model: str = "model.gguf"
    gpu_layers: int = -1  # -1 = auto-detect
    batch_size: int = 512
    context_size: int = 4096
    parallel: int = 1

    # --- Swarm ---
    SWARM_SIZE: int = 3
    SWARM_ENABLED: bool = False

    # --- File Handling ---
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: Set[str] = field(
        default_factory=lambda: {
            ".txt",
            ".md",
            ".py",
            ".js",
            ".html",
            ".css",
            ".json",
            ".xml",
            ".csv",
            ".log",
            ".yaml",
            ".yml",
            ".rst",
            ".c",
            ".cpp",
            ".java",
        }
    )

    # --- Audio ---
    AUDIO_SAMPLE_RATE: int = 16000
    RECORDING_DURATION: int = 5

    # --- Scraping ---
    DEFAULT_MAX_PAGES: int = 50
    DEFAULT_MAX_FILES: int = 1000

    # --- RAG ---
    RAG_CACHE_DIR: Path = field(default_factory=lambda: Path("rag_cache"))
    rag: RAGConfig = field(default_factory=RAGConfig)
    embedding_config: EmbeddingConfig = field(default_factory=EmbeddingConfig)

    # --- UI ---
    STREAM_UPDATE_INTERVAL: float = 0.05  # 50ms - batch UI updates
    MAX_CHAT_MESSAGES: int = 100  # Prevent DOM bloat
    THEME_PRIMARY: str = "#007bff"
    THEME_SECONDARY: str = "#6c757d"
    THEME_ACCENT: str = "#17a2b8"

    # --- Workers ---
    RAG_MAX_WORKERS: int = 8
    TTS_MAX_WORKERS: int = 4
    GENERIC_MAX_WORKERS: int = 4

    # --- Paths (env-configurable for portability) ---
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent)
    BIN_DIR: Path = field(
        default_factory=lambda: Path(
            os.environ.get("ZENAI_BIN_DIR", str(Path(__file__).parent / "_bin"))
        )
    )
    MODEL_DIR: Path = field(
        default_factory=lambda: Path(
            os.environ.get("ZENAI_MODEL_DIR", str(Path(__file__).parent / "models"))
        )
    )

    def get_api_url(self) -> str:
        """Return the full LLM chat completions endpoint."""
        return f"{self.LLM_API_URL}/v1/chat/completions"

    @classmethod
    def from_json(cls, path: Path) -> "AppConfig":
        """From json."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle nested configs
            rag_data = data.pop("rag", None)
            emb_data = data.pop("embedding_config", None)

            # Build case-insensitive field lookup (json may use model_dir, code uses MODEL_DIR)
            _field_map = {k.lower(): k for k in cls.__dataclass_fields__}
            config_data = {}
            for k, v in data.items():
                canon = _field_map.get(k.lower()) or _field_map.get(k)
                if canon:
                    config_data[canon] = v

            # Convert string paths to Path objects for known Path fields
            # Relative paths are resolved against the project root
            _project_root = Path(__file__).parent
            _path_fields = {"BASE_DIR", "BIN_DIR", "MODEL_DIR", "RAG_CACHE_DIR"}
            for pf in _path_fields:
                if pf in config_data and isinstance(config_data[pf], str):
                    p = Path(config_data[pf])
                    if not p.is_absolute():
                        p = _project_root / p
                    config_data[pf] = p

            if rag_data and isinstance(rag_data, dict):
                config_data["rag"] = RAGConfig(
                    **{k: v for k, v in rag_data.items() if k in RAGConfig.__dataclass_fields__}
                )
            if emb_data and isinstance(emb_data, dict):
                config_data["embedding_config"] = EmbeddingConfig(
                    **{k: v for k, v in emb_data.items() if k in EmbeddingConfig.__dataclass_fields__}
                )

            logger.info(f"[Config] Loaded from {path}")
            return cls(**config_data)
        except FileNotFoundError:
            logger.warning(f"[Config] File not found: {path}, using defaults")
            return cls()
        except Exception as e:
            logger.error(f"[Config] Failed to load {path}: {e}, using defaults")
            return cls()

    def to_json(self, path: Path) -> None:
        """To json."""
        try:
            data = {}
            for key, value in self.__dict__.items():
                if isinstance(value, Path):
                    data[key] = str(value)
                elif isinstance(value, set):
                    data[key] = list(value)
                elif isinstance(value, (RAGConfig, EmbeddingConfig)):
                    # Serialize nested dataclasses
                    nested = {}
                    for nk, nv in value.__dict__.items():
                        nested[nk] = nv
                    data[key] = nested
                else:
                    data[key] = value
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"[Config] Saved to {path}")
        except Exception as e:
            logger.error(f"[Config] Failed to save {path}: {e}")


EMOJI = {
    "warning": "⚠️",
    "search": "🔍",
    "success": "✅",
    "error": "❌",
    "thinking": "💭",
    "file": "📄",
    "folder": "📁",
    "database": "💾",
    "web": "🌐",
    "robot": "🤖",
    "sparkles": "✨",
    "check": "✓",
    "info": "ℹ️",
    "timer": "⏱️",
    "loading": "💡",
    "expert": "🤖",
    "rocket": "🚀",
    "hardware": "🔧",
    "recovery": "🔄",
}

# ---------------------------------------------------------------------------
#  External LLM provider config (used by settings.py and UI)
# ---------------------------------------------------------------------------

@dataclass
class ExternalLLMConfig:
    """Configuration for external LLM providers (Anthropic, Google, xAI)."""
    enabled: bool = False
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    google_api_key: str = ""
    google_model: str = "gemini-pro"
    xai_api_key: str = ""
    xai_model: str = "grok-beta"
    use_consensus: bool = False
    cost_tracking_enabled: bool = False
    budget_limit: float = 50.0


# ---------------------------------------------------------------------------
#  Singleton config and helpers
# ---------------------------------------------------------------------------

config = AppConfig()

_SETTINGS_PATH = Path(__file__).parent / "data" / "user_settings.json"


def load_config(config_path: Path = Path("config.json")) -> AppConfig:
    global config
    config = AppConfig.from_json(config_path)
    return config


def get_settings() -> AppConfig:
    """Return the current app config (alias used by UI code)."""
    return config


def is_dark_mode() -> bool:
    """Read dark_mode preference from user_settings.json."""
    try:
        if _SETTINGS_PATH.exists():
            data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
            return bool(data.get("dark_mode", False))
    except Exception:
        pass
    return False


def set_dark_mode(value: bool) -> None:
    """Persist dark_mode preference to user_settings.json."""
    try:
        _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if _SETTINGS_PATH.exists():
            data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        data["dark_mode"] = value
        _SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"[Config] Failed to save dark_mode: {e}")


# ---------------------------------------------------------------------------
#  Path validation & interactive directory picker
# ---------------------------------------------------------------------------

def _pick_directory(prompt_msg: str) -> Optional[Path]:
    """Ask the user to pick a directory.

    Tries tkinter (GUI) first, falls back to console input.
    Returns None if the user cancels.
    """
    # Try GUI picker
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        chosen = filedialog.askdirectory(title=prompt_msg)
        root.destroy()
        if chosen:
            return Path(chosen)
        return None
    except Exception:
        pass  # No display / tkinter unavailable

    # Fallback: console prompt
    try:
        print(f"\n{prompt_msg}")
        raw = input("Enter full path (or press Enter to skip): ").strip()
        if raw:
            p = Path(raw)
            if p.is_dir():
                return p
            print(f"  Directory not found: {p}")
    except (EOFError, KeyboardInterrupt):
        pass
    return None


def validate_paths(cfg: AppConfig, config_path: Path = Path("config.json")) -> AppConfig:
    """Check that critical directories exist; prompt user to pick if not.

    Persists any user-chosen paths back into *config_path* so the picker
    only appears once.
    """
    changed = False

    # --- MODEL_DIR ---
    if not cfg.MODEL_DIR.is_dir():
        logger.warning(f"[Config] MODEL_DIR not found: {cfg.MODEL_DIR}")
        picked = _pick_directory(
            f"Models directory not found ({cfg.MODEL_DIR}).\n"
            "Please select the folder where your .gguf model files are stored."
        )
        if picked and picked.is_dir():
            cfg.MODEL_DIR = picked
            changed = True
        else:
            # Create a local models/ folder as last resort
            local_models = cfg.BASE_DIR / "models"
            local_models.mkdir(parents=True, exist_ok=True)
            cfg.MODEL_DIR = local_models
            changed = True
            logger.info(f"[Config] Created local models dir: {local_models}")

    # --- BIN_DIR ---
    if not cfg.BIN_DIR.is_dir():
        logger.warning(f"[Config] BIN_DIR not found: {cfg.BIN_DIR}")
        picked = _pick_directory(
            f"llama.cpp binaries directory not found ({cfg.BIN_DIR}).\n"
            "Please select the folder containing llama-server(.exe)."
        )
        if picked and picked.is_dir():
            cfg.BIN_DIR = picked
            changed = True
        else:
            # Create the default _bin/ so downstream code doesn't crash
            local_bin = cfg.BASE_DIR / "_bin"
            local_bin.mkdir(parents=True, exist_ok=True)
            cfg.BIN_DIR = local_bin
            changed = True
            logger.info(f"[Config] Created local _bin dir: {local_bin}")

    # Persist changes so the picker doesn't reappear
    if changed:
        try:
            data: dict = {}
            if config_path.exists():
                data = json.loads(config_path.read_text(encoding="utf-8"))
            data["model_dir"] = str(cfg.MODEL_DIR)
            data["bin_dir"] = str(cfg.BIN_DIR)
            config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"[Config] Saved updated paths to {config_path}")
        except Exception as e:
            logger.warning(f"[Config] Could not persist path changes: {e}")

    return cfg
