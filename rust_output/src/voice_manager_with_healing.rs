/// Enhanced Voice Manager with Microphone Self-Healing
/// 
/// This module extends the standard VoiceManager with automatic microphone
/// diagnostics and recovery capabilities.

use anyhow::{Result, Context};
use crate::voice_manager::{VoiceManager};
use std::collections::HashMap;
use std::collections::HashSet;
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Voice Manager with automatic microphone diagnostics and self-healing.
/// 
/// Features:
/// - Automatic device health checks before recording
/// - Fallback to alternative devices on failure
/// - Process monitoring (finds which apps block microphone)
/// - Audio quality scoring
/// - Actionable recommendations for users
#[derive(Debug, Clone)]
pub struct VoiceManagerWithHealing {
    pub preferred_device: String,
    pub auto_heal_enabled: String,
    pub healer: ProductionMicrophoneHealer,
}

impl VoiceManagerWithHealing {
    /// Initialize with optional auto-healing.
    /// 
    /// Args:
    /// model_dir: Directory for downloaded models
    /// stt_model: Whisper model size
    /// tts_voice: Piper voice name
    /// auto_heal: Enable automatic microphone healing
    /// preferred_device: Preferred microphone device ID
    pub fn new(model_dir: Option<PathBuf>, stt_model: String, tts_voice: String, auto_heal: bool, preferred_device: Option<i64>) -> Self {
        Self {
            preferred_device,
            auto_heal_enabled: (auto_heal && HAS_HEALER),
            healer: Default::default(),
        }
    }
}

/// Voice Manager with automatic microphone diagnostics and self-healing.
/// 
/// Features:
/// - Automatic device health checks before recording
/// - Fallback to alternative devices on failure
/// - Process monitoring (finds which apps block microphone)
/// - Audio quality scoring
/// - Actionable recommendations for users
#[derive(Debug, Clone)]
pub struct VoiceManagerWithHealing {
    pub auto_heal_enabled: String,
    pub healer: ProductionMicrophoneHealer,
}

impl VoiceManagerWithHealing {
    /// Initialize with optional auto-healing.
    /// 
    /// Args:
    /// model_dir: Directory for downloaded models
    /// stt_model: Whisper model size
    /// tts_voice: Piper voice name
    /// auto_heal: Enable automatic microphone healing
    pub fn new(model_dir: Option<PathBuf>, stt_model: String, tts_voice: String, auto_heal: bool) -> Self {
        Self {
            auto_heal_enabled: (auto_heal && HAS_HEALER),
            healer: Default::default(),
        }
    }
    /// Run complete microphone diagnostic.
    /// 
    /// Args:
    /// verbose: Print detailed diagnostics
    /// 
    /// Returns:
    /// Diagnostic results with recommendations
    pub fn diagnose_microphone(&mut self, verbose: bool) -> HashMap<String, Box<dyn std::any::Any>> {
        // Run complete microphone diagnostic.
        // 
        // Args:
        // verbose: Print detailed diagnostics
        // 
        // Returns:
        // Diagnostic results with recommendations
        if !self.healer {
            logger.warning("Healer not available".to_string());
            HashMap::from([("status".to_string(), "ERROR".to_string()), ("message".to_string(), "Healer not initialized".to_string())])
        }
        if verbose { self.healer.auto_heal_with_recommendations() } else { self.healer.full_diagnostic(/* verbose= */ false) }
    }
    /// Get the best available microphone device.
    /// 
    /// Uses ProductionMicrophoneHealer to score all devices and return
    /// the best one based on availability, quality, and priority.
    /// 
    /// Returns:
    /// Device ID or None if no devices available
    pub fn get_best_device(&mut self) -> Option<i64> {
        // Get the best available microphone device.
        // 
        // Uses ProductionMicrophoneHealer to score all devices and return
        // the best one based on availability, quality, and priority.
        // 
        // Returns:
        // Device ID or None if no devices available
        if !self.healer {
            logger.warning("Healer not available".to_string());
            None
        }
        let mut diag = self.healer.full_diagnostic(/* verbose= */ false);
        diag.get(&"best_device_id".to_string()).cloned()
    }
    /// Record audio with automatic microphone healing.
    /// 
    /// If recording fails:
    /// 1. Run diagnostic to find best device
    /// 2. Try alternative devices automatically
    /// 3. Return audio or None on failure
    /// 
    /// Args:
    /// duration: Recording duration in seconds
    /// device_id: Specific device to try first
    /// auto_fallback: Try alternative devices on failure
    /// verbose: Print healing messages
    /// 
    /// Returns:
    /// WAV audio bytes or None on failure
    pub fn record_audio_with_healing(&mut self, duration: f64, device_id: Option<i64>, auto_fallback: bool, verbose: bool) -> Option<Vec<u8>> {
        // Record audio with automatic microphone healing.
        // 
        // If recording fails:
        // 1. Run diagnostic to find best device
        // 2. Try alternative devices automatically
        // 3. Return audio or None on failure
        // 
        // Args:
        // duration: Recording duration in seconds
        // device_id: Specific device to try first
        // auto_fallback: Try alternative devices on failure
        // verbose: Print healing messages
        // 
        // Returns:
        // WAV audio bytes or None on failure
        if verbose {
            logger.info("Recording audio...".to_string());
        }
        let mut result = self.record_audio(/* duration= */ duration, /* device_id= */ device_id, /* auto_fallback= */ auto_fallback);
        if (result.success && result.audio_data) {
            if verbose {
                logger.info(format!("✓ Recording successful ({} bytes)", result.audio_data.len()));
            }
            result.audio_data
        }
        if (auto_fallback && self.healer && verbose) {
            logger.warning(format!("Recording failed: {}", result.error));
            logger.info("Running microphone diagnostic...".to_string());
            let mut diag = self.full_diagnostic(/* verbose= */ false);
            let mut best = diag.get(&"best_device_id".to_string()).cloned();
            if (best.is_some() && best != device_id) {
                logger.info(format!("Trying best device: #{}", best));
                let mut result2 = self.record_audio(/* duration= */ duration, /* device_id= */ best, /* auto_fallback= */ false);
                if result2.success {
                    logger.info(format!("✓ Success with device {}", best));
                    result2.audio_data
                }
            }
        }
        logger.error(format!("Could not record audio: {}", result.error));
        None
    }
    /// Alias for diagnose_microphone for consistency.
    pub fn full_diagnostic(&mut self, verbose: bool) -> HashMap<String, Box<dyn std::any::Any>> {
        // Alias for diagnose_microphone for consistency.
        self.diagnose_microphone(/* verbose= */ verbose)
    }
    /// Get human-readable microphone health report.
    /// 
    /// Returns:
    /// Multi-line health report
    pub fn get_health_report(&mut self) -> String {
        // Get human-readable microphone health report.
        // 
        // Returns:
        // Multi-line health report
        if !self.healer {
            "Healer not available".to_string()
        }
        let mut result = self.healer.auto_heal_with_recommendations();
        let mut lines = vec![];
        lines.push(("=".to_string() * 70));
        lines.push("MICROPHONE HEALTH REPORT".to_string());
        lines.push(("=".to_string() * 70));
        let mut best = result["diagnostic".to_string()]["best_device".to_string()];
        if best {
            lines.push(format!("\nBest Device: #{} - {}", best["device_id".to_string()], best["device_name".to_string()]));
            lines.push(format!("Overall Score: {}/100", best["total_score".to_string()]));
            lines.push(format!("  - Availability: {}/100", best["availability_score".to_string()]));
            lines.push(format!("  - Quality: {}/100", best["quality_score".to_string()]));
            lines.push(format!("  - Priority: {}/100", best["priority_score".to_string()]));
        }
        let mut procs = result["diagnostic".to_string()]["competing_processes".to_string()];
        if procs {
            let mut proc_names = procs.iter().map(|p| p["name".to_string()]).collect::<Vec<_>>().into_iter().collect::<HashSet<_>>().into_iter().collect::<Vec<_>>();
            lines.push(format!("\nAudio-using Processes ({}):", proc_names.len()));
            for name in proc_names[..5].iter() {
                lines.push(format!("  - {}", name));
            }
            if proc_names.len() > 5 {
                lines.push(format!("  ... and {} more", (proc_names.len() - 5)));
            }
        } else {
            lines.push(format!("\nNo competing audio processes detected"));
        }
        lines.push("\nRecommendations:".to_string());
        for rec in result["recommendations".to_string()].iter() {
            lines.push(format!("  {}", rec));
        }
        lines.join(&"\n".to_string())
    }
}

/// Record audio with healing part 1.
pub fn _record_audio_with_healing_part1(r#self: String, auto_fallback: String, duration: String, verbose: String) -> Result<()> {
    // Record audio with healing part 1.
    if auto_fallback {
        if verbose {
            logger.info("Running microphone healing...".to_string());
        }
        let mut result = self.diagnose_microphone(/* verbose= */ false);
        let mut best_device = result["diagnostic".to_string()]["best_device_id".to_string()];
        if (best_device.is_some() && best_device != self.device) {
            if verbose {
                let mut proc_count = result["diagnostic".to_string()]["competing_processes".to_string()].len();
                if proc_count > 0 {
                    logger.warning(format!("  {} audio-using processes detected", proc_count));
                }
                let mut device_name = result["diagnostic".to_string()]["best_device".to_string()]["device_name".to_string()];
                logger.info(format!("  Switching to device: {}", device_name));
            }
            let mut old_device = self.device;
            self.device = best_device;
            // try:
            {
                let mut audio = self.record_audio(/* duration= */ duration, /* auto_fallback= */ false);
                if audio {
                    if verbose {
                        logger.info("✓ Recording successful with alternative device".to_string());
                    }
                    audio
                }
            }
            // except Exception as e:
        }
    }
    logger.error("Could not record audio after healing attempts".to_string());
    None
    let record_audio_with_healing = |duration, auto_fallback, verbose| {
        // Record audio with automatic microphone healing.
        // 
        // If initial device fails:
        // 1. Check what's using microphone (process blocking?)
        // 2. Find alternative working device
        // 3. Use best available device automatically
        // 
        // Args:
        // duration: Recording duration in seconds
        // auto_fallback: Try alternative devices on failure
        // verbose: Print healing messages
        // 
        // Returns:
        // WAV audio bytes or None on failure
        if !self.healer {
            self.record_audio(/* duration= */ duration, /* auto_fallback= */ auto_fallback)
        }
        if verbose {
            logger.info("Recording audio with healing...".to_string());
        }
        // try:
        {
            let mut audio = self.record_audio(/* duration= */ duration, /* auto_fallback= */ false);
            if audio {
                if verbose {
                    logger.info("✓ Recording successful with current device".to_string());
                }
                audio
            }
        }
        // except Exception as e:
        _record_audio_with_healing_part1(self, auto_fallback, duration, verbose);
    };
    let get_health_report = || {
        // Get human-readable microphone health report.
        // 
        // Returns:
        // Multi-line health report
        if !self.healer {
            "Healer not available".to_string()
        }
        let mut result = self.healer.auto_heal_with_recommendations();
        let mut lines = vec![];
        lines.push(("=".to_string() * 70));
        lines.push("MICROPHONE HEALTH REPORT".to_string());
        lines.push(("=".to_string() * 70));
        let mut best = result["diagnostic".to_string()]["best_device".to_string()];
        if best {
            lines.push(format!("\nBest Device: {}", best["device_name".to_string()]));
            lines.push(format!("Score: {}/100", best["total_score".to_string()]));
            lines.push(format!("  - Availability: {}/100", best["availability_score".to_string()]));
            lines.push(format!("  - Quality: {}/100", best["quality_score".to_string()]));
            lines.push(format!("  - Priority: {}/100", best["priority_score".to_string()]));
        }
        let mut procs = result["diagnostic".to_string()]["competing_processes".to_string()];
        if procs {
            let mut proc_names = procs.iter().map(|p| p["name".to_string()]).collect::<Vec<_>>().into_iter().collect::<HashSet<_>>().into_iter().collect::<Vec<_>>();
            lines.push(format!("\nBlocking Processes ({}):", proc_names.len()));
            for name in proc_names[..5].iter() {
                lines.push(format!("  - {}", name));
            }
            if proc_names.len() > 5 {
                lines.push(format!("  ... and {} more", (proc_names.len() - 5)));
            }
        }
        lines.push("\nRecommendations:".to_string());
        for rec in result["recommendations".to_string()].iter() {
            lines.push(format!("  {}", rec));
        }
        lines.join(&"\n".to_string())
    Ok(})
}
