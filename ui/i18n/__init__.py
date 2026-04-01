"""
Internationalization (i18n) module - Support for multiple languages.

Integrates with Streamlit session state so the active language persists
across reruns and can be changed via a UI selector.
"""

import json
import os
from pathlib import Path
from typing import Dict


# Language display names (native) — used by the UI selector
LANGUAGE_LABELS = {
    "en": "🇬🇧 English",
    "fr": "🇫🇷 Français",
    "es": "🇪🇸 Español",
    "ro": "🇷🇴 Română",
    "hu": "🇭🇺 Magyar",
}


class Translator:
    """
    Simple but effective i18n handler using JSON locale files.

    Supports string interpolation and fallback to English.
    """

    SUPPORTED_LANGUAGES = list(LANGUAGE_LABELS.keys())

    def __init__(self, language: str = "en"):
        """
        Initialize translator for a language.

        Args:
            language: Language code (en, fr, es, ro, hu)
        """
        if language not in self.SUPPORTED_LANGUAGES:
            print(f"⚠️ Language '{language}' not supported. Using English.")
            language = "en"

        self.language = language
        self.translations: Dict = {}
        self._fallback_en: Dict = {}
        self._load_locale(language)

        if language != "en":
            self._load_locale("en", fallback=True)

    def _load_locale(self, lang: str, fallback: bool = False) -> bool:
        """
        Load translation dictionary from JSON file.

        Args:
            lang: Language code
            fallback: If True, load as fallback

        Returns:
            True if loaded successfully
        """
        locale_dir = Path(__file__).parent / "locales"
        locale_file = locale_dir / f"{lang}.json"

        if not locale_file.exists():
            if not fallback:
                print(f"❌ Locale file not found: {locale_file}")
                pass
            return False

        try:
            with open(locale_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if fallback:
                self._fallback_en = data
            else:
                self.translations = data

            return True
        except Exception:
            print(f"❌ Error loading locale: {e}")
            return False

    def t(self, key: str, **kwargs) -> str:
        """
        Translate a key, with optional interpolation.

        Args:
            key: Translation key (e.g., "app.title")
            **kwargs: Format variables for interpolation

        Returns:
            Translated string, or key itself if not found
        """
        # Try current language first
        text = self.translations.get(key)

        # Fall back to English if not found
        if text is None and self.language != "en":
            text = self._fallback_en.get(key)

        # Fall back to key name if still not found
        if text is None:
            text = key

        # Interpolate variables
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                print(f"⚠️ Missing interpolation key: {e}")
                pass
        return text


# Global translator instance, initialized from environment
_language = os.getenv("APP_LANGUAGE", "en")
translator = Translator(_language)


def _(key: str, **kwargs) -> str:
    """
    Shorthand for translator.t().

    Usage:
        from ui.i18n import _
        message = _("app.title")
        error = _("rag.upload_error", error="File too large")
    """
    return translator.t(key, **kwargs)


def set_language(language: str) -> bool:
    """
    Change the active language at runtime.

    Args:
        language: Language code

    Returns:
        True if language change was successful
    """
    global translator

    if language not in Translator.SUPPORTED_LANGUAGES:
        print(f"❌ Language not supported: {language}")
        return False

    translator = Translator(language)
    return True


def get_supported_languages() -> list:
    """Get list of supported language codes."""
    return Translator.SUPPORTED_LANGUAGES


def get_language_labels() -> dict:
    """Get mapping of language code -> native display label with flag."""
    return dict(LANGUAGE_LABELS)
