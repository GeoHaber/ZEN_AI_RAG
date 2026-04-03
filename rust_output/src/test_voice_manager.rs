/// Quick test of VoiceManager

use anyhow::{Result, Context};
use crate::voice_manager::{get_voice_manager};

pub static VM: std::sync::LazyLock<get_voice_manager> = std::sync::LazyLock::new(|| Default::default());

pub static STATUS: std::sync::LazyLock<String /* vm.get_status */> = std::sync::LazyLock::new(|| Default::default());

pub const INPUT_DEVICES: &str = "[d for d in status['devices'] if d['is_input']]";
