# -*- coding: utf-8 -*-
"""
locales/en.py - English Locale
Default language for ZenAI.
"""

from .base import BaseLocale


class EnglishLocale(BaseLocale):
    """
    English locale - inherits all defaults from BaseLocale.
    BaseLocale is written in English, so minimal overrides needed.
    This class exists for consistency and potential future customization.
    """
    
    LANGUAGE_CODE = "en"
    LANGUAGE_NAME = "English"
    LANGUAGE_NATIVE = "English"
    
    # Any English-specific overrides can go here
    # For example, regional variants:
    # APP_NAME = "ZenAI"  # US English
    # APP_NAME = "ZenAI"  # UK English could be different
