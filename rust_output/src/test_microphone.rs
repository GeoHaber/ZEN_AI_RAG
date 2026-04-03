/// Microphone Diagnostic Test
/// Test audio input capabilities and troubleshoot issues

use anyhow::{Result, Context};

pub static DEVICES: std::sync::LazyLock<String /* sounddevice.query_devices */> = std::sync::LazyLock::new(|| Default::default());
