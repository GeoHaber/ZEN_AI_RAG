"""
Centralized Configuration for ZEN_RAG
======================================
This module delegates to config_enhanced.py which is the SINGLE SOURCE OF TRUTH.

All constants, paths, helper functions, and the Config class are re-exported from
config_enhanced so that ``from Core.config import ...`` continues to work everywhere.

Priority Order (highest to lowest):
  1. Environment variables (overrides applied in config_enhanced.py)
  2. config_enhanced.py values
  3. Hardcoded defaults in config_enhanced.py
"""

import os

# Re-export everything from the canonical config module
from config_enhanced import (  # noqa: F401
    Config,
    PROVIDERS,
    LLMProvider,
    LLMConfig,
    ProviderConfig,
    get_provider,
    get_all_providers,
    get_local_providers,
    get_external_providers,
    save_config,
    load_config,
    validate_config,
)

# ---------------------------------------------------------------------------
# Convenience aliases so existing ``from Core.config import X`` still works.
# All values come from the Config class defined in config_enhanced.py.
# ---------------------------------------------------------------------------

PROJECT_ROOT = Config.PROJECT_ROOT
DEFAULT_MODELS_DIR = Config.MODELS_DIR  # legacy name used in some modules
MODELS_DIR = Config.MODELS_DIR
CACHE_DIR = Config.CACHE_DIR
LOGS_DIR = Config.LOGS_DIR
UPLOADS_DIR = Config.UPLOADS_DIR

# Extra dir that only existed here — create it lazily
RAG_STORAGE_DIR = PROJECT_ROOT / "rag_storage"
RAG_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PROVIDER = Config.DEFAULT_PROVIDER
DEFAULT_MODEL = Config.DEFAULT_MODEL
INFERENCE_PARAMS = Config.INFERENCE_PARAMS
MODEL_OVERRIDES = Config.MODEL_OVERRIDES

# Llama.cpp server settings (env-overridable)
DEFAULT_LLAMA_PORT = int(os.getenv("LLAMA_PORT", "8001"))
MANAGEMENT_PORT = int(os.getenv("MGMT_PORT", "8002"))
LLAMA_STARTUP_TIMEOUT = int(os.getenv("LLAMA_STARTUP_TIMEOUT", "30"))
LLAMA_SHUTDOWN_TIMEOUT = int(os.getenv("LLAMA_SHUTDOWN_TIMEOUT", "5"))
GPU_LAYERS = int(os.getenv("GPU_LAYERS", "33"))
CONTEXT_SIZE = int(os.getenv("CONTEXT_SIZE", "4096"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "512"))

# Caching
STATUS_CACHE_TTL = float(os.getenv("STATUS_CACHE_TTL", "2.0"))
RESPONSE_CACHE_TTL = Config.CACHE_TTL
MAX_CACHE_SIZE = Config.MAX_CACHE_SIZE
CACHE_TYPE = Config.CACHE_TYPE

# RAG
QDRANT_URL = Config.QDRANT_URL
QDRANT_COLLECTION = Config.QDRANT_COLLECTION
EMBEDDING_MODEL = Config.EMBEDDING_MODEL
EMBEDDING_DIM = Config.EMBEDDING_DIM
TOP_K_RESULTS = Config.TOP_K_RESULTS
SEMANTIC_WEIGHT = Config.SEMANTIC_WEIGHT
KEYWORD_WEIGHT = Config.KEYWORD_WEIGHT

# Security
RATE_LIMIT_ENABLED = Config.RATE_LIMIT_ENABLED
RATE_LIMIT_REQUESTS = Config.RATE_LIMIT_REQUESTS
RATE_LIMIT_WINDOW = Config.RATE_LIMIT_WINDOW
MAX_INPUT_LENGTH = Config.MAX_INPUT_LENGTH
MAX_FILE_SIZE = Config.MAX_FILE_SIZE
ALLOWED_EXTENSIONS = Config.ALLOWED_EXTENSIONS

# Logging
LOG_LEVEL = Config.LOG_LEVEL
LOG_FORMAT = Config.LOG_FORMAT
LOG_FILE = Config.LOG_FILE

# API / Network
API_TIMEOUT = Config.API_TIMEOUT
MAX_RETRIES = Config.MAX_RETRIES
RETRY_DELAY = Config.RETRY_DELAY
STREAMLIT_HOST = Config.STREAMLIT_HOST
STREAMLIT_PORT = Config.STREAMLIT_PORT
STREAMLIT_THEME = Config.STREAMLIT_THEME

# Feature flags
FEATURES = Config.FEATURES

# ---------------------------------------------------------------------------
# Helper functions (delegate to config_enhanced versions)
# ---------------------------------------------------------------------------


def get_models_dir():
    """Get the models directory, creating if needed."""
    Config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return Config.MODELS_DIR


def get_cloud_providers():
    """Get only cloud/external providers (require API keys)."""
    return get_external_providers()
