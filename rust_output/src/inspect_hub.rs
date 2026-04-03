use anyhow::{Result, Context};

pub static P: std::sync::LazyLock<String /* subprocess::Popen */> = std::sync::LazyLock::new(|| Default::default());

pub static START: std::sync::LazyLock<String /* time::time */> = std::sync::LazyLock::new(|| Default::default());

pub const TIMEOUT: i64 = 12;
