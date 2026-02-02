# -*- coding: utf-8 -*-
"""
settings.py - Legacy Bridge for config_system
Allows old files to 'from settings import ...' without breaking.
"""
from config_system import config, get_settings, is_dark_mode, set_dark_mode, AppConfig

# Re-export exactly what ui_components.py expects
__all__ = ['get_settings', 'set_dark_mode', 'is_dark_mode', 'config', 'AppConfig']
