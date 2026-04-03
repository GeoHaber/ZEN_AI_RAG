/// locales/en::py - English Locale
/// Default language for ZenAI.

use anyhow::{Result, Context};
use crate::base::{BaseLocale};

/// English locale - inherits all defaults from BaseLocale.
/// BaseLocale is written in English, so minimal overrides needed.
/// This class exists for consistency and potential future customization.
#[derive(Debug, Clone)]
pub struct EnglishLocale {
}
