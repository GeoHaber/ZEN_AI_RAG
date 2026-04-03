use anyhow::{Result, Context};
use crate::analysis::{analyze_and_write_report};

pub static P: std::sync::LazyLock<PathBuf> = std::sync::LazyLock::new(|| Default::default());
