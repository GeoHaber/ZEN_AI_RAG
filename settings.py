# -*- coding: utf-8 -*-
"""
settings.py - Legacy Bridge for config_system
Allows old files to 'from settings import ...' without breaking.
"""

from config_system import config, get_settings, is_dark_mode, set_dark_mode, AppConfig, ExternalLLMConfig

# Aliases for compatibility with tests
ExternalLLMSettings = ExternalLLMConfig


class AppSettings:
    """Wrapper for AppConfig that provides a unified settings interface."""

    def __init__(self):
        self._config = AppConfig()
        self.external_llm = ExternalLLMSettings()

    def __getattr__(self, name):
        return getattr(self._config, name)


# Re-export exactly what ui_components.py expects
__all__ = ["get_settings", "set_dark_mode", "is_dark_mode", "config", "AppConfig", "AppSettings", "ExternalLLMSettings"]
