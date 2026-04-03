use anyhow::{Result, Context};

pub static R: std::sync::LazyLock<String /* requests.post */> = std::sync::LazyLock::new(|| Default::default());
