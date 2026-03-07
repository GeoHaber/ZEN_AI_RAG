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
    
    RAG_LABEL = "Local Context"
