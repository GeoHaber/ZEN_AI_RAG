# -*- coding: utf-8 -*-
"""
config.py - ZenAI Configuration System
Centralized configuration for all application constants
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Set
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class AppConfig:
    """Application configuration with sensible defaults."""
    
    # API Endpoints
    LLM_API_URL: str = "http://127.0.0.1:8001"
    HUB_API_URL: str = "http://127.0.0.1:8002"
    VOICE_API_URL: str = "http://127.0.0.1:8003"
    UI_PORT: int = 8080
    
    # Swarm Settings
    SWARM_SIZE: int = 3
    SWARM_ENABLED: bool = False
    
    # File Upload Security
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: Set[str] = field(default_factory=lambda: {
        '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml',
        '.csv', '.log', '.yaml', '.yml', '.rst', '.c', '.cpp', '.java'
    })
    
    # Audio Settings
    AUDIO_SAMPLE_RATE: int = 16000
    RECORDING_DURATION: int = 5
    
    # RAG Settings
    DEFAULT_MAX_PAGES: int = 50
    DEFAULT_MAX_FILES: int = 1000
    RAG_CACHE_DIR: Path = field(default_factory=lambda: Path("rag_cache"))
    
    # Performance Settings
    STREAM_UPDATE_INTERVAL: float = 0.05  # 50ms - batch UI updates
    MAX_CHAT_MESSAGES: int = 100  # Prevent DOM bloat
    
    # UI Settings
    THEME_PRIMARY: str = '#007bff'
    THEME_SECONDARY: str = '#6c757d'
    THEME_ACCENT: str = '#17a2b8'
    
    @classmethod
    def from_json(cls, path: Path) -> 'AppConfig':
        """Load configuration from JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract relevant fields (ignore zena_mode for now)
            config_data = {
                k: v for k, v in data.items() 
                if k in cls.__dataclass_fields__
            }
            
            logger.info(f"[Config] Loaded from {path}")
            return cls(**config_data)
        
        except FileNotFoundError:
            logger.warning(f"[Config] File not found: {path}, using defaults")
            return cls()
        except Exception as e:
            logger.error(f"[Config] Failed to load {path}: {e}, using defaults")
            return cls()
    
    def to_json(self, path: Path) -> None:
        """Save configuration to JSON file."""
        try:
            # Convert to dict, handling Path objects
            data = {}
            for key, value in self.__dict__.items():
                if isinstance(value, Path):
                    data[key] = str(value)
                elif isinstance(value, set):
                    data[key] = list(value)
                else:
                    data[key] = value
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"[Config] Saved to {path}")
        
        except Exception as e:
            logger.error(f"[Config] Failed to save {path}: {e}")


# Emoji constants (fix encoding issues)
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


# Global config instance
config = AppConfig()


def load_config(config_path: Path = Path("config.json")) -> AppConfig:
    """Load application configuration."""
    global config
    config = AppConfig.from_json(config_path)
    return config
