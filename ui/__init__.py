# -*- coding: utf-8 -*-
"""
ui/ - UI Module for ZenAI
Centralized theme, styles, and reusable components.

Usage:
    from ui import Theme, Styles, Icons
    from ui.settings_dialog import create_settings_dialog
    from ui.modern_theme import ModernTheme  # NEW: Modern Claude-inspired theme
"""

from .theme import Theme, Colors, Typography, Spacing
from .styles import Styles
from .icons import Icons
from .formatters import Formatters
from .modern_theme import ModernTheme, MODERN_CSS

__all__ = [
    'Theme',
    'Colors',
    'Typography',
    'Spacing',
    'Styles',
    'Icons',
    'Formatters',
    'ModernTheme',
    'MODERN_CSS',
]
