/// Microphone Audio Injection Test
/// Generate synthetic audio and inject it as if from microphone
/// to test the full audio pipeline

use anyhow::{Result, Context};

pub const SAMPLE_RATE: i64 = 16000;

pub const DURATION: i64 = 3;

pub const FREQUENCY: i64 = 1000;

pub static T: std::sync::LazyLock<String /* numpy.linspace */> = std::sync::LazyLock::new(|| Default::default());

pub const AUDIO_DATA: &str = "0.3 * numpy.sin(2 * numpy.pi * frequency * t).astype(numpy.float32)";

pub static WAV_BUFFER: std::sync::LazyLock<String /* io.BytesIO */> = std::sync::LazyLock::new(|| Default::default());

pub static WAV_BYTES: std::sync::LazyLock<String /* wav_buffer.getvalue */> = std::sync::LazyLock::new(|| Default::default());

pub static TEST_WAV_PATH: std::sync::LazyLock<PathBuf> = std::sync::LazyLock::new(|| Default::default());
