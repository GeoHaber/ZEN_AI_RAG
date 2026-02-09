# -*- coding: utf-8 -*-
"""
config_system.py - ZenAI Configuration System
Centralized configuration for all application constants
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Set, Dict
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Nested Config Dataclasses
# =============================================================================

@dataclass
class EmbeddingConfig:
    """Configuration for embedding models used in RAG."""
    MODELS: Dict[str, str] = field(default_factory=lambda: {
        "fast": "all-MiniLM-L6-v2",
        "balanced": "all-mpnet-base-v2",
        "accurate": "BAAI/bge-large-en-v1.5"
    })
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
    gpu_layers: int = -1        # -1 = auto-detect
    batch_size: int = 512
    context_size: int = 4096
    parallel: int = 1

    # --- Swarm ---
    SWARM_SIZE: int = 3
    SWARM_ENABLED: bool = False

    # --- File Handling ---
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: Set[str] = field(default_factory=lambda: {
        '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml',
        '.csv', '.log', '.yaml', '.yml', '.rst', '.c', '.cpp', '.java'
    })

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
    THEME_PRIMARY: str = '#007bff'
    THEME_SECONDARY: str = '#6c757d'
    THEME_ACCENT: str = '#17a2b8'

    # --- Workers ---
    RAG_MAX_WORKERS: int = 8
    TTS_MAX_WORKERS: int = 4
    GENERIC_MAX_WORKERS: int = 4

    # --- Paths ---
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent)
    BIN_DIR: Path = field(default_factory=lambda: Path(__file__).parent / '_bin')
    MODEL_DIR: Path = field(default_factory=lambda: Path("C:/AI/Models"))

    @classmethod
    def from_json(cls, path: Path) -> 'AppConfig':
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle nested configs
            rag_data = data.pop('rag', None)
            emb_data = data.pop('embedding_config', None)

            config_data = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}

            if rag_data and isinstance(rag_data, dict):
                config_data['rag'] = RAGConfig(**{
                    k: v for k, v in rag_data.items()
                    if k in RAGConfig.__dataclass_fields__
                })
            if emb_data and isinstance(emb_data, dict):
                config_data['embedding_config'] = EmbeddingConfig(**{
                    k: v for k, v in emb_data.items()
                    if k in EmbeddingConfig.__dataclass_fields__
                })

            logger.info(f"[Config] Loaded from {path}")
            return cls(**config_data)
        except FileNotFoundError:
            logger.warning(f"[Config] File not found: {path}, using defaults")
            return cls()
        except Exception as e:
            logger.error(f"[Config] Failed to load {path}: {e}, using defaults")
            return cls()

    def to_json(self, path: Path) -> None:
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
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"[Config] Saved to {path}")
        except Exception as e:
            logger.error(f"[Config] Failed to save {path}: {e}")


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
    'rocket': '🚀',
    'hardware': '🔧',
    'recovery': '🔄',
}

config = AppConfig()

def load_config(config_path: Path = Path("config.json")) -> AppConfig:
    global config
    config = AppConfig.from_json(config_path)
    return config
