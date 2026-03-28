"""
Configuration System - Backwards Compatibility Layer
=====================================================
Unifies access to config_enhanced.py for all modules.

IMPORTANT: config_enhanced.py is now the SINGLE SOURCE OF TRUTH.
This module provides compatibility for modules using config_system.py imports.

Usage:
    from config_system import config, EMOJI
    config.MODEL_DIR        # Maps to Config.MODELS_DIR
    config.mgmt_port        # Backend port
    EMOJI['success']        # For status messages
"""

from config_enhanced import Config

# ============================================================================
# EMOJI CONSTANTS - For user-friendly output
# ============================================================================
EMOJI = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "loading": "⏳",
    "search": "🔍",
    "rocket": "🚀",
    "gear": "⚙️",
    "database": "🗄️",
    "network": "🌐",
}


class ConfigAdapter:
    """Adapter to provide zena_mode-compatible interface while using config_enhanced.Config."""

    def get(self, key: str, default=None):
        """Dict-style access for compatibility (e.g. config.get('MAX_FILE_SIZE', 10*1024*1024))."""
        return getattr(self, key, getattr(Config, key, default))

    # Map config_enhanced attributes to legacy names
    @property
    def BASE_DIR(self):
        return Config.PROJECT_ROOT

    @property
    def BIN_DIR(self):
        return Config.PROJECT_ROOT / "_bin"

    @property
    def MODEL_DIR(self):
        """Alias for Config.MODELS_DIR - use this consistently."""
        return Config.MODELS_DIR

    @property
    def MODELS_DIR(self):
        """Direct access to Config.MODELS_DIR."""
        return Config.MODELS_DIR

    @property
    def default_model(self):
        return Config.DEFAULT_MODEL

    # Backend server ports
    mgmt_port = 8002
    llm_port = 8001
    ui_port = 8501
    voice_port = 8003
    host = "localhost"

    # Runtime config
    threads = 4
    gpu_layers = 33
    context_size = 4096
    batch_size = 512
    ubatch_size = 512

    # RAG/Embedding config
    @property
    def rag(self):
        class RAGConfig:
            embedding_model = Config.EMBEDDING_MODEL
            embedding_model_path = getattr(Config, "RAG_EMBEDDING_MODEL_PATH", None)
            reranker_model_path = getattr(Config, "RAG_RERANKER_MODEL_PATH", None)
            local_only = getattr(Config, "RAG_LOCAL_ONLY", False)
            use_gpu = True
            chunk_strategy = "recursive"
            reranker_model = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
            # Excel → vector tables (performance)
            excel_max_rows_per_sheet = getattr(Config, "EXCEL_MAX_ROWS_PER_SHEET", 500)
            excel_max_chars_per_sheet = getattr(Config, "EXCEL_MAX_CHARS_PER_SHEET", 12000)
            rag_table_max_chars = getattr(Config, "RAG_TABLE_MAX_CHARS", 12000)
            # Complex query expansion and multi-query
            complex_query_word_threshold = getattr(Config, "RAG_COMPLEX_QUERY_WORD_THRESHOLD", 8)
            multi_query_enabled = getattr(Config, "RAG_MULTI_QUERY_ENABLED", True)

        return RAGConfig()

    @property
    def embedding_config(self):
        class EmbeddingConfig:
            MODELS = {
                "balanced": Config.EMBEDDING_MODEL,
                "fast": "paraphrase-multilingual-MiniLM-L12-v2",
                "quality": "BAAI/bge-m3",
            }
            fallback_model = "fast"

        return EmbeddingConfig()


# Singleton instance
config = ConfigAdapter()

# For convenience, also export Config directly
__all__ = ["config", "Config", "EMOJI"]
