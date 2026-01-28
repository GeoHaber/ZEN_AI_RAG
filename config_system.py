# -*- coding: utf-8 -*-
"""
config_system.py - ZenAI Unified Configuration System
=====================================================
Centralized configuration for constants, user settings, and hardware defaults.
Strictly follows zena_master_spec.md.
"""
import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Set, Optional, Any

logger = logging.getLogger("ZenAIConfig")

# --- Discovery Logic ---
BASE_DIR: Path = Path(__file__).parent.resolve()
CONFIG_JSON: Path = BASE_DIR / "config.json"
SETTINGS_JSON: Path = BASE_DIR / "settings.json"

@dataclass
class LanguageConfig:
    ui_language: str = "en"  # en, ro

@dataclass
class AppearanceConfig:
    dark_mode: bool = False
    font_size: str = "medium"
    chat_density: str = "comfortable"
    show_avatars: bool = True
    animate_messages: bool = True

@dataclass
class AIConfig:
    default_model: str = "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
    temperature: float = 0.7
    context_window: int = 8192
    max_tokens: int = 2048
    use_cot_swarm: bool = False
    quiet_cot: bool = False

@dataclass
class ExternalLLMConfig:
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

@dataclass
class VoiceConfig:
    tts_enabled: bool = False
    voice_speed: float = 1.0
    auto_speak_responses: bool = False
    recording_duration: int = 10

@dataclass
class RAGConfig:
    enabled: bool = True
    chunk_size: int = 500
    similarity_threshold: float = 0.5
    max_results: int = 5
    auto_index_on_startup: bool = True

@dataclass
class ChatConfig:
    show_timestamps: bool = True
    auto_scroll: bool = True
    stream_responses: bool = True
    show_token_count: bool = True
    save_conversations: bool = True
    history_days: int = 30

@dataclass
class SystemConfig:
    api_port: int = 8001
    models_directory: str = "AI_Models"
    check_updates_on_startup: bool = True
    auto_start_backend: bool = True
    log_level: str = "INFO"

@dataclass
class AppConfig:
    """Unified application configuration."""
    
    # 1. Directories (Auto-Discovery)
    bin_dir: str = "_bin"
    model_dir: str = "AI_Models"
    central_model_dir: str = "C:/AI/Models"
    log_file: str = "nebula_debug.log"
    rag_cache_dir: str = "rag_cache"
    
    # 2. Networking & Ports
    host: str = "127.0.0.1"
    llm_port: int = 8001
    mgmt_port: int = 8002
    ui_port: int = 8080
    voice_port: int = 8003
    
    # 3. Security (Spec Mandated)
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB HARD LIMIT
    ALLOWED_EXTENSIONS: list[str] = field(default_factory=lambda: [
        '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml',
        '.csv', '.log', '.yaml', '.yml', '.rst', '.c', '.cpp', '.java', '.pdf'
    ])
    
    # 4. LLM & Performance Defaults
    default_model: str = "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
    context_size: int = 8192
    batch_size: int = 512
    ubatch_size: int = 512
    threads: int = 4
    gpu_layers: int = 0
    temperature: float = 0.7
    
    # 5. Feature Flags
    zena_mode_enabled: bool = False
    swarm_enabled: bool = False
    voice_enabled: bool = True
    auto_update_enabled: bool = True
    
    # 6. UI Preferences & Nested Configs
    dark_mode: bool = False
    language: LanguageConfig = field(default_factory=LanguageConfig)
    appearance: AppearanceConfig = field(default_factory=AppearanceConfig)
    ai_model: AIConfig = field(default_factory=AIConfig)
    external_llm: ExternalLLMConfig = field(default_factory=ExternalLLMConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    chat: ChatConfig = field(default_factory=ChatConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    
    MAX_CHAT_MESSAGES: int = 100
    
    # 7. Integration Tokens
    telegram_token: str = ""
    telegram_whitelist: list = field(default_factory=list)
    
    def __post_init__(self):
        """Path resolution and cleanup."""
        self.BASE_DIR = BASE_DIR
        self.BIN_DIR = BASE_DIR / self.bin_dir
        # Unified Model Path resolution
        m_path = Path(self.model_dir)
        if m_path.is_absolute():
            self.MODEL_DIR = m_path
        else:
            self.MODEL_DIR = BASE_DIR / self.model_dir
            
        # Central Storage Fallback (Higher Priority if local is empty)
        central_store = Path(self.central_model_dir)
        if central_store.exists():
             # If local directory doesn't exist or is empty, use central store
             if not self.MODEL_DIR.exists() or not list(self.MODEL_DIR.glob("*.gguf")):
                 self.MODEL_DIR = central_store
                 logger.info(f"[Config] Redirected MODEL_DIR to store: {self.MODEL_DIR}")
            
    def get(self, key: str, default: Any = None) -> Any:
        """Legacy dictionary-like get for backward compatibility."""
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        """Legacy dictionary-like access."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def save(self):
        """Save settings to settings.json (for user preferences)."""
        try:
            data = asdict(self)
            with open(SETTINGS_JSON, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Settings saved to {SETTINGS_JSON}")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    def reset(self):
        """Reset settings to default."""
        default = AppConfig()
        for field in self.__dataclass_fields__:
            setattr(self, field, getattr(default, field))
        self.save()
        logger.info("Settings reset to defaults")

    @classmethod
    def load(cls) -> 'AppConfig':
        """Load config with priority: config.json > settings.json > defaults."""
        merged_data = {}
        
        # Load from config.json (Installer/System-level)
        if CONFIG_JSON.exists():
            try:
                with open(CONFIG_JSON, 'r') as f:
                    merged_data.update(json.load(f))
            except Exception as e:
                logger.error(f"Error reading config.json: {e}")

        # Load from settings.json (User preferences)
        if SETTINGS_JSON.exists():
            try:
                with open(SETTINGS_JSON, 'r') as f:
                    merged_data.update(json.load(f))
            except Exception as e:
                logger.error(f"Error reading settings.json: {e}")

        # Helper to convert dicts to dataclasses
        config_inst = cls()
        
        def safe_instantiate(dc_cls, data_dict):
            # Only use fields that exist in the dataclass
            valid_fields = {k: v for k, v in data_dict.items() if k in dc_cls.__dataclass_fields__}
            return dc_cls(**valid_fields)

        for k, v in merged_data.items():
            if k in cls.__dataclass_fields__:
                # Support nested dataclasses
                field_type = cls.__dataclass_fields__[k].type
                if isinstance(v, dict) and hasattr(field_type, "__dataclass_fields__"):
                     setattr(config_inst, k, safe_instantiate(field_type, v))
                else:
                    setattr(config_inst, k, v)
        return config_inst

# --- Global Accessors ---
config = AppConfig.load()

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
}

# Legacy Compatibility Accessors (to prevent breaking UI immediately)
def get_settings(): return config
def is_dark_mode(): return config.dark_mode
def set_dark_mode(enabled): 
    config.dark_mode = enabled
    config.save()
