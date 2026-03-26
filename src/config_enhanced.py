# -*- coding: utf-8 -*-
"""
Enhanced Configuration System for ZEN_RAG
==========================================
Supports multiple LLM sources:
- Local (llama-cpp, Ollama)
- External (OpenAI, Anthropic, HuggingFace)
- Custom APIs
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional
import json


# Platform-aware default model directory (~/AI/Models on macOS so models are always found)
def _default_models_dir() -> str:
    """Default to a 'models' directory inside the project root for portability."""
    return str(Path(__file__).parent / "models")


_DEFAULT_MODELS_DIR = _default_models_dir()

# ============================================================================
# LLM PROVIDERS CONFIGURATION
# ============================================================================


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider (connection settings, not the enum)."""

    name: str
    type: str  # "local", "openai", "anthropic", "ollama", "huggingface", "custom"
    api_url: str
    requires_api_key: bool = False
    requires_model_download: bool = True
    default_model: Optional[str] = None
    description: str = ""

    def get(self, key: str, default=None):
        """Dict-style access for backward compatibility."""
        return getattr(self, key, default)


# Predefined providers
PROVIDERS = {
    "Local (llama-cpp)": ProviderConfig(
        name="Local (llama-cpp)",
        type="local",
        api_url="http://localhost:8001",
        requires_api_key=False,
        requires_model_download=True,
        description="Run GGUF models locally using llama.cpp",
    ),
    "Local (MLX)": ProviderConfig(
        name="Local (MLX)",
        type="local",
        api_url="",
        requires_api_key=False,
        requires_model_download=True,
        description="Qwen3 / MLX on Apple Silicon (mlx-lm). Recommended for Mac.",
    ),
    "Ollama": ProviderConfig(
        name="Ollama",
        type="ollama",
        api_url="http://localhost:11434",
        requires_api_key=False,
        requires_model_download=True,
        description="Run models via Ollama (easiest local option)",
    ),
    "OpenAI": ProviderConfig(
        name="OpenAI",
        type="openai",
        api_url="https://api.openai.com/v1",
        requires_api_key=True,
        requires_model_download=False,
        default_model="gpt-4",
        description="Use OpenAI's GPT models",
    ),
    "Anthropic (Claude)": ProviderConfig(
        name="Anthropic (Claude)",
        type="anthropic",
        api_url="https://api.anthropic.com",
        requires_api_key=True,
        requires_model_download=False,
        default_model="claude-3-opus",
        description="Use Anthropic's Claude models",
    ),
    "HuggingFace": ProviderConfig(
        name="HuggingFace",
        type="huggingface",
        api_url="https://api-inference.huggingface.co/models",
        requires_api_key=True,
        requires_model_download=False,
        description="Use HuggingFace Inference API",
    ),
    "Google (Gemini)": ProviderConfig(
        name="Google (Gemini)",
        type="google",
        api_url="https://generativelanguage.googleapis.com",
        requires_api_key=True,
        requires_model_download=False,
        default_model="gemini-pro",
        description="Use Google's Gemini models",
    ),
    "Cohere": ProviderConfig(
        name="Cohere",
        type="cohere",
        api_url="https://api.cohere.ai",
        requires_api_key=True,
        requires_model_download=False,
        description="Use Cohere's language models",
    ),
    "Custom API": ProviderConfig(
        name="Custom API",
        type="custom",
        api_url="",
        requires_api_key=True,
        requires_model_download=False,
        description="Connect to any OpenAI-compatible API",
    ),
}

# Backward compatibility alias (was LLMProvider, renamed to avoid collision with llm_adapters.LLMProvider enum)
LLMProvider = ProviderConfig

# ============================================================================
# CONFIGURATION
# ============================================================================


class Config:
    """Enhanced configuration for ZEN_RAG."""

    # Project paths
    PROJECT_ROOT = Path(__file__).parent
    MODELS_DIR = Path(os.getenv("MODELS_DIR", _DEFAULT_MODELS_DIR)).expanduser()
    CACHE_DIR = PROJECT_ROOT / "cache"
    LOGS_DIR = PROJECT_ROOT / "logs"
    UPLOADS_DIR = PROJECT_ROOT / "uploads"

    # Create directories if they don't exist
    for dir_path in [CACHE_DIR, LOGS_DIR, UPLOADS_DIR]:
        dir_path.mkdir(exist_ok=True)

    # ========================================================================
    # LLM CONFIGURATION
    # ========================================================================

    # Default provider
    DEFAULT_PROVIDER = "Local (llama-cpp)"
    DEFAULT_MODEL = "tinyllama-1.1b-chat.Q4_K_M.gguf"  # Ultra-small: 1.1B parameters, ~2x faster

    # Provider settings
    PROVIDERS_CONFIG = PROVIDERS

    # ========================================================================
    # LLM PARAMETERS
    # ========================================================================

    # Default inference parameters
    INFERENCE_PARAMS = {
        "temperature": 0.5,  # Conservative for stability
        "top_p": 0.80,
        "top_k": 30,
        "max_tokens": 512,  # BALANCED: enough for coherent answers
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    }

    # Model-specific overrides
    MODEL_OVERRIDES = {
        "gpt-4": {
            "temperature": 0.7,
            "max_tokens": 8000,
        },
        "claude-3-opus": {
            "temperature": 0.7,
            "max_tokens": 4000,
        },
        "gemini-pro": {
            "temperature": 0.7,
            "max_tokens": 2048,
        },
    }

    # ========================================================================
    # CACHE CONFIGURATION
    # ========================================================================

    # Response caching
    CACHE_ENABLED = True
    CACHE_TTL = 3600  # 1 hour in seconds
    MAX_CACHE_SIZE = 100
    CACHE_TYPE = "lru"  # lru, lfu

    # ========================================================================
    # SECURITY CONFIGURATION
    # ========================================================================

    # Rate limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_REQUESTS = 30  # requests
    RATE_LIMIT_WINDOW = 60  # seconds

    # Input validation
    MAX_INPUT_LENGTH = 10000
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".jpg", ".png", ".webp"}

    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
    }

    # ========================================================================
    # RAG CONFIGURATION
    # ========================================================================

    # Vector database (Qdrant)
    QDRANT_URL = "http://localhost:6333"
    QDRANT_COLLECTION = "documents"

    # Embeddings (multilingual model — supports 50+ languages)
    EMBEDDING_MODEL = os.getenv(
        "RAG_EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    # Local paths: when set, load from disk only (no HuggingFace hub). Use for offline/local-only.
    RAG_EMBEDDING_MODEL_PATH = os.getenv("RAG_EMBEDDING_MODEL_PATH", "").strip() or None
    RAG_RERANKER_MODEL_PATH = os.getenv("RAG_RERANKER_MODEL_PATH", "").strip() or None
    RAG_LOCAL_ONLY = os.getenv("RAG_LOCAL_ONLY", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    EMBEDDING_DIM = 384
    BATCH_SIZE = 32

    # RAG search (higher default for accurate counts over Excel/table data)
    TOP_K_RESULTS = 30
    SEMANTIC_WEIGHT = 0.6
    KEYWORD_WEIGHT = 0.4

    # Excel → RAG tables (best practice: limit size for embedding quality and chat performance)
    EXCEL_MAX_ROWS_PER_SHEET = int(os.getenv("RAG_EXCEL_MAX_ROWS", "500"))  # 0 = no cap
    EXCEL_MAX_CHARS_PER_SHEET = int(os.getenv("RAG_EXCEL_MAX_CHARS", "12000"))
    RAG_TABLE_MAX_CHARS = int(os.getenv("RAG_TABLE_MAX_CHARS", "12000"))  # max chars per table chunk in vector

    # Complex query expansion and multi-query retrieval
    RAG_COMPLEX_QUERY_WORD_THRESHOLD = int(os.getenv("RAG_COMPLEX_QUERY_WORD_THRESHOLD", "8"))
    RAG_MULTI_QUERY_ENABLED = os.getenv("RAG_MULTI_QUERY_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )

    # ========================================================================
    # LOGGING
    # ========================================================================

    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = LOGS_DIR / "app.log"

    # ========================================================================
    # API CONFIGURATION
    # ========================================================================

    # HTTP client settings
    API_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    # Streamlit settings
    STREAMLIT_HOST = "localhost"
    STREAMLIT_PORT = 8501
    STREAMLIT_THEME = "light"

    # ========================================================================
    # FEATURE FLAGS
    # ========================================================================

    FEATURES = {
        "voice_input": False,
        "voice_output": False,
        "document_upload": True,
        "web_scraping": True,
        "model_switching": True,
        "batch_processing": False,
        "swarm_mode": False,
    }

    # ========================================================================
    # EXPERIMENTAL FEATURES
    # ========================================================================

    EXPERIMENTAL = {
        "semantic_caching": False,
        "auto_model_selection": False,
        "response_streaming": True,
        "parallel_search": True,
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_provider(provider_name: str) -> Optional[LLMProvider]:
    """Get provider configuration."""
    return PROVIDERS.get(provider_name)


def get_all_providers() -> Dict[str, LLMProvider]:
    """Get all available providers."""
    return PROVIDERS.copy()


def get_local_providers() -> Dict[str, LLMProvider]:
    """Get only local providers."""
    return {name: provider for name, provider in PROVIDERS.items() if provider.type in ["local", "ollama"]}


def get_external_providers() -> Dict[str, LLMProvider]:
    """Get only external providers."""
    return {name: provider for name, provider in PROVIDERS.items() if provider.type not in ["local", "ollama"]}


def save_config(config_dict: Dict) -> bool:
    """Save configuration to file."""
    try:
        config_file = Config.PROJECT_ROOT / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_dict, f, indent=2)
        return True
    except Exception:
        # [X-Ray auto-fix] print(f"Error saving config: {e}")
        return False


def load_config() -> Dict:
    """Load configuration from file."""
    try:
        config_file = Config.PROJECT_ROOT / "config.json"
        if config_file.exists():
            with open(config_file, "r") as f:
                return json.load(f)
    except Exception:
        # [X-Ray auto-fix] print(f"Error loading config: {e}")
        pass
    return {}


# ============================================================================
# ENVIRONMENT-BASED CONFIGURATION
# ============================================================================

# Override config from environment variables
if os.getenv("LLM_PROVIDER"):
    Config.DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER")

if os.getenv("LLM_API_KEY"):
    # Store API key (use with caution)
    API_KEY = os.getenv("LLM_API_KEY")

if os.getenv("LLM_API_URL"):
    # Custom API URL
    Custom = PROVIDERS["Custom API"]
    Custom.api_url = os.getenv("LLM_API_URL")

if os.getenv("CACHE_TTL"):
    Config.CACHE_TTL = int(os.getenv("CACHE_TTL"))

if os.getenv("LOG_LEVEL"):
    Config.LOG_LEVEL = os.getenv("LOG_LEVEL")

# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================


def validate_config() -> bool:
    """Validate configuration."""
    try:
        # Check directories exist
        for dir_path in [Config.MODELS_DIR, Config.CACHE_DIR, Config.LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Check default provider exists
        if Config.DEFAULT_PROVIDER not in PROVIDERS:
            print(f"Warning: Default provider '{Config.DEFAULT_PROVIDER}' not found")
            return False

        # Check model directory for local providers
        provider = get_provider(Config.DEFAULT_PROVIDER)
        if provider and provider.type in ["local", "ollama"]:
            if not Config.MODELS_DIR.exists():
                print(f"Warning: Models directory not found: {Config.MODELS_DIR}")

        return True
    except Exception as e:
        print(f"Config validation error: {e}")
        return False


# Validate on import
validate_config()

# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "Config",
    "PROVIDERS",
    "LLMProvider",
    "get_provider",
    "get_all_providers",
    "get_local_providers",
    "get_external_providers",
    "save_config",
    "load_config",
    "validate_config",
    "LLMConfig",  # Alias for backward compatibility
]

# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================
# Alias LLMConfig to Config for backward compatibility
LLMConfig = Config
