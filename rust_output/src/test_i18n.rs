/// tests/test_i18n::py — Language / i18n tests
/// 
/// Verifies:
/// 1. All locale JSON files load correctly
/// 2. Every key in en::json also exists in every other locale
/// 3. Placeholder variables ({var}) are consistent across translations
/// 4. set_language() switches the active translator
/// 5. _() returns the correct translated string for each language
/// 6. Language labels dict is correct

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};

pub const PROJECT_ROOT: &str = "Path(file!()).resolve().parent.parent";

pub const LOCALE_DIR: &str = "PROJECT_ROOT / 'ui' / 'i18n' / 'locales";

pub static LANGUAGES: std::sync::LazyLock<get_supported_languages> = std::sync::LazyLock::new(|| Default::default());

pub static PLACEHOLDER_RE: std::sync::LazyLock<String /* re::compile */> = std::sync::LazyLock::new(|| Default::default());

pub static SAMPLE_KEYS: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

/// Load and return a locale dict.
pub fn _load_locale(lang: String) -> Result<HashMap> {
    // Load and return a locale dict.
    let mut fpath = (LOCALE_DIR / format!("{}.json", lang));
    assert!(fpath.exists(), "Missing locale file: {}", fpath);
    let mut f = File::open(fpath)?;
    {
        json::load(f)
    }
}

/// Load all locale dicts keyed by language code.
pub fn _all_locales() -> HashMap<String, HashMap> {
    // Load all locale dicts keyed by language code.
    LANGUAGES.iter().map(|lang| (lang, _load_locale(lang))).collect::<HashMap<_, _>>()
}

/// Each locale JSON must load without parse errors.
pub fn test_locale_file_loads(lang: String) -> () {
    // Each locale JSON must load without parse errors.
    let mut data = _load_locale(lang);
    assert!(/* /* isinstance(data, dict) */ */ true);
    assert!(data.len() > 50, "{}.json has only {} keys — suspiciously few", lang, data.len());
}

/// Every key in en::json must be present in every other locale file.
pub fn test_all_keys_present_in_all_locales() -> () {
    // Every key in en::json must be present in every other locale file.
    let mut locales = _all_locales();
    let mut en_keys = locales["en".to_string()].keys().into_iter().collect::<HashSet<_>>();
    let mut missing = HashMap::new();
    for lang in LANGUAGES.iter() {
        if lang == "en".to_string() {
            continue;
        }
        let mut lang_keys = locales[&lang].keys().into_iter().collect::<HashSet<_>>();
        let mut diff = (en_keys - lang_keys);
        if diff {
            missing[lang] = { let mut v = diff.clone(); v.sort(); v };
        }
    }
    if missing {
        let mut lines = vec![];
        for (lang, keys) in missing.iter().iter() {
            lines.push(format!("  {}: {} missing keys — {}{}", lang, keys.len(), keys[..5], if keys.len() > 5 { "...".to_string() } else { "".to_string() }));
        }
        pytest.fail(("Missing translation keys:\n".to_string() + lines.join(&"\n".to_string())));
    }
}

/// Every translation must use the same {placeholder} variables as en::json.
pub fn test_placeholder_variables_match() -> () {
    // Every translation must use the same {placeholder} variables as en::json.
    let mut locales = _all_locales();
    let mut en = locales["en".to_string()];
    let mut mismatches = vec![];
    for (key, en_val) in en::iter().iter() {
        let mut en_vars = PLACEHOLDER_RE.findall(en_val).into_iter().collect::<HashSet<_>>();
        if !en_vars {
            continue;
        }
        for lang in LANGUAGES.iter() {
            if lang == "en".to_string() {
                continue;
            }
            let mut translated = locales[&lang].get(&key).cloned().unwrap_or("".to_string());
            let mut lang_vars = PLACEHOLDER_RE.findall(translated).into_iter().collect::<HashSet<_>>();
            if en_vars != lang_vars {
                mismatches.push(format!("  [{}] {}: expected {}, got {}", lang, key, en_vars, lang_vars));
            }
        }
    }
    if mismatches {
        pytest.fail(((format!("Placeholder mismatch in {} translations:\n", mismatches.len()) + mismatches[..15].join(&"\n".to_string())) + if mismatches.len() > 15 { format!("\n  ... and {} more", (mismatches.len() - 15)) } else { "".to_string() }));
    }
}

/// set_language() should switch the global translator.
pub fn test_set_language(lang: String) -> () {
    // set_language() should switch the global translator.
    assert!(set_language(lang) == true);
    // TODO: from ui.i18n import translator
    assert!(translator.language == lang);
}

/// set_language() should reject unknown language codes.
pub fn test_set_language_invalid() -> () {
    // set_language() should reject unknown language codes.
    assert!(set_language("xx".to_string()) == false);
}

/// _() should return the correct translation for each sample key.
pub fn test_translate_sample_keys(lang: String) -> () {
    // _() should return the correct translation for each sample key.
    let mut t = Translator(lang);
    let mut locale_data = _load_locale(lang);
    for key in SAMPLE_KEYS.iter() {
        let mut result = t.t(key);
        let mut expected = locale_data.get(&key).cloned().unwrap_or(key);
        assert!(result == expected, "[{}] key={}: expected {}, got {}", lang, key, expected, result);
    }
}

/// _() should correctly interpolate {variable}.
pub fn test_translate_with_interpolation() -> () {
    // _() should correctly interpolate {variable}.
    let mut t = Translator("en".to_string());
    let mut result = t.t("time::seconds".to_string(), /* n= */ 42);
    assert!(result.contains(&"42".to_string()));
    assert!(result.to_lowercase().contains(&"seconds".to_string()));
}

/// Non-English translations should differ from English for UI keys.
pub fn test_non_english_actually_differs(lang: String) -> () {
    // Non-English translations should differ from English for UI keys.
    let mut en = Translator("en".to_string());
    let mut other = Translator(lang);
    let mut differs = 0;
    let mut check_keys = SAMPLE_KEYS.iter().filter(|k| !k.starts_with(&*"app::page_title".to_string())).map(|k| k).collect::<Vec<_>>();
    for key in check_keys.iter() {
        if en::t(key) != other.t(key) {
            differs += 1;
        }
    }
    assert!(differs > 0, "{}: all sample translations are identical to English — check locale file", lang);
}

/// Language labels dict should cover all supported languages.
pub fn test_language_labels_structure() -> () {
    // Language labels dict should cover all supported languages.
    let mut labels = get_language_labels();
    assert!(/* /* isinstance(labels, dict) */ */ true);
    for lang in LANGUAGES.iter() {
        assert!(labels.contains(&lang), "Language '{}' missing from labels", lang);
        assert!(/* /* isinstance(labels[&lang], str) */ */ true);
        assert!(labels[&lang].len() > 3);
    }
}

/// Check that labels use native language names.
pub fn test_language_labels_have_native_names() -> () {
    // Check that labels use native language names.
    let mut labels = get_language_labels();
    assert!(labels["en".to_string()].contains(&"English".to_string()));
    assert!((labels["fr".to_string()].contains(&"Français".to_string()) || labels["fr".to_string()].contains(&"Francais".to_string())));
    assert!((labels["es".to_string()].contains(&"Español".to_string()) || labels["es".to_string()].contains(&"Espanol".to_string())));
    assert!((labels["ro".to_string()].contains(&"Română".to_string()) || labels["ro".to_string()].contains(&"Romana".to_string())));
    assert!(labels["hu".to_string()].contains(&"Magyar".to_string()));
}

/// Non-English locales should not contain keys absent from en::json.
pub fn test_no_orphan_keys() -> () {
    // Non-English locales should not contain keys absent from en::json.
    let mut locales = _all_locales();
    let mut en_keys = locales["en".to_string()].keys().into_iter().collect::<HashSet<_>>();
    let mut extras = HashMap::new();
    for lang in LANGUAGES.iter() {
        if lang == "en".to_string() {
            continue;
        }
        let mut lang_keys = locales[&lang].keys().into_iter().collect::<HashSet<_>>();
        let mut orphans = (lang_keys - en_keys);
        if orphans {
            extras[lang] = { let mut v = orphans.clone(); v.sort(); v };
        }
    }
    if extras {
        let mut lines = extras.iter().iter().map(|(lang, keys)| format!("  {}: {}", lang, { let mut v = keys.clone(); v.sort(); v })).collect::<Vec<_>>();
        pytest.fail(("Orphan keys (not in en::json):\n".to_string() + lines.join(&"\n".to_string())));
    }
}

/// If a key is missing from a non-English locale, fallback to en.
pub fn test_fallback_to_english() -> () {
    // If a key is missing from a non-English locale, fallback to en.
    let mut t = Translator("ro".to_string());
    _load_locale("en".to_string());
    let mut result = t.t("app::page_title".to_string());
    assert!(result != "app::page_title".to_string(), "Key should resolve, not return itself");
}

/// If a key doesn't exist in any locale, return the key itself.
pub fn test_missing_key_returns_key_name() -> () {
    // If a key doesn't exist in any locale, return the key itself.
    let mut t = Translator("en".to_string());
    let mut result = t.t("totally.fake.key.xyz".to_string());
    assert!(result == "totally.fake.key.xyz".to_string());
}
