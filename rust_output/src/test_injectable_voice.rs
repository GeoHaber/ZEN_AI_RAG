/// Test the injectable voice manager

use anyhow::{Result, Context};
use crate::injectable_voice::{InjectableVoiceManager};

pub static VM: std::sync::LazyLock<InjectableVoiceManager> = std::sync::LazyLock::new(|| Default::default());

pub static STATUS: std::sync::LazyLock<String /* vm.get_injection_status */> = std::sync::LazyLock::new(|| Default::default());

pub static RESULT: std::sync::LazyLock<String /* vm.record_audio */> = std::sync::LazyLock::new(|| Default::default());
