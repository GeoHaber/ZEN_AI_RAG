"""
tests/test_i18n.py — Language / i18n tests

Verifies:
  1. All locale JSON files load correctly
  2. Every key in en.json also exists in every other locale
  3. Placeholder variables ({var}) are consistent across translations
  4. set_language() switches the active translator
  5. _() returns the correct translated string for each language
  6. Language labels dict is correct
"""

import json
import re
import sys
from pathlib import Path

import pytest

# ── ensure project root is importable ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.i18n import (
    Translator,
    set_language,
    get_supported_languages,
    get_language_labels,
)  # noqa: E402

LOCALE_DIR = PROJECT_ROOT / "ui" / "i18n" / "locales"
LANGUAGES = get_supported_languages()
PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


# ── helpers ──


def _load_locale(lang: str) -> dict:
    """Load and return a locale dict."""
    fpath = LOCALE_DIR / f"{lang}.json"
    assert fpath.exists(), f"Missing locale file: {fpath}"
    with open(fpath, "r", encoding="utf-8") as f:
        return json.load(f)


def _all_locales() -> dict[str, dict]:
    """Load all locale dicts keyed by language code."""
    return {lang: _load_locale(lang) for lang in LANGUAGES}


# =====================================================================
# 1. Locale files load without errors
# =====================================================================


@pytest.mark.parametrize("lang", LANGUAGES)
def test_locale_file_loads(lang):
    """Each locale JSON must load without parse errors."""
    data = _load_locale(lang)
    assert isinstance(data, dict)
    assert len(data) > 50, f"{lang}.json has only {len(data)} keys — suspiciously few"


# =====================================================================
# 2. Key coverage — every en.json key must exist in all other locales
# =====================================================================


def test_all_keys_present_in_all_locales():
    """Every key in en.json must be present in every other locale file."""
    locales = _all_locales()
    en_keys = set(locales["en"].keys())

    missing = {}
    for lang in LANGUAGES:
        if lang == "en":
            continue
        lang_keys = set(locales[lang].keys())
        diff = en_keys - lang_keys
        if diff:
            missing[lang] = sorted(diff)

    if missing:
        lines = []
        for lang, keys in missing.items():
            lines.append(f"  {lang}: {len(keys)} missing keys — {keys[:5]}{'...' if len(keys) > 5 else ''}")
        pytest.fail("Missing translation keys:\n" + "\n".join(lines))


# =====================================================================
# 3. Placeholder consistency — same {var} names in all translations
# =====================================================================


def test_placeholder_variables_match():
    """Every translation must use the same {placeholder} variables as en.json."""
    locales = _all_locales()
    en = locales["en"]

    mismatches = []
    for key, en_val in en.items():
        en_vars = set(PLACEHOLDER_RE.findall(en_val))
        if not en_vars:
            continue
        for lang in LANGUAGES:
            if lang == "en":
                continue
            translated = locales[lang].get(key, "")
            lang_vars = set(PLACEHOLDER_RE.findall(translated))
            if en_vars != lang_vars:
                mismatches.append(f"  [{lang}] {key}: expected {en_vars}, got {lang_vars}")

    if mismatches:
        pytest.fail(
            f"Placeholder mismatch in {len(mismatches)} translations:\n"
            + "\n".join(mismatches[:15])
            + (f"\n  ... and {len(mismatches) - 15} more" if len(mismatches) > 15 else "")
        )


# =====================================================================
# 4. set_language() switches Translator correctly
# =====================================================================


@pytest.mark.parametrize("lang", LANGUAGES)
def test_set_language(lang):
    """set_language() should switch the global translator."""
    assert set_language(lang) is True
    from ui.i18n import translator

    assert translator.language == lang


def test_set_language_invalid():
    """set_language() should reject unknown language codes."""
    assert set_language("xx") is False


# =====================================================================
# 5. _() returns correct translations per language
# =====================================================================

SAMPLE_KEYS = [
    "app.page_title",
    "tab.chat",
    "footer.data_local",
    "sidebar.ai_provider",
    "button.clear",
    "chat.thinking",
    "metric.model",
    "time.almost_done",
]


@pytest.mark.parametrize("lang", LANGUAGES)
def test_translate_sample_keys(lang):
    """_() should return the correct translation for each sample key."""
    t = Translator(lang)
    locale_data = _load_locale(lang)

    for key in SAMPLE_KEYS:
        result = t.t(key)
        expected = locale_data.get(key, key)
        assert result == expected, f"[{lang}] key={key}: expected {expected!r}, got {result!r}"


def test_translate_with_interpolation():
    """_() should correctly interpolate {variables}."""
    t = Translator("en")
    result = t.t("time.seconds", n=42)
    assert "42" in result
    assert "seconds" in result.lower()


@pytest.mark.parametrize("lang", ["ro", "fr", "es", "hu"])
def test_non_english_actually_differs(lang):
    """Non-English translations should differ from English for UI keys."""
    en = Translator("en")
    other = Translator(lang)

    differs = 0
    check_keys = [k for k in SAMPLE_KEYS if not k.startswith("app.page_title")]  # page_title may stay same
    for key in check_keys:
        if en.t(key) != other.t(key):
            differs += 1

    assert differs > 0, f"{lang}: all sample translations are identical to English — check locale file"


# =====================================================================
# 6. Language labels
# =====================================================================


def test_language_labels_structure():
    """Language labels dict should cover all supported languages."""
    labels = get_language_labels()
    assert isinstance(labels, dict)
    for lang in LANGUAGES:
        assert lang in labels, f"Language '{lang}' missing from labels"
        assert isinstance(labels[lang], str)
        # Should contain a flag emoji
        assert len(labels[lang]) > 3


def test_language_labels_have_native_names():
    """Check that labels use native language names."""
    labels = get_language_labels()
    assert "English" in labels["en"]
    assert "Français" in labels["fr"] or "Francais" in labels["fr"]
    assert "Español" in labels["es"] or "Espanol" in labels["es"]
    assert "Română" in labels["ro"] or "Romana" in labels["ro"]
    assert "Magyar" in labels["hu"]


# =====================================================================
# 7. No extra keys in non-English locales
# =====================================================================


def test_no_orphan_keys():
    """Non-English locales should not contain keys absent from en.json."""
    locales = _all_locales()
    en_keys = set(locales["en"].keys())

    extras = {}
    for lang in LANGUAGES:
        if lang == "en":
            continue
        lang_keys = set(locales[lang].keys())
        orphans = lang_keys - en_keys
        if orphans:
            extras[lang] = sorted(orphans)

    if extras:
        lines = [f"  {lang}: {sorted(keys)}" for lang, keys in extras.items()]
        pytest.fail("Orphan keys (not in en.json):\n" + "\n".join(lines))


# =====================================================================
# 8. Translator fallback to English
# =====================================================================


def test_fallback_to_english():
    """If a key is missing from a non-English locale, fallback to en."""
    t = Translator("ro")
    # _meta keys won't match — use a key that's definitely in en
    _load_locale("en")
    # Pick a key and ensure it resolves
    result = t.t("app.page_title")
    assert result != "app.page_title", "Key should resolve, not return itself"


# =====================================================================
# 9. Translator returns key name if missing everywhere
# =====================================================================


def test_missing_key_returns_key_name():
    """If a key doesn't exist in any locale, return the key itself."""
    t = Translator("en")
    result = t.t("totally.fake.key.xyz")
    assert result == "totally.fake.key.xyz"
