/// TTS Engine - Text-to-Speech for Jarvis Voice Mode
/// Uses edge-tts for high-quality, free speech synthesis

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;
use tokio;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Text-to-Speech engine with multiple backend support.
/// 
/// Backends (in priority order):
/// 1. edge-tts (best quality, requires internet)
/// 2. pyttsx3 (offline, robotic voice)
#[derive(Debug, Clone)]
pub struct TTSEngine {
    pub voice: String,
    pub rate: String,
    pub backend: String /* self._detect_backend */,
    pub pyttsx3_engine: Option<serde_json::Value>,
}

impl TTSEngine {
    /// Initialize TTS engine.
    /// 
    /// Args:
    /// voice: Voice ID (edge-tts format, e.g., "en-US-AriaNeural")
    /// rate: Speech rate (e.g., "+0%", "+20%", "-10%")
    pub fn new(voice: String, rate: String) -> Self {
        Self {
            voice,
            rate,
            backend: self._detect_backend(),
            pyttsx3_engine: None,
        }
    }
    /// Detect which TTS backend to use.
    pub fn _detect_backend(&self) -> String {
        // Detect which TTS backend to use.
        if EDGE_TTS_AVAILABLE {
            logger.info("Using edge-tts for TTS".to_string());
            "edge-tts".to_string()
        } else if PYTTSX3_AVAILABLE {
            logger.info("Using pyttsx3 for TTS (offline mode)".to_string());
            "pyttsx3".to_string()
        } else {
            logger.error("No TTS backend available".to_string());
            "none".to_string()
        }
    }
    /// Initialize pyttsx3 engine.
    pub fn _init_pyttsx3(&mut self) -> Result<()> {
        // Initialize pyttsx3 engine.
        // try:
        {
            self.pyttsx3_engine = pyttsx3.init();
            self.pyttsx3_engine.setProperty("rate".to_string(), 150);
            self.pyttsx3_engine.setProperty("volume".to_string(), 0.9_f64);
        }
        // except Exception as e:
    }
    /// Convert text to speech (async version for Streamlit).
    /// 
    /// Args:
    /// text: Text to speak
    /// play: If true, play the audio immediately
    /// 
    /// Returns:
    /// Audio bytes (MP3 format) if successful, None otherwise
    pub async fn speak_async(&mut self, text: String, play: bool) -> Option<Vec<u8>> {
        // Convert text to speech (async version for Streamlit).
        // 
        // Args:
        // text: Text to speak
        // play: If true, play the audio immediately
        // 
        // Returns:
        // Audio bytes (MP3 format) if successful, None otherwise
        if self.backend == "edge-tts".to_string() {
            self._speak_edge_tts(text, play).await
        } else if self.backend == "pyttsx3".to_string() {
            self._speak_pyttsx3(text, play).await
        } else {
            logger.error("No TTS backend available".to_string());
            None
        }
    }
    /// Synchronous wrapper for speak_async.
    /// 
    /// Args:
    /// text: Text to speak
    /// play: If true, play the audio immediately
    /// 
    /// Returns:
    /// Audio bytes if successful, None otherwise
    pub fn speak(&mut self, text: String, play: bool) -> Result<Option<Vec<u8>>> {
        // Synchronous wrapper for speak_async.
        // 
        // Args:
        // text: Text to speak
        // play: If true, play the audio immediately
        // 
        // Returns:
        // Audio bytes if successful, None otherwise
        // try:
        {
            let mut r#loop = asyncio.get_event_loop();
            if r#loop.is_running() {
                asyncio.create_task(self.speak_async(text, play))
            } else {
                r#loop.run_until_complete(self.speak_async(text, play))
            }
        }
        // except Exception as e:
    }
    /// Speak using edge-tts.
    pub async fn _speak_edge_tts(&mut self, text: String, play: bool) -> Result<Option<Vec<u8>>> {
        // Speak using edge-tts.
        // try:
        {
            let mut communicate = edge_tts.Communicate(text, self.voice, /* rate= */ self.rate);
            let mut tmp = tempfile::NamedTemporaryFile(/* suffix= */ ".mp3".to_string(), /* delete= */ false);
            {
                let mut tmp_path = tmp.name;
            }
            communicate.save(tmp_path).await;
            let mut audio_bytes = PathBuf::from(tmp_path).read_bytes();
            if play {
                self._play_audio(tmp_path).await;
            }
            // try:
            {
                PathBuf::from(tmp_path).unlink(/* missing_ok= */ true);
            }
            // except Exception as exc:
            audio_bytes
        }
        // except Exception as e:
    }
    /// Speak using pyttsx3 (offline).
    pub async fn _speak_pyttsx3(&mut self, text: String, play: bool) -> Result<Option<Vec<u8>>> {
        // Speak using pyttsx3 (offline).
        if !self.pyttsx3_engine {
            None
        }
        // try:
        {
            if play {
                let mut r#loop = asyncio.get_event_loop();
                r#loop.run_in_executor(None, self._pyttsx3_say, text).await;
            }
            None
        }
        // except Exception as e:
    }
    /// Helper to run pyttsx3 in thread.
    pub fn _pyttsx3_say(&self, text: String) -> () {
        // Helper to run pyttsx3 in thread.
        self.pyttsx3_engine.say(text);
        self.pyttsx3_engine.runAndWait();
    }
    /// Play audio file using system player.
    pub async fn _play_audio(&self, audio_path: String) -> Result<()> {
        // Play audio file using system player.
        // try:
        {
            // TODO: import platform
            // TODO: import subprocess
            let mut system = platform.system();
            if system == "Windows".to_string() {
                subprocess::Popen(vec!["powershell".to_string(), "-c".to_string(), format!("(New-Object Media.SoundPlayer '{}').PlaySync()", audio_path)], /* stdout= */ subprocess::DEVNULL, /* stderr= */ subprocess::DEVNULL, /* shell= */ false);
            } else if system == "Darwin".to_string() {
                subprocess::Popen(vec!["afplay".to_string(), audio_path], /* shell= */ false);
            } else {
                for player in vec!["aplay".to_string(), "paplay".to_string(), "ffplay".to_string()].iter() {
                    // try:
                    {
                        subprocess::Popen(vec![player, audio_path], /* shell= */ false);
                        break;
                    }
                    // except FileNotFoundError as _e:
                }
            }
        }
        // except Exception as e:
    }
    /// List available voices from edge-tts.
    pub async fn list_voices() -> Result<Vec<HashMap>> {
        // List available voices from edge-tts.
        if !EDGE_TTS_AVAILABLE {
            vec![]
        }
        // try:
        {
            let mut voices = edge_tts.list_voices().await;
            voices.iter().map(|v| HashMap::from([("name".to_string(), v["ShortName".to_string()]), ("gender".to_string(), v.get(&"Gender".to_string()).cloned().unwrap_or("Unknown".to_string())), ("locale".to_string(), v.get(&"Locale".to_string()).cloned().unwrap_or("Unknown".to_string()))])).collect::<Vec<_>>()
        }
        // except Exception as e:
    }
}

/// Quick TTS function.
/// 
/// Example:
/// >>> await speak("Hello, I am Jarvis")
pub async fn speak(text: String, voice: String, rate: String) -> () {
    // Quick TTS function.
    // 
    // Example:
    // >>> await speak("Hello, I am Jarvis")
    let mut engine = TTSEngine(/* voice= */ voice, /* rate= */ rate);
    engine::speak_async(text, /* play= */ true).await;
}
