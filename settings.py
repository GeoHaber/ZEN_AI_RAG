# -*- coding: utf-8 -*-
"""
settings.py - Application Settings Management
Handles loading, saving, and accessing user preferences.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)

# Settings file location
SETTINGS_DIR = Path(__file__).parent
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


@dataclass
class LanguageSettings:
    """Language and localization settings."""
    ui_language: str = "en"  # en, es, fr, ro, hu, he


@dataclass
class AppearanceSettings:
    """Visual appearance settings."""
    dark_mode: bool = True
    font_size: str = "medium"  # small, medium, large
    chat_density: str = "comfortable"  # compact, comfortable, spacious
    show_avatars: bool = True
    animate_messages: bool = True


@dataclass 
class AIModelSettings:
    """AI model configuration."""
    default_model: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    context_window: int = 4096
    top_p: float = 0.9
    repeat_penalty: float = 1.1
    use_cot_swarm: bool = False
    quiet_cot: bool = True


@dataclass
class VoiceSettings:
    """Voice and TTS settings."""
    tts_enabled: bool = True
    voice_speed: float = 1.0  # 0.5 to 2.0
    auto_speak_responses: bool = False
    voice_id: str = "default"
    recording_duration: int = 5  # seconds


@dataclass
class RAGSettings:
    """RAG (Retrieval Augmented Generation) settings."""
    enabled: bool = False
    chunk_size: int = 500
    chunk_overlap: int = 50
    similarity_threshold: float = 0.7
    max_results: int = 5
    auto_index_on_startup: bool = False
    last_source_type: str = "website"  # website, filesystem
    last_website_url: str = ""
    last_directory_path: str = ""


@dataclass
class ChatSettings:
    """Chat interface settings."""
    show_timestamps: bool = False
    auto_scroll: bool = True
    history_days: int = 30
    stream_responses: bool = True
    show_token_count: bool = False
    max_history_messages: int = 100
    save_conversations: bool = True


@dataclass
class SystemSettings:
    """System and backend settings."""
    api_port: int = 8001
    hub_port: int = 8002
    ui_port: int = 8080
    models_directory: str = "_models"
    check_updates_on_startup: bool = True
    auto_start_backend: bool = True
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR


@dataclass
class AppSettings:
    """
    Main settings container holding all setting categories.
    """
    language: LanguageSettings = field(default_factory=LanguageSettings)
    appearance: AppearanceSettings = field(default_factory=AppearanceSettings)
    ai_model: AIModelSettings = field(default_factory=AIModelSettings)
    voice: VoiceSettings = field(default_factory=VoiceSettings)
    rag: RAGSettings = field(default_factory=RAGSettings)
    chat: ChatSettings = field(default_factory=ChatSettings)
    system: SystemSettings = field(default_factory=SystemSettings)
    
    # Metadata
    version: str = "1.0"
    first_run: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppSettings":
        """Create settings from dictionary."""
        settings = cls()
        
        if "language" in data:
            settings.language = LanguageSettings(**data["language"])
        if "appearance" in data:
            settings.appearance = AppearanceSettings(**data["appearance"])
        if "ai_model" in data:
            settings.ai_model = AIModelSettings(**data["ai_model"])
        if "voice" in data:
            settings.voice = VoiceSettings(**data["voice"])
        if "rag" in data:
            settings.rag = RAGSettings(**data["rag"])
        if "chat" in data:
            settings.chat = ChatSettings(**data["chat"])
        if "system" in data:
            settings.system = SystemSettings(**data["system"])
        
        settings.version = data.get("version", "1.0")
        settings.first_run = data.get("first_run", True)
        
        return settings


class SettingsManager:
    """
    Manages application settings with load/save functionality.
    Singleton pattern ensures consistent state across the app.
    """
    
    _instance: Optional["SettingsManager"] = None
    _settings: AppSettings
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = AppSettings()
            cls._instance._load()
        return cls._instance
    
    def _load(self) -> None:
        """Load settings from file."""
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._settings = AppSettings.from_dict(data)
                logger.info(f"Settings loaded from {SETTINGS_FILE}")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                self._settings = AppSettings()
        else:
            logger.info("No settings file found, using defaults")
            self._settings = AppSettings()
    
    def save(self) -> bool:
        """Save settings to file."""
        try:
            self._settings.first_run = False
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._settings.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Settings saved to {SETTINGS_FILE}")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False
    
    def reset(self) -> None:
        """Reset all settings to defaults."""
        self._settings = AppSettings()
        self.save()
    
    @property
    def settings(self) -> AppSettings:
        """Get current settings."""
        return self._settings
    
    # Convenience accessors
    @property
    def language(self) -> LanguageSettings:
        return self._settings.language
    
    @property
    def appearance(self) -> AppearanceSettings:
        return self._settings.appearance
    
    @property
    def ai_model(self) -> AIModelSettings:
        return self._settings.ai_model
    
    @property
    def voice(self) -> VoiceSettings:
        return self._settings.voice
    
    @property
    def rag(self) -> RAGSettings:
        return self._settings.rag
    
    @property
    def chat(self) -> ChatSettings:
        return self._settings.chat
    
    @property
    def system(self) -> SystemSettings:
        return self._settings.system


# Global instance accessor
def get_settings() -> SettingsManager:
    """Get the global settings manager instance."""
    return SettingsManager()


# Quick accessors for common settings
def get_ui_language() -> str:
    """Get current UI language code."""
    return get_settings().language.ui_language


def set_ui_language(code: str) -> None:
    """Set UI language and save."""
    get_settings().language.ui_language = code
    get_settings().save()


def is_dark_mode() -> bool:
    """Check if dark mode is enabled."""
    return get_settings().appearance.dark_mode


def set_dark_mode(enabled: bool) -> None:
    """Set dark mode and save."""
    get_settings().appearance.dark_mode = enabled
    get_settings().save()
