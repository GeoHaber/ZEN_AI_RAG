/// Production-Grade Microphone Self-Check & Self-Healing System
/// Based on industry best-practices from:
/// - OBS Studio (audio device management)
/// - FFmpeg (device detection & fallback)
/// - PulseAudio (device probing)
/// - Real-time audio frameworks
/// 
/// Features:
/// - Device lock detection (identifies which apps are using mic)
/// - Intelligent fallback with performance scoring
/// - Loopback verification (play->record->verify)
/// - Audio level optimization
/// - Self-healing with automatic recovery

use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Score a microphone device for quality and availability
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceScore {
    pub device_id: i64,
    pub device_name: String,
    pub availability_score: i64,
    pub quality_score: i64,
    pub priority_score: i64,
    pub availability_reason: String,
    pub quality_reason: String,
    pub priority_reason: String,
}

impl DeviceScore {
    /// Total score.
    pub fn total_score(&self) -> i64 {
        // Total score.
        (((self.availability_score * 0.5_f64) + (self.quality_score * 0.3_f64)) + (self.priority_score * 0.2_f64)).to_string().parse::<i64>().unwrap_or(0)
    }
    pub fn to_dict(&self) -> HashMap<String, Box<dyn std::any::Any>> {
        asdict(self)
    }
}

/// Detect which processes are using microphone.
/// Based on Windows API patterns used in OBS Studio.
#[derive(Debug, Clone)]
pub struct ProcessAudioUsageDetector {
}

impl ProcessAudioUsageDetector {
    /// Find Windows processes using microphone.
    /// Uses psutil + heuristics (not guaranteed to find all).
    pub fn find_processes_using_microphone() -> Result<Vec<HashMap<String, Box<dyn std::any::Any>>>> {
        // Find Windows processes using microphone.
        // Uses psutil + heuristics (not guaranteed to find all).
        let mut processes = vec![];
        // try:
        {
            let mut audio_apps = HashMap::from([("obs.exe".to_string(), "OBS Studio".to_string()), ("obs64.exe".to_string(), "OBS Studio (64-bit)".to_string()), ("zoom.exe".to_string(), "Zoom".to_string()), ("Teams.exe".to_string(), "Microsoft Teams".to_string()), ("skype.exe".to_string(), "Skype".to_string()), ("discord.exe".to_string(), "Discord".to_string()), ("slack.exe".to_string(), "Slack".to_string()), ("chrome.exe".to_string(), "Google Chrome".to_string()), ("firefox.exe".to_string(), "Mozilla Firefox".to_string()), ("brave.exe".to_string(), "Brave Browser".to_string()), ("edge.exe".to_string(), "Microsoft Edge".to_string()), ("audiodg.exe".to_string(), "Windows Audio Device Graph Isolation".to_string()), ("WaveOutMix.exe".to_string(), "Audio Mixer".to_string()), ("vlc.exe".to_string(), "VLC Media Player".to_string()), ("audacity.exe".to_string(), "Audacity".to_string())]);
            for proc in psutil.process_iter(vec!["pid".to_string(), "name".to_string(), "exe".to_string()]).iter() {
                // try:
                {
                    let mut name = proc.info["name".to_string()].to_lowercase();
                    for (app_exe, app_name) in audio_apps.iter().iter() {
                        if !name.contains(&app_exe.to_lowercase()) {
                            continue;
                        }
                        processes.push(HashMap::from([("pid".to_string(), proc.info["pid".to_string()]), ("name".to_string(), app_name), ("executable".to_string(), proc.info["name".to_string()]), ("status".to_string(), "possibly_using_audio".to_string())]));
                        break;
                    }
                }
                // except (psutil.NoSuchProcess, psutil.AccessDenied) as _e:
            }
        }
        // except Exception as e:
        Ok(processes)
    }
}

/// Enterprise-grade microphone diagnostic and auto-healing system.
#[derive(Debug, Clone)]
pub struct ProductionMicrophoneHealer {
    pub timeout_sec: String,
    pub test_frequency: i64,
    pub process_detector: ProcessAudioUsageDetector,
}

impl ProductionMicrophoneHealer {
    pub fn new(timeout_sec: f64) -> Self {
        Self {
            timeout_sec,
            test_frequency: 1000,
            process_detector: ProcessAudioUsageDetector(),
        }
    }
    /// Generate a pure sine wave for loopback testing.
    pub fn generate_test_tone(&self, frequency: f64, duration: f64) -> Result<Vec<u8>> {
        // Generate a pure sine wave for loopback testing.
        let mut sample_rate = 16000;
        let mut t = numpy.linspace(0, duration, (sample_rate * duration).to_string().parse::<i64>().unwrap_or(0));
        let mut audio = (0.2_f64 * numpy.sin((((2 * numpy.pi) * frequency) * t)).astype(numpy.float32));
        let mut wav_buffer = io.BytesIO();
        wavfile.write(wav_buffer, sample_rate, (audio * 32767).astype("int16".to_string()));
        Ok(wav_buffer.getvalue())
    }
    /// Check if device is locked by another process.
    /// Returns (is_locked, reason_or_none)
    pub fn is_device_locked(&mut self, device_id: i64) -> Result<(bool, Option<String>)> {
        // Check if device is locked by another process.
        // Returns (is_locked, reason_or_none)
        // try:
        {
            let mut dev_info = sounddevice.query_devices(device_id);
            let mut channels = 1.min(dev_info.get(&"max_input_channels".to_string()).cloned().unwrap_or(1).to_string().parse::<i64>().unwrap_or(0));
            if channels < 1 {
                let mut channels = 1;
            }
            let mut stream = sounddevice.InputStream(/* device= */ device_id, /* channels= */ channels, /* samplerate= */ 16000, /* latency= */ "low".to_string());
            stream.start();
            stream.stop();
            stream.close();
            (false, None)
        }
        // except RuntimeError as e:
        // except Exception as e:
    }
    /// Measure audio quality (0-100 score).
    /// Uses signal-to-noise ratio heuristics.
    /// 
    /// Returns (quality_score, reason)
    pub fn measure_audio_quality(&self, device_id: i64, duration: f64) -> Result<(i64, String)> {
        // Measure audio quality (0-100 score).
        // Uses signal-to-noise ratio heuristics.
        // 
        // Returns (quality_score, reason)
        // try:
        {
            let mut recording = sounddevice.rec((duration * 16000).to_string().parse::<i64>().unwrap_or(0), /* samplerate= */ 16000, /* channels= */ 1, /* device= */ device_id, /* dtype= */ "float32".to_string());
            sounddevice.wait();
            let mut rms = numpy.sqrt(numpy.mean((recording).pow(2 as u32)));
            if rms > 0.3_f64 {
                (100, "Excellent - strong audio signal".to_string())
            } else if rms > 0.1_f64 {
                (85, "Good - clear audio".to_string())
            } else if rms > 0.05_f64 {
                (60, "Fair - somewhat quiet".to_string())
            } else if rms > 0.01_f64 {
                (40, "Poor - very quiet".to_string())
            } else {
                (0, "Silent - no audio detected".to_string())
            }
        }
        // except Exception as e:
    }
    /// Play a test tone and listen for it on same device.
    /// 
    /// Returns (success, confidence_0_to_1, reason)
    pub fn verify_loopback(&mut self, device_id: i64) -> Result<(bool, f64, String)> {
        // Play a test tone and listen for it on same device.
        // 
        // Returns (success, confidence_0_to_1, reason)
        // try:
        {
            let mut tone_bytes = self.generate_test_tone(/* frequency= */ 1000, /* duration= */ 0.2_f64);
            let mut wav_buffer = io.BytesIO(tone_bytes);
            let (mut rate, mut tone_data) = wavfile.read(wav_buffer);
            let mut tone_float = (tone_data.astype(numpy.float32) / 32768.0_f64);
            let mut sample_rate = 16000;
            let mut recording = sounddevice.rec((0.5_f64 * sample_rate).to_string().parse::<i64>().unwrap_or(0), /* samplerate= */ sample_rate, /* channels= */ 1, /* device= */ device_id, /* dtype= */ "float32".to_string());
            sounddevice.play(tone_float, /* samplerate= */ sample_rate, /* device= */ device_id);
            sounddevice.wait();
            let mut recording = recording.flatten();
            let mut fft = numpy.fft.fft(recording);
            let mut freqs = numpy.fft.fftfreq(fft.len(), (1 / sample_rate));
            let mut freq_mask = (freqs > 900 & freqs < 1100);
            if numpy.any(freq_mask) {
                let mut peak_bin = numpy.argmax(numpy.abs(fft[&freq_mask]));
                let mut peak_val = numpy.abs(fft[&freq_mask])[&peak_bin];
                let mut noise_floor = numpy.median(numpy.abs(fft[!freq_mask]));
                let mut snr = (peak_val / (noise_floor + 1e-10_f64));
                let mut confidence = 1.0_f64.min((snr / 100.0_f64));
                if confidence > 0.7_f64 {
                    (true, confidence, "Loopback verified".to_string())
                } else {
                    (true, confidence, format!("Loopback detected (SNR: {:.1})", snr))
                }
            }
            (false, 0.0_f64, "No loopback detected".to_string())
        }
        // except Exception as e:
    }
    /// Score a device (0-100) based on:
    /// - Availability (is it free?)
    /// - Quality (how good is audio?)
    /// - Priority (is it preferred?)
    pub fn score_device(&mut self, device_id: i64) -> DeviceScore {
        // Score a device (0-100) based on:
        // - Availability (is it free?)
        // - Quality (how good is audio?)
        // - Priority (is it preferred?)
        let mut dev_info = sounddevice.query_devices(device_id);
        let mut device_name = dev_info["name".to_string()];
        let mut score = DeviceScore(/* device_id= */ device_id, /* device_name= */ device_name);
        let (mut is_locked, mut lock_reason) = self.is_device_locked(device_id);
        if is_locked {
            score.availability_score = 0;
            score.availability_reason = (lock_reason || "Device locked".to_string());
        } else {
            score.availability_score = 100;
            score.availability_reason = "Device available".to_string();
        }
        if !is_locked {
            let (mut quality, mut quality_reason) = self.measure_audio_quality(device_id, /* duration= */ 0.5_f64);
            score.quality_score = quality;
            score.quality_reason = quality_reason;
        }
        if device_name.to_lowercase().contains(&"logi".to_string()) {
            score.priority_score = 100;
            score.priority_reason = "Logitech device (preferred)".to_string();
        } else if device_name.to_lowercase().contains(&"microphone".to_string()) {
            score.priority_score = 80;
            score.priority_reason = "Labeled as microphone".to_string();
        } else if device_name.to_lowercase().contains(&"audio".to_string()) {
            score.priority_score = 60;
            score.priority_reason = "Generic audio device".to_string();
        } else {
            score.priority_score = 30;
            score.priority_reason = "Unrecognized device".to_string();
        }
        score
    }
}

/// Helper: setup phase for _do_full_diagnostic_setup.
pub fn _do_do_full_diagnostic_setup_setup(verbose: String) -> () {
    // Helper: setup phase for _do_full_diagnostic_setup.
    if verbose {
        println!("{}", "\n[DIAGNOSTIC] MICROPHONE SYSTEM".to_string());
        println!("{}", ("=".to_string() * 70));
    }
    let mut all_devices = sounddevice.query_devices();
    let mut input_devices = all_devices.iter().enumerate().iter().filter(|(i, d)| d["max_input_channels".to_string()] > 0).map(|(i, d)| (i, d)).collect::<Vec<_>>();
    if verbose {
        println!("\n[INFO] Found {} input device(s)", input_devices.len());
    }
    let mut device_scores = vec![];
    for (dev_id, dev_info) in input_devices.iter() {
        if verbose {
            println!("\n  Testing device #{}: {}", dev_id, dev_info["name".to_string()]);
        }
        let mut score = self.score_device(dev_id);
        device_scores.push(score);
        if verbose {
            println!("    Availability: {}/100 - {}", score.availability_score, score.availability_reason);
            println!("    Quality: {}/100 - {}", score.quality_score, score.quality_reason);
            println!("    Priority: {}/100 - {}", score.priority_score, score.priority_reason);
            println!("    TOTAL: {}/100", score.total_score);
        }
    }
    device_scores
    device_scores
}

/// Do full diagnostic setup part 1.
pub fn _do_full_diagnostic_setup_part1() -> () {
    // Do full diagnostic setup part 1.
    let mut diag = self.full_diagnostic(/* verbose= */ true);
    let mut recommendations = vec![];
    let mut best_score = diag["best_device_id".to_string()];
    if best_score.is_none() {
        recommendations.push("[ERROR] No input devices found! Connect a microphone.".to_string());
    } else if diag["devices".to_string()][0]["availability_score".to_string()] < 100 {
        let mut processes = diag["competing_processes".to_string()];
        if processes {
            let mut proc_names = processes.iter().map(|p| p["name".to_string()]).collect::<Vec<_>>();
            let mut proc_names = dict.fromkeys(proc_names).into_iter().collect::<Vec<_>>();
            recommendations.push(format!("[ACTION] Microphone locked by: {}. Close these apps to use the microphone in ZEN_AI.", proc_names[..5].join(&", ".to_string())));
        } else {
            recommendations.push("[ACTION] Microphone device is locked (unknown process). Check Windows audio settings or restart your system.".to_string());
        }
    } else if diag["devices".to_string()][0]["quality_score".to_string()] < 50 {
        recommendations.push("[ACTION] Microphone audio quality is very low. Increase microphone volume in Windows Sound Mixer (Right-click speaker icon).".to_string());
    } else if diag["devices".to_string()][0]["quality_score".to_string()] < 80 {
        recommendations.push("[ACTION] Microphone audio could be better. Consider increasing microphone gain in system settings.".to_string());
    } else {
        recommendations.push("[OK] Microphone system is healthy and ready to use!".to_string());
    }
    println!("\n[ADVICE] RECOMMENDATIONS:");
    for rec in recommendations.iter() {
        println!("  {}", rec);
    }
    HashMap::from([("diagnostic".to_string(), diag), ("recommendations".to_string(), recommendations), ("status".to_string(), if diag["devices".to_string()][0]["availability_score".to_string()] == 100 { "OK".to_string() } else { "NEEDS_ATTENTION".to_string() })])
}

/// Helper: setup phase for full_diagnostic.
pub fn _do_full_diagnostic_setup(verbose: String) -> () {
    // Helper: setup phase for full_diagnostic.
    _do_do_full_diagnostic_setup_setup(verbose);
    let full_diagnostic = |verbose| {
        // Run complete system diagnostic.
        // 
        // Returns comprehensive analysis with recommendations.
        let mut device_scores = _do_full_diagnostic_setup(verbose);
        device_scores.sort(/* key= */ |s| s.total_score, /* reverse= */ true);
        let mut best_device = if device_scores { device_scores[0] } else { None };
        if (verbose && best_device) {
            println!("\n[BEST] Device #{} - {}", best_device.device_id, best_device.device_name);
            println!("  Score: {}/100", best_device.total_score);
        }
        if verbose {
            let mut processes = self.process_detector.find_processes_using_microphone();
            if processes {
                println!("\n[WARNING] Audio-using processes detected:");
                for proc in processes[..10].iter() {
                    println!("    * {} (PID: {})", proc["name".to_string()], proc["pid".to_string()]);
                }
                if processes.len() > 10 {
                    println!("    ... and {} more", (processes.len() - 10));
                }
            } else {
                println!("\n[OK] No other audio-using processes detected");
            }
        }
        HashMap::from([("devices".to_string(), device_scores.iter().map(|s| s.to_dict()).collect::<Vec<_>>()), ("best_device".to_string(), if best_device { best_device.to_dict() } else { None }), ("best_device_id".to_string(), if best_device { best_device.device_id } else { None }), ("competing_processes".to_string(), self.process_detector.find_processes_using_microphone()), ("total_devices".to_string(), device_scores.len())])
    };
    let auto_heal_with_recommendations = || {
        // Run diagnostics and provide actionable recommendations.
        println!("{}", "\n[HEALING] MICROPHONE AUTO-HEALING SYSTEM".to_string());
        println!("{}", ("=".to_string() * 70));
    };
    _do_full_diagnostic_setup_part1();
}
