import pytest
from ui import locales


def test_localization_switching_branding():
    """Verify that switching locales updates strings and maintains ZenAI branding."""
    supported_codes = ["en", "es", "fr", "ro", "hu", "he"]

    for code in supported_codes:
        # Switch locale
        loc = locales.set_locale(code)

        # Verify language code matches
        assert locales.get_locale_code() == code

        # Verify branding consistency across all languages
        # These should NEVER be "ZenAI" or "ZenAI" (in user-facing content)
        assert "ZenAI" in loc.APP_NAME
        assert "ZenAI" in loc.APP_TITLE

        # Check welcome message key exists (we renamed it to WELCOME_ZENAI)
        assert hasattr(loc, "WELCOME_ZENAI")
        assert not hasattr(loc, "WELCOME_ZENA")

        # Check chat placeholder key exists
        assert hasattr(loc, "CHAT_PLACEHOLDER_ZENAI")
        assert not hasattr(loc, "CHAT_PLACEHOLDER_ZENA")


def test_invalid_locale_raises_error():
    """Verify that an unsupported locale code raises ValueError."""
    with pytest.raises(ValueError):
        locales.set_locale("zz_ZZ")


def test_shorthand_access():
    """Verify that L() shorthand works correctly after a switch."""
    locales.set_locale("hu")
    assert locales.L().LANGUAGE_CODE == "hu"

    locales.set_locale("en")
    assert locales.L().LANGUAGE_CODE == "en"


def test_menu_strings_not_empty():
    """Verification that critical UI strings are translated (not empty)."""
    loc = locales.set_locale("ro")
    assert loc.NAV_MODEL_MANAGER
    assert loc.BTN_SEND
    assert loc.CHAT_PLACEHOLDER
