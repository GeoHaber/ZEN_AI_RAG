/// Injectable Voice Handler for ZEN_AI_RAG UI
/// Allows injecting synthetic audio for testing without microphone

use anyhow::{Result, Context};
use crate::voice_manager::{VoiceManager, RecordingResult};
use std::collections::HashMap;

/// VoiceManager with audio injection capability for testing.
/// Can synthesize audio or use pre-recorded audio for testing without microphone.
#[derive(Debug, Clone)]
pub struct InjectableVoiceManager {
    pub inject_audio: Option<Vec<u8>>,
    pub inject_enabled: bool,
    pub last_injection: Option<serde_json::Value>,
}

impl InjectableVoiceManager {
    /// Initialize instance.
    pub fn new(args: Vec<Box<dyn std::any::Any>>, kwargs: HashMap<String, Box<dyn std::any::Any>>) -> Self {
        Self {
            inject_audio: None,
            inject_enabled: false,
            last_injection: None,
        }
    }
    /// Generate a sine wave for testing.
    /// 
    /// Args:
    /// frequency: Frequency in Hz (default: 1000)
    /// duration: Duration in seconds (default: 2.0)
    /// amplitude: Amplitude 0-1 (default: 0.3)
    /// 
    /// Returns:
    /// WAV bytes
    pub fn generate_sine_wave(&self, frequency: f64, duration: f64, amplitude: f64) -> Result<Vec<u8>> {
        // Generate a sine wave for testing.
        // 
        // Args:
        // frequency: Frequency in Hz (default: 1000)
        // duration: Duration in seconds (default: 2.0)
        // amplitude: Amplitude 0-1 (default: 0.3)
        // 
        // Returns:
        // WAV bytes
        let mut sample_rate = 16000;
        let mut t = numpy.linspace(0, duration, (sample_rate * duration).to_string().parse::<i64>().unwrap_or(0));
        let mut audio_data = (amplitude * numpy.sin((((2 * numpy.pi) * frequency) * t)).astype(numpy.float32));
        let mut wav_buffer = io.BytesIO();
        wavfile.write(wav_buffer, sample_rate, (audio_data * 32767).astype("int16".to_string()));
        Ok(wav_buffer.getvalue())
    }
    /// Generate white noise for testing.
    /// 
    /// Args:
    /// duration: Duration in seconds
    /// amplitude: Amplitude 0-1
    /// 
    /// Returns:
    /// WAV bytes
    pub fn generate_white_noise(&self, duration: f64, amplitude: f64) -> Result<Vec<u8>> {
        // Generate white noise for testing.
        // 
        // Args:
        // duration: Duration in seconds
        // amplitude: Amplitude 0-1
        // 
        // Returns:
        // WAV bytes
        let mut sample_rate = 16000;
        let mut samples = (sample_rate * duration).to_string().parse::<i64>().unwrap_or(0);
        let mut audio_data = (amplitude * numpy.random.normal(0, 1, samples).astype(numpy.float32));
        let mut audio_data = numpy.clip(audio_data, -1, 1);
        let mut wav_buffer = io.BytesIO();
        wavfile.write(wav_buffer, sample_rate, (audio_data * 32767).astype("int16".to_string()));
        Ok(wav_buffer.getvalue())
    }
    /// Generate audio that mimics voice (mix of frequencies).
    /// 
    /// Args:
    /// duration: Duration in seconds
    /// 
    /// Returns:
    /// WAV bytes
    pub fn generate_voice_like_audio(&self, duration: f64) -> Result<Vec<u8>> {
        // Generate audio that mimics voice (mix of frequencies).
        // 
        // Args:
        // duration: Duration in seconds
        // 
        // Returns:
        // WAV bytes
        let mut sample_rate = 16000;
        let mut t = numpy.linspace(0, duration, (sample_rate * duration).to_string().parse::<i64>().unwrap_or(0));
        let mut audio_data = ((((0.3_f64 * numpy.sin((((2 * numpy.pi) * 150) * t))) + (0.2_f64 * numpy.sin((((2 * numpy.pi) * 300) * t)))) + (0.1_f64 * numpy.sin((((2 * numpy.pi) * 600) * t)))) + (0.05_f64 * numpy.random.normal(0, 1, t.len()))).astype(numpy.float32);
        let mut max_val = numpy.max(numpy.abs(audio_data));
        if max_val > 0 {
            let mut audio_data = ((audio_data / max_val) * 0.3_f64);
        }
        let mut wav_buffer = io.BytesIO();
        wavfile.write(wav_buffer, sample_rate, (audio_data * 32767).astype("int16".to_string()));
        Ok(wav_buffer.getvalue())
    }
    /// Record audio, with injection support for testing.
    /// 
    /// If inject_enabled=true and inject_audio is set, returns injected audio
    /// instead of recording from microphone.
    /// 
    /// Args:
    /// duration: Recording duration in seconds
    /// device_id: Microphone device ID (ignored if injecting)
    /// sample_rate: Sample rate in Hz
    /// channels: Number of channels
    /// auto_fallback: Try alternate devices if primary fails
    /// 
    /// Returns:
    /// RecordingResult with audio data
    pub fn record_audio(&mut self, duration: f64, device_id: String, sample_rate: i64, channels: i64, auto_fallback: bool) -> RecordingResult {
        // Record audio, with injection support for testing.
        // 
        // If inject_enabled=true and inject_audio is set, returns injected audio
        // instead of recording from microphone.
        // 
        // Args:
        // duration: Recording duration in seconds
        // device_id: Microphone device ID (ignored if injecting)
        // sample_rate: Sample rate in Hz
        // channels: Number of channels
        // auto_fallback: Try alternate devices if primary fails
        // 
        // Returns:
        // RecordingResult with audio data
        if (self.inject_enabled && self.inject_audio) {
            self.last_injection = HashMap::from([("type".to_string(), "custom".to_string()), ("size".to_string(), self.inject_audio.len()), ("duration".to_string(), duration), ("sample_rate".to_string(), sample_rate)]);
            RecordingResult(/* success= */ true, /* audio_data= */ self.inject_audio, /* duration= */ duration, /* sample_rate= */ sample_rate)
        }
        r#super().record_audio(duration, device_id, sample_rate, channels, auto_fallback)
    }
    /// Enable audio injection with generated audio.
    /// 
    /// Args:
    /// audio_type: 'sine' (1kHz), 'noise', or 'voice'
    pub fn enable_injection(&mut self, audio_type: String) -> Result<()> {
        // Enable audio injection with generated audio.
        // 
        // Args:
        // audio_type: 'sine' (1kHz), 'noise', or 'voice'
        if audio_type == "sine".to_string() {
            self.inject_audio = self.generate_sine_wave(/* frequency= */ 1000, /* duration= */ 2.0_f64);
            let mut label = "Sine Wave (1kHz)".to_string();
        } else if audio_type == "noise".to_string() {
            self.inject_audio = self.generate_white_noise(/* duration= */ 2.0_f64);
            let mut label = "White Noise".to_string();
        } else if audio_type == "voice".to_string() {
            self.inject_audio = self.generate_voice_like_audio(/* duration= */ 2.0_f64);
            let mut label = "Voice-like".to_string();
        } else {
            return Err(anyhow::anyhow!("ValueError(f'Unknown audio type: {audio_type}')"));
        }
        self.inject_enabled = true;
        Ok(self.last_injection = HashMap::from([("type".to_string(), audio_type), ("label".to_string(), label)]))
    }
    /// Disable audio injection and use real microphone.
    pub fn disable_injection(&mut self) -> () {
        // Disable audio injection and use real microphone.
        self.inject_enabled = false;
        self.inject_audio = None;
    }
    /// Get current injection status.
    pub fn get_injection_status(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Get current injection status.
        HashMap::from([("enabled".to_string(), self.inject_enabled), ("has_audio".to_string(), self.inject_audio.is_some()), ("last_injection".to_string(), self.last_injection)])
    }
}

/// Create a test panel for audio injection in the UI.
/// 
/// Args:
/// ui: NiceGUI ui module
/// voice_manager: InjectableVoiceManager instance
pub fn create_audio_test_panel(ui: String, voice_manager: InjectableVoiceManager) -> () {
    // Create a test panel for audio injection in the UI.
    // 
    // Args:
    // ui: NiceGUI ui module
    // voice_manager: InjectableVoiceManager instance
    let _ctx = ui.card().classes("gap-2".to_string());
    {
        ui.label("🔧 Audio Injection (Testing)".to_string()).classes("font-bold".to_string());
        let _ctx = ui.row().classes("gap-2".to_string());
        {
            let use_sine = || {
                voice_manager::enable_injection("sine".to_string());
                ui.notify("Using synthetic sine wave (1kHz)".to_string(), /* type= */ "info".to_string());
            };
            let use_noise = || {
                voice_manager::enable_injection("noise".to_string());
                ui.notify("Using white noise".to_string(), /* type= */ "info".to_string());
            };
            let use_voice = || {
                voice_manager::enable_injection("voice".to_string());
                ui.notify("Using voice-like audio".to_string(), /* type= */ "info".to_string());
            };
            let disable = || {
                voice_manager::disable_injection();
                ui.notify("Injection disabled - using real microphone".to_string(), /* type= */ "info".to_string());
            };
            ui.button("📡 Sine Wave".to_string(), /* on_click= */ use_sine).classes("text-sm".to_string());
            ui.button("🌊 Noise".to_string(), /* on_click= */ use_noise).classes("text-sm".to_string());
            ui.button("🗣️ Voice".to_string(), /* on_click= */ use_voice).classes("text-sm".to_string());
            ui.button("❌ Real Mic".to_string(), /* on_click= */ disable).classes("text-sm".to_string());
        }
        let mut status_label = ui.label("Status: Ready".to_string());
        let update_status = || {
            // Update status.
            let mut status = voice_manager::get_injection_status();
            if status["enabled".to_string()] {
                let mut mode = status["last_injection".to_string()].get(&"label".to_string()).cloned().unwrap_or("Injected".to_string());
                status_label.text = format!("✓ Injection ON ({})", mode);
                status_label.classes("text-green-600".to_string(), /* remove= */ "text-gray-600".to_string());
            } else {
                status_label.text = "⚪ Using real microphone".to_string();
                status_label.classes("text-gray-600".to_string(), /* remove= */ "text-green-600".to_string());
            }
        };
        ui.timer(0.5_f64, update_status);
    }
}
