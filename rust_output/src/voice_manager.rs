/// ZenAI Voice Manager - Unified Voice System
/// Manages microphone enumeration, recording, and TTS with proper device handling.

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _VOICE_MANAGER: std::sync::LazyLock<Option<VoiceManager>> = std::sync::LazyLock::new(|| None);

pub static _VOICE_MANAGER_LOCK: std::sync::LazyLock<std::sync::Mutex<()>> = std::sync::LazyLock::new(|| std::sync::Mutex::new(()));

/// Microphone/speaker device info.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioDevice {
    pub id: i64,
    pub name: String,
    pub channels: i64,
    pub is_input: bool,
    pub is_output: bool,
    pub default_sample_rate: f64,
}

impl AudioDevice {
    /// Convert to JSON-serializable dict.
    pub fn to_dict(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Convert to JSON-serializable dict.
        asdict(self)
    }
}

/// Result from audio recording.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecordingResult {
    pub success: bool,
    pub audio_data: Option<Vec<u8>>,
    pub duration: f64,
    pub sample_rate: i64,
    pub error: Option<String>,
}

impl RecordingResult {
    /// Convert to JSON-serializable dict (excludes raw audio_data).
    pub fn to_dict(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        // Convert to JSON-serializable dict (excludes raw audio_data).
        HashMap::from([("success".to_string(), self.success), ("duration".to_string(), self.duration), ("sample_rate".to_string(), self.sample_rate), ("error".to_string(), self.error)])
    }
}

/// Unified voice management system:
/// - Enumerate audio devices
/// - Record from selected microphone
/// - Transcribe audio (STT)
/// - Synthesize speech (TTS)
#[derive(Debug, Clone)]
pub struct VoiceManager {
    pub model_dir: PathBuf,
    pub stt_model: String,
    pub tts_voice: String,
    pub _voice_service: Option<VoiceService>,
    pub _service_lock: std::sync::Mutex<()>,
    pub _default_input_device: Option<i64>,
    pub _device_list_cache: Option<Vec<AudioDevice>>,
    pub _cache_valid: bool,
    pub _tts_cache: HashMap<String, Vec<u8>>,
    pub _tts_cache_dir: String,
}

impl VoiceManager {
    /// Initialize voice manager.
    /// 
    /// Args:
    /// model_dir: Directory for downloaded models. Defaults to ~/.zena/models
    /// stt_model: Whisper model size ("tiny", "base", "small", "medium", "large")
    /// tts_voice: Piper voice name ("en_US-lessac-medium", etc.)
    pub fn new(model_dir: Option<PathBuf>, stt_model: String, tts_voice: String) -> Self {
        Self {
            model_dir: PathBuf::from(model_dir),
            stt_model,
            tts_voice,
            _voice_service: None,
            _service_lock: std::sync::Mutex::new(()),
            _default_input_device: None,
            _device_list_cache: None,
            _cache_valid: false,
            _tts_cache: HashMap::new(),
            _tts_cache_dir: (self.model_dir / "tts_cache".to_string()),
        }
    }
    /// Get or create VoiceService instance (thread-safe).
    pub fn get_voice_service(&mut self) -> Result<Option<VoiceService>> {
        // Get or create VoiceService instance (thread-safe).
        if !HAS_VOICE_SERVICE {
            None
        }
        let _ctx = self._service_lock;
        {
            if self._voice_service.is_none() {
                // try:
                {
                    self._voice_service = VoiceService(/* model_dir= */ self.model_dir, /* stt_model= */ self.stt_model, /* tts_voice= */ self.tts_voice);
                }
                // except Exception as e:
            }
            self._voice_service
        }
    }
    /// Enumerate all audio input/output devices.
    /// 
    /// Returns:
    /// List of AudioDevice objects with id, name, channels, etc.
    pub fn enumerate_devices(&mut self) -> Result<Vec<AudioDevice>> {
        // Enumerate all audio input/output devices.
        // 
        // Returns:
        // List of AudioDevice objects with id, name, channels, etc.
        if !HAS_AUDIO_CAPTURE {
            logger.warning("[VoiceManager] sounddevice not available".to_string());
            vec![]
        }
        // try:
        {
            let mut devices = vec![];
            let mut device_list = sd.query_devices();
            if /* /* isinstance(device_list, dict) */ */ true {
                let mut device_list = vec![device_list];
            }
            for (i, dev) in device_list.iter().enumerate().iter() {
                let mut device = AudioDevice(/* id= */ i, /* name= */ dev.get(&"name".to_string()).cloned().unwrap_or(format!("Device {}", i)), /* channels= */ dev.get(&"max_input_channels".to_string()).cloned().unwrap_or(0), /* is_input= */ dev.get(&"max_input_channels".to_string()).cloned().unwrap_or(0) > 0, /* is_output= */ dev.get(&"max_output_channels".to_string()).cloned().unwrap_or(0) > 0, /* default_sample_rate= */ dev.get(&"default_samplerate".to_string()).cloned().unwrap_or(48000).to_string().parse::<f64>().unwrap_or(0.0));
                devices.push(device);
            }
            self._device_list_cache = devices;
            self._cache_valid = true;
            logger.info(format!("[VoiceManager] Enumerated {} devices", devices.len()));
            devices
        }
        // except Exception as e:
    }
    /// Get default microphone device ID.
    pub fn get_default_input_device(&self) -> Result<Option<i64>> {
        // Get default microphone device ID.
        if !HAS_AUDIO_CAPTURE {
            None
        }
        // try:
        {
            let mut default_info = sd.default.device;
            if /* /* isinstance(default_info, tuple) */ */ true {
                default_info[0]
            }
            default_info
        }
        // except Exception as e:
    }
}

/// Record audio part1 part 2.
pub fn _record_audio_part1_part2(r#self: String) -> Result<()> {
    // Record audio part1 part 2.
    let transcribe = |audio_data, language| {
        // Transcribe audio to text using Whisper.
        // 
        // Args:
        // audio_data: WAV audio bytes
        // language: Language code (default: "en")
        // 
        // Returns:
        // Dict with 'text' (transcribed text) and 'success'
        let mut vs = self.get_voice_service();
        if !vs {
            HashMap::from([("success".to_string(), false), ("error".to_string(), "VoiceService not available".to_string())])
        }
        // try:
        {
            logger.info(format!("[VoiceManager] Transcribing {} bytes", audio_data.len()));
            let mut result = vs.transcribe_audio(io.BytesIO(audio_data), /* language= */ language);
            logger.info(format!("[VoiceManager] Transcription: {}...", result.get(&"text".to_string()).cloned().unwrap_or("".to_string())[..50]));
            result
        }
        // except Exception as e:
    };
    let synthesize = |text, use_cache| {
        // Synthesize text to speech with optional caching.
        // 
        // Args:
        // text: Text to speak
        // use_cache: Use cached audio if available (default: true)
        // 
        // Returns:
        // Dict with:
        // - 'success': bool
        // - 'audio_data': base64-encoded WAV bytes
        // - 'audio_url': data URL for HTML5 audio tag
        // - 'text': original text
        // - 'duration': estimated duration in seconds
        // - 'error': error message if failed
        let mut vs = self.get_voice_service();
        if !vs {
            HashMap::from([("success".to_string(), false), ("error".to_string(), "VoiceService not available".to_string())])
        }
        // try:
        {
            if (use_cache && self._tts_cache.contains(&text)) {
                let mut audio_data = self._tts_cache[&text];
                logger.info(format!("[VoiceManager] Using cached TTS: {}...", text[..50]));
            } else {
                logger.info(format!("[VoiceManager] Synthesizing: {}...", text[..50]));
                let _ctx = self._service_lock;
                {
                    let mut audio_data = vs.synthesize_speech(text);
                }
                if use_cache {
                    self._tts_cache[text] = audio_data;
                }
                logger.info(format!("[VoiceManager] Generated {} bytes", audio_data.len()));
            }
            if !audio_data {
                HashMap::from([("success".to_string(), false), ("error".to_string(), "TTS generated empty audio".to_string())])
            }
            // TODO: import base64
            let mut audio_b64 = base64::b64encode(audio_data).decode("utf-8".to_string());
            let mut audio_url = format!("data:audio/wav;base64,{}", audio_b64);
            let mut estimated_duration = 1.0_f64.max((text.len() / 100.0_f64));
            logger.info(format!("[VoiceManager] Synthesis complete ({} bytes)", audio_data.len()));
            HashMap::from([("success".to_string(), true), ("audio_data".to_string(), audio_b64), ("audio_url".to_string(), audio_url), ("text".to_string(), text), ("duration".to_string(), estimated_duration)])
        }
        // except Exception as e:
    Ok(})
}

/// Record audio part1 part 3.
pub fn _record_audio_part1_part3(r#self: String) -> () {
    // Record audio part1 part 3.
    let get_status = || {
        // Get comprehensive voice system status.
        HashMap::from([("voice_available".to_string(), HAS_VOICE_SERVICE), ("audio_capture_available".to_string(), HAS_AUDIO_CAPTURE), ("stt_model".to_string(), self.stt_model), ("tts_voice".to_string(), self.tts_voice), ("default_input_device".to_string(), self.get_default_input_device()), ("devices".to_string(), self.enumerate_devices().iter().map(|d| d.to_dict()).collect::<Vec<_>>())])
    };
}

/// Record audio part 1.
pub fn _record_audio_part1(r#self: String) -> Result<()> {
    // Record audio part 1.
    RecordingResult(/* success= */ false, /* error= */ format!("Recording failed on all {} devices. Last error: {}", devices_to_try.len(), last_error))
    let record_audio = |duration, device_id, sample_rate, channels, auto_fallback| {
        // Record audio from microphone with auto-fallback support.
        // 
        // Args:
        // duration: Recording duration in seconds (default: 3.0)
        // device_id: Microphone device ID (default: system default)
        // sample_rate: Sample rate in Hz (default: 16000)
        // channels: Number of channels (default: 1 for mono)
        // auto_fallback: Try alternate devices if primary fails (default: true)
        // 
        // Returns:
        // RecordingResult with audio_data as WAV bytes
        if !HAS_AUDIO_CAPTURE {
            RecordingResult(/* success= */ false, /* error= */ "sounddevice not installed - run: pip install sounddevice scipy".to_string())
        }
        let mut devices_to_try = vec![];
        if device_id.is_some() {
            devices_to_try.push(device_id);
        }
        let mut default_dev = self.get_default_input_device();
        if (default_dev.is_some() && !devices_to_try.contains(&default_dev)) {
            devices_to_try.push(default_dev);
        }
        if auto_fallback {
            let mut all_devices = self.enumerate_devices();
            for dev in all_devices.iter() {
                if (dev.is_input && !devices_to_try.contains(&dev.id)) {
                    devices_to_try.push(dev.id);
                }
            }
        }
        for (attempt, dev_id) in devices_to_try.iter().enumerate().iter() {
            // try:
            {
                logger.info(format!("[VoiceManager] Recording {}s from device {} (attempt {}/{})", duration, dev_id, attempt, devices_to_try.len()));
                let mut num_samples = (duration * sample_rate).to_string().parse::<i64>().unwrap_or(0);
                let mut recording = sd.rec(num_samples, /* samplerate= */ sample_rate, /* channels= */ channels, /* dtype= */ "float32".to_string(), /* device= */ dev_id, /* blocking= */ true);
                sd.wait();
                let mut wav_buffer = io.BytesIO();
                wav.write(wav_buffer, sample_rate, (recording * 32767).astype("int16".to_string()));
                wav_buffer.seek(0);
                let mut result = RecordingResult(/* success= */ true, /* audio_data= */ wav_buffer.getvalue(), /* duration= */ duration, /* sample_rate= */ sample_rate);
                logger.info(format!("[VoiceManager] Recording complete from device {} ({} bytes)", dev_id, result.audio_data.len()));
                result
            }
            // except Exception as e:
        }
        _record_audio_part1(self);
    };
    _record_audio_part1_part2(self);
    Ok(_record_audio_part1_part3(self))
}

/// Get or create global VoiceManager instance.
pub fn get_voice_manager(model_dir: Option<PathBuf>) -> VoiceManager {
    // Get or create global VoiceManager instance.
    // global/nonlocal _voice_manager
    if _voice_manager.is_none() {
        let _ctx = _voice_manager_lock;
        {
            if _voice_manager.is_none() {
                let mut _voice_manager = VoiceManager(/* model_dir= */ model_dir);
            }
        }
    }
    _voice_manager
}
