use anyhow::{Result, Context};

pub const BASE: &str = "http://localhost:5050";

pub static STATS: std::sync::LazyLock<String /* requests.get.json */> = std::sync::LazyLock::new(|| Default::default());
