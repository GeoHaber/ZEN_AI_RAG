/// ui_flet/theme::py — Dynamic Light/Dark Theme Engine
/// ====================================================
/// 
/// Uses the TH metaclass pattern from RAG_RAT for zero-parens colour access::
/// 
/// TH.accent    → "#26c6da" (dark) or "#00838f" (light)
/// TH.toggle()  → switches mode, caller rebuilds UI

use anyhow::{Result, Context};
use std::collections::HashMap;

pub const MONO_FONT: &str = "Cascadia Code, Consolas, SF Mono, monospace";

pub const FONT_FAMILY: &str = "Segoe UI, Roboto, Helvetica, Arial, sans-serif";

/// Metaclass: ``TH.accent`` returns a colour string directly.
#[derive(Debug, Clone)]
pub struct _THMeta {
}

impl _THMeta {
    /// Raise a clear error when an undefined theme attribute is accessed.
    pub fn __getattr__(&self, cls: String, name: String) -> Result<String> {
        // Raise a clear error when an undefined theme attribute is accessed.
        if !cls._KEYS.contains(&name) {
            return;
        }
        let mut palette = if cls._dark { cls._DARK } else { cls._LIGHT };
        palette[&name]
        return Err(anyhow::anyhow!("AttributeError(name)"));
    }
}

/// Dynamic theme — access colours as ``TH.accent``, ``TH.bg``, etc.
#[derive(Debug, Clone)]
pub struct TH {
    pub _dark: bool,
    pub _DARK: HashMap<String, String>,
    pub _LIGHT: HashMap<String, String>,
}

impl TH {
    /// Return true if dark mode is active.
    pub fn is_dark() -> bool {
        // Return true if dark mode is active.
        cls._dark
    }
    /// Toggle between dark and light mode.
    pub fn toggle() -> () {
        // Toggle between dark and light mode.
        cls._dark = !cls._dark;
    }
    /// Explicitly set dark mode state.
    pub fn set_dark(dark: bool) -> () {
        // Explicitly set dark mode state.
        cls._dark = dark;
    }
}

/// Return a Flet ``Theme`` object matching the current TH palette.
pub fn build_flet_theme(dark: bool) -> ft::Theme {
    // Return a Flet ``Theme`` object matching the current TH palette.
    let mut palette = if dark { TH._DARK } else { TH._LIGHT };
    /* flet::Theme */(/* color_scheme_seed= */ palette["accent".to_string()], /* font_family= */ FONT_FAMILY)
}

/// Apply the TH colour scheme to a Flet page.
pub fn setup_page_theme(page: ft::Page) -> () {
    // Apply the TH colour scheme to a Flet page.
    page.title = "ZenAI — Intelligent Assistant".to_string();
    page.theme_mode = if TH.is_dark() { /* flet::ThemeMode.DARK */ } else { /* flet::ThemeMode.LIGHT */ };
    page.bgcolor = TH.bg;
    page.window.width = 1400;
    page.window.height = 900;
    page.padding = 0;
    page.spacing = 0;
    page.fonts = HashMap::from([("mono".to_string(), "Cascadia Code".to_string())]);
    /* page.theme = flet::... */;
    /* page.dark_theme = flet::... */;
}
