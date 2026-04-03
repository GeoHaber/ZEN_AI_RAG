/// ZenAI Voice Service - Local Speech-to-Text and Text-to-Speech
/// Provides voice input/output capabilities using:
/// - faster-whisper for STT (speech recognition)
/// - Piper TTS for TTS (speech synthesis)

use anyhow::{Result, Context};
use crate::utils::{safe_print};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

pub static _VOICE_SERVICE: std::sync::LazyLock<Option<VoiceService>> = std::sync::LazyLock::new(|| None);

/// Local voice processing service with STT and TTS capabilities.
/// All processing happens offline on the user's machine.
#[derive(Debug, Clone)]
pub struct VoiceService {
    pub model_dir: String,
    pub stt_model_name: String,
    pub stt_model: Option<WhisperModel>,
    pub tts_voice_name: String,
    pub tts_model: Option<PiperVoice>,
    pub _lock: std::sync::Mutex<()>,
}

impl VoiceService {
    /// Initialize instance.
    pub fn new(model_dir: PathBuf, stt_model: String, tts_voice: String) -> Self {
        Self {
            model_dir,
            stt_model_name: stt_model,
            stt_model,
            tts_voice_name: tts_voice,
            tts_model: None,
            _lock: std::sync::Mutex::new(()),
        }
    }
    /// Load faster-whisper model for speech recognition.
    pub fn load_stt_model(&mut self) -> Result<()> {
        // Load faster-whisper model for speech recognition.
        if self.stt_model.is_some() {
            return;
        }
        if WhisperModel.is_none() {
            return Err(anyhow::anyhow!("RuntimeError('faster-whisper not installed. Run: pip install faster-whisper')"));
        }
        logger.info(format!("[STT] Loading {} model...", self.stt_model_name));
        self.stt_model = WhisperModel(self.stt_model_name, /* device= */ "cpu".to_string(), /* compute_type= */ "int8".to_string(), /* download_root= */ (self.model_dir / "whisper".to_string()).to_string());
        Ok(logger.info("[STT] Model loaded successfully".to_string()))
    }
    /// Ensures the Piper model exists, downloading it if necessary.
    pub fn ensure_piper_model(&mut self) -> Result<()> {
        // Ensures the Piper model exists, downloading it if necessary.
        let mut voice_dir = (self.model_dir / "piper".to_string());
        voice_dir.create_dir_all();
        let mut onnx_file = (voice_dir / format!("{}.onnx", self.tts_voice_name));
        let mut json_file = (voice_dir / format!("{}.onnx.json", self.tts_voice_name));
        if (onnx_file.exists() && json_file.exists()) {
            (onnx_file, json_file)
        }
        logger.info(format!("[TTS] Downloading missing voice model: {}", self.tts_voice_name));
        let mut base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium".to_string();
        if self.tts_voice_name != "en_US-lessac-medium".to_string() {
            logger.warning(format!("[TTS] Auto-download only supports 'en_US-lessac-medium'. Please check path manually for {}", self.tts_voice_name));
            (onnx_file, json_file)
        }
        // TODO: import urllib::request
        // try:
        {
            if !onnx_file.exists() {
                logger.info("Downloading ONNX model...".to_string());
                urllib::request.urlretrieve(format!("{}/en_US-lessac-medium.onnx", base_url), onnx_file);
            }
            if !json_file.exists() {
                logger.info("Downloading Config JSON...".to_string());
                urllib::request.urlretrieve(format!("{}/en_US-lessac-medium.onnx.json", base_url), json_file);
            }
            logger.info("[TTS] Download complete.".to_string());
        }
        // except Exception as e:
        Ok((onnx_file, json_file))
    }
    /// Load Piper TTS model for speech synthesis.
    pub fn load_tts_model(&mut self) -> Result<()> {
        // Load Piper TTS model for speech synthesis.
        if self.tts_model.is_some() {
            return;
        }
        if PiperVoice.is_none() {
            return Err(anyhow::anyhow!("RuntimeError('piper-tts not installed. Run: pip install piper-tts')"));
        }
        logger.info(format!("[TTS] Loading {} voice...", self.tts_voice_name));
        // try:
        {
            let (mut voice_path, mut config_path) = self.ensure_piper_model();
            self.tts_model = PiperVoice.load(voice_path.to_string(), /* config_path= */ config_path.to_string());
            logger.info("[TTS] Voice loaded successfully".to_string());
        }
        // except Exception as e:
    }
    /// Transcribe audio file to text using faster-whisper.
    /// Robustly handles generic audio inputs by converting to clean WAV first.
    pub fn transcribe_audio(&mut self, audio_file: BinaryIO, language: String) -> Result<HashMap> {
        // Transcribe audio file to text using faster-whisper.
        // Robustly handles generic audio inputs by converting to clean WAV first.
        // TODO: import subprocess
        let _ctx = self._lock;
        {
            self.load_stt_model();
            let mut raw_path = (self.model_dir / "raw_audio_input.bin".to_string());
            let mut clean_path = (self.model_dir / "clean_audio.wav".to_string());
            let mut f = File::open(raw_path)?;
            {
                f.write(audio_file.read());
            }
            // try:
            {
                let mut cmd = vec!["ffmpeg".to_string(), "-y".to_string(), "-i".to_string(), raw_path.to_string(), "-ar".to_string(), "16000".to_string(), "-ac".to_string(), "1".to_string(), "-c:a".to_string(), "pcm_s16le".to_string(), clean_path.to_string()];
                let mut result = std::process::Command::new("sh").arg("-c").arg(cmd, /* capture_output= */ true, /* text= */ true, /* shell= */ false).output().unwrap();
                if result.returncode != 0 {
                    logger.error(format!("[Voice] FFmpeg conversion failed: {}", result.stderr));
                    let mut transcribe_target = raw_path.to_string();
                } else {
                    let mut transcribe_target = clean_path.to_string();
                }
                let (mut segments, mut info) = self.stt_model.transcribe(transcribe_target, /* language= */ if language != "auto".to_string() { language } else { None }, /* beam_size= */ 5, /* vad_filter= */ true);
                let mut text_parts = vec![];
                let mut segment_list = vec![];
                for segment in segments.iter() {
                    text_parts.push(segment.text);
                    segment_list.push(HashMap::from([("start".to_string(), segment.start), ("end".to_string(), segment.end), ("text".to_string(), segment.text)]));
                }
                let mut full_text = text_parts.join(&" ".to_string()).trim().to_string();
                HashMap::from([("text".to_string(), full_text), ("language".to_string(), info.language), ("segments".to_string(), segment_list), ("duration".to_string(), info.duration)])
            }
            // except Exception as e:
            // finally:
                // try:
                {
                    raw_path.unlink(/* missing_ok= */ true);
                }
                // except Exception as _e:
                // try:
                {
                    clean_path.unlink(/* missing_ok= */ true);
                }
                // except Exception as _e:
        }
    }
    /// Convert text to speech using Piper TTS.
    /// Optimized to use float32 PCM directly (no int16 conversion overhead).
    /// 
    /// Args:
    /// text: Text to speak
    /// speed: Speech speed multiplier (1.0 = normal)
    /// 
    /// Returns:
    /// WAV audio data as bytes (float32 PCM format for faster synthesis)
    pub fn synthesize_speech(&mut self, text: String, speed: f64) -> Result<Vec<u8>> {
        // Convert text to speech using Piper TTS.
        // Optimized to use float32 PCM directly (no int16 conversion overhead).
        // 
        // Args:
        // text: Text to speak
        // speed: Speech speed multiplier (1.0 = normal)
        // 
        // Returns:
        // WAV audio data as bytes (float32 PCM format for faster synthesis)
        self.load_tts_model();
        if self.tts_model.is_none() {
            return Err(anyhow::anyhow!("RuntimeError('TTS model failed to load. Check logs.')"));
        }
        let mut audio_stream = io.BytesIO();
        // try:
        {
            let mut audio_chunks = vec![];
            let mut sample_rate = 22050;
            for chunk in self.tts_model.synthesize(text).iter() {
                if /* hasattr(chunk, "audio_float_array".to_string()) */ true {
                    audio_chunks.push(chunk.audio_float_array.tobytes());
                    if /* hasattr(chunk, "sample_rate".to_string()) */ true {
                        let mut sample_rate = chunk.sample_rate;
                    }
                }
            }
            if !audio_chunks {
                return Err(anyhow::anyhow!("RuntimeError('TTS synthesize produced no audio chunks')"));
            }
            let mut pcm_data = audio_chunks.join(&b"");
            let mut wav_file = wave.open(audio_stream, "wb".to_string());
            {
                wav_file.setnchannels(1);
                wav_file.setsampwidth(4);
                wav_file.setframerate(sample_rate);
                wav_file.writeframes(pcm_data);
            }
            audio_stream.seek(0);
            audio_stream.read()
        }
        // except Exception as e:
    }
    /// Create a new stream processor instance.
    pub fn create_stream_processor(&self) -> () {
        // Create a new stream processor instance.
        self.load_stt_model();
        StreamProcessor(self.stt_model)
    }
}

/// Handles streaming audio input with real-time incremental transcription.
/// Uses sliding window with quick partial results.
#[derive(Debug, Clone)]
pub struct StreamProcessor {
    pub model: String,
    pub audio_buffer: bytearray,
    pub sample_rate: i64,
    pub sample_width: i64,
    pub process_interval: String,
    pub last_text: String,
    pub transcription_count: i64,
}

impl StreamProcessor {
    /// Initialize instance.
    pub fn new(model: WhisperModel) -> Self {
        Self {
            model,
            audio_buffer: bytearray(),
            sample_rate: 16000,
            sample_width: 2,
            process_interval: ((self.sample_rate * self.sample_width) * 0.5_f64),
            last_text: "".to_string(),
            transcription_count: 0,
        }
    }
    /// Add PCM audio chunk to buffer.
    pub fn add_audio(&self, audio_chunk: Vec<u8>) -> () {
        // Add PCM audio chunk to buffer.
        self.audio_buffer.extend(audio_chunk);
    }
    /// Process current buffer and return incremental text.
    /// Returns: { "text": "incremental text...", "is_final": false }
    pub fn process(&mut self) -> Result<HashMap> {
        // Process current buffer and return incremental text.
        // Returns: { "text": "incremental text...", "is_final": false }
        if self.audio_buffer.len() < self.process_interval {
            None
        }
        // TODO: import numpy as np
        // try:
        {
            let mut audio_int16 = np.frombuffer(self.audio_buffer, /* dtype= */ np.int16);
            let mut audio_float32 = (audio_int16.astype(np.float32) / 32768.0_f64);
            let (mut segments, _) = self.model.transcribe(audio_float32, /* language= */ "en".to_string(), /* beam_size= */ 1, /* word_timestamps= */ false, /* vad_filter= */ false);
            let mut text_parts = segments.iter().map(|segment| segment.text).collect::<Vec<_>>();
            let mut full_text = text_parts.join(&" ".to_string()).trim().to_string();
            if full_text != self.last_text {
                self.last_text = full_text;
                self.transcription_count += 1;
                HashMap::from([("text".to_string(), full_text), ("is_final".to_string(), false)])
            }
            None
        }
        // except Exception as e:
    }
    /// Finalize the stream and return final text.
    pub fn finish(&mut self) -> Result<HashMap> {
        // Finalize the stream and return final text.
        if !self.audio_buffer {
            HashMap::from([("text".to_string(), self.last_text), ("is_final".to_string(), true)])
        }
        // TODO: import numpy as np
        // try:
        {
            let mut audio_int16 = np.frombuffer(self.audio_buffer, /* dtype= */ np.int16);
            let mut audio_float32 = (audio_int16.astype(np.float32) / 32768.0_f64);
            let (mut segments, _) = self.model.transcribe(audio_float32, /* language= */ "en".to_string(), /* beam_size= */ 5, /* word_timestamps= */ false);
            let mut text_parts = segments.iter().map(|segment| segment.text).collect::<Vec<_>>();
            let mut final_text = text_parts.join(&" ".to_string()).trim().to_string();
            self.audio_buffer.clear();
            self.last_text = "".to_string();
            self.transcription_count = 0;
            HashMap::from([("text".to_string(), final_text), ("is_final".to_string(), true)])
        }
        // except Exception as e:
    }
}

/// Get or create the global voice service instance.
pub fn get_voice_service(model_dir: PathBuf, stt_model: String, tts_voice: String) -> VoiceService {
    // Get or create the global voice service instance.
    // global/nonlocal _voice_service
    if _voice_service.is_none() {
        let mut _voice_service = VoiceService(model_dir, stt_model, tts_voice);
    }
    _voice_service
}
