# -*- coding: utf-8 -*-
"""
locales/ - Internationalization (i18n) System for ZenAI
Provides centralized text management for localization support.

Usage:
    from locales import get_locale, set_locale
    
    locale = get_locale()
    print(locale.APP_NAME)  # "ZenAI"
    
    set_locale('es')  # Switch to Spanish
"""

from .base import BaseLocale
from .en import EnglishLocale
from .es import SpanishLocale
from .fr import FrenchLocale
from .ro import RomanianLocale
from .hu import HungarianLocale
from .he import HebrewLocale

# Available locales registry
_LOCALES = {
    'en': EnglishLocale,
    'es': SpanishLocale,
    'fr': FrenchLocale,
    'ro': RomanianLocale,
    'hu': HungarianLocale,
    'he': HebrewLocale,
    # 'de': GermanLocale,
    # 'zh': ChineseLocale,
    # 'ja': JapaneseLocale,
}

# Current active locale
_current_locale = None
_current_locale_code = 'en'


def get_locale() -> BaseLocale:
    """Get the current active locale instance."""
    global _current_locale
    if _current_locale is None:
        _current_locale = EnglishLocale()
    return _current_locale


def set_locale(code: str) -> BaseLocale:
    """
    Set the active locale by language code.
    
    Args:
        code: Language code ('en', 'es', 'de', etc.)
        
    Returns:
        The new active locale instance
        
    Raises:
        ValueError: If locale code is not supported
    """
    global _current_locale, _current_locale_code
    
    code = code.lower()
    if code not in _LOCALES:
        available = ', '.join(_LOCALES.keys())
        raise ValueError(f"Locale '{code}' not supported. Available: {available}")
    
    _current_locale = _LOCALES[code]()
    _current_locale_code = code
    return _current_locale


def get_locale_code() -> str:
    """Get the current locale language code."""
    return _current_locale_code


def get_available_locales() -> dict:
    """
    Get dictionary of available locales with their details.
    
    Returns:
        Dict of locale codes to info dicts with 'name' and 'native' keys.
        Example: {'en': {'name': 'English', 'native': 'English'}, ...}
    """
    result = {}
    for code, cls in _LOCALES.items():
        result[code] = {
            'name': cls.LANGUAGE_NAME,
            'native': cls.LANGUAGE_NATIVE,
            'rtl': getattr(cls, 'RTL', False)
        }
    return result


# Shorthand access (for convenience)
L = get_locale  # Usage: L().APP_NAME
