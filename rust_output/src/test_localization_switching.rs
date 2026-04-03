use anyhow::{Result, Context};

/// Verify that switching locales updates strings and maintains ZenAI branding.
pub fn test_localization_switching_branding() -> () {
    // Verify that switching locales updates strings and maintains ZenAI branding.
    let mut supported_codes = vec!["en".to_string(), "es".to_string(), "fr".to_string(), "ro".to_string(), "hu".to_string(), "he".to_string()];
    for code in supported_codes.iter() {
        let mut loc = locales.set_locale(code);
        assert!(locales.get_locale_code() == code);
        assert!(loc.APP_NAME.contains(&"ZenAI".to_string()));
        assert!(loc.APP_TITLE.contains(&"ZenAI".to_string()));
        assert!(/* hasattr(loc, "WELCOME_ZENAI".to_string()) */ true);
        assert!(!/* hasattr(loc, "WELCOME_ZENA".to_string()) */ true);
        assert!(/* hasattr(loc, "CHAT_PLACEHOLDER_ZENAI".to_string()) */ true);
        assert!(!/* hasattr(loc, "CHAT_PLACEHOLDER_ZENA".to_string()) */ true);
    }
}

/// Verify that an unsupported locale code raises ValueError.
pub fn test_invalid_locale_raises_error() -> () {
    // Verify that an unsupported locale code raises ValueError.
    let _ctx = pytest.raises(ValueError);
    {
        locales.set_locale("zz_ZZ".to_string());
    }
}

/// Verify that L() shorthand works correctly after a switch.
pub fn test_shorthand_access() -> () {
    // Verify that L() shorthand works correctly after a switch.
    locales.set_locale("hu".to_string());
    assert!(locales.L().LANGUAGE_CODE == "hu".to_string());
    locales.set_locale("en".to_string());
    assert!(locales.L().LANGUAGE_CODE == "en".to_string());
}

/// Verification that critical UI strings are translated (not empty).
pub fn test_menu_strings_not_empty() -> () {
    // Verification that critical UI strings are translated (not empty).
    let mut loc = locales.set_locale("ro".to_string());
    assert!(loc.NAV_MODEL_MANAGER);
    assert!(loc.BTN_SEND);
    assert!(loc.CHAT_PLACEHOLDER);
}
