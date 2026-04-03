use anyhow::{Result, Context};

pub static BASE_DIR: std::sync::LazyLock<String /* Path.parent().unwrap_or(std::path::Path::new("")).resolve */> = std::sync::LazyLock::new(|| Default::default());

pub static MODULES: std::sync::LazyLock<Vec<String>> = std::sync::LazyLock::new(|| Vec::new());

pub const ALL_OK: bool = true;

/// Test import.
pub fn test_import(module_name: String) -> Result<()> {
    // Test import.
    // try:
    {
        println!("Testing import: {}...", module_name);
        __import__(module_name);
        println!("{}", " OK".to_string());
        true
    }
    // except Exception as _e:
}
