/// Self-Checking & Self-Healing Microphone System
/// Comprehensive diagnostics + auto-recovery for ZEN_AI audio

use anyhow::{Result, Context};
use std::collections::HashMap;
use std::collections::HashSet;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Professional microphone diagnostics and self-healing system.
/// 
/// Features:
/// - Device lock detection (other apps using mic)
/// - Loopback test (play beep, record it back)
/// - Audio level verification
/// - Automatic device switching
/// - Self-healing on failure
#[derive(Debug, Clone)]
pub struct MicrophoneHealer {
    pub test_results: HashMap<String, serde_json::Value>,
    pub device_status: HashMap<String, serde_json::Value>,
    pub locked_devices: HashSet<String>,
    pub working_device: Option<serde_json::Value>,
}

impl MicrophoneHealer {
    /// Initialize instance.
    pub fn new() -> Self {
        Self {
            test_results: HashMap::new(),
            device_status: HashMap::new(),
            locked_devices: HashSet::new(),
            working_device: None,
        }
    }
    /// Generate a test beep sound.
    pub fn generate_test_beep(&self, frequency: f64, duration: f64) -> Result<Vec<u8>> {
        // Generate a test beep sound.
        let mut sample_rate = 16000;
        let mut t = numpy.linspace(0, duration, (sample_rate * duration).to_string().parse::<i64>().unwrap_or(0));
        let mut audio = (0.3_f64 * numpy.sin((((2 * numpy.pi) * frequency) * t)).astype(numpy.float32));
        let mut wav_buffer = io.BytesIO();
        wavfile.write(wav_buffer, sample_rate, (audio * 32767).astype("int16".to_string()));
        Ok(wav_buffer.getvalue())
    }
    /// Test if a device is available (not locked by another app).
    /// 
    /// Returns:
    /// {
    /// 'available': bool,
    /// 'error': str or None,
    /// 'device_name': str,
    /// 'reason': str
    /// }
    pub fn test_device_availability(&self, device_id: i64, timeout: f64) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
        // Test if a device is available (not locked by another app).
        // 
        // Returns:
        // {
        // 'available': bool,
        // 'error': str or None,
        // 'device_name': str,
        // 'reason': str
        // }
        // try:
        {
            let mut dev_info = sounddevice.query_devices(device_id);
            // try:
            {
                let mut stream = sounddevice.OutputStream(/* device= */ device_id, /* channels= */ 1, /* samplerate= */ 16000, /* latency= */ "low".to_string());
                stream.start();
                stream.stop();
                stream.close();
                HashMap::from([("available".to_string(), true), ("error".to_string(), None), ("device_name".to_string(), dev_info["name".to_string()]), ("reason".to_string(), "Device is available".to_string())])
            }
            // except Exception as e:
        }
        // except Exception as e:
    }
    /// Loopback test: Play beep + record it back.
    /// 
    /// Returns:
    /// {
    /// 'success': bool,
    /// 'beep_detected': bool,
    /// 'audio_level': float,
    /// 'frequency': float,
    /// 'error': str or None
    /// }
    pub fn loopback_test(&mut self, device_id: i64, timeout: f64) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
        // Loopback test: Play beep + record it back.
        // 
        // Returns:
        // {
        // 'success': bool,
        // 'beep_detected': bool,
        // 'audio_level': float,
        // 'frequency': float,
        // 'error': str or None
        // }
        // try:
        {
            let mut beep_bytes = self.generate_test_beep(/* frequency= */ 1000, /* duration= */ 0.5_f64);
            let mut sample_rate = 16000;
            let mut beep_wav = io.BytesIO(beep_bytes);
            let (mut rate, mut beep_data) = wavfile.read(beep_wav);
            let mut beep_float = (beep_data.astype(numpy.float32) / 32768.0_f64);
            let mut duration = 1.0_f64;
            let mut recording = sounddevice.rec((duration * sample_rate).to_string().parse::<i64>().unwrap_or(0), /* samplerate= */ sample_rate, /* channels= */ 1, /* device= */ device_id, /* dtype= */ "float32".to_string());
            sounddevice.play(beep_float, /* samplerate= */ sample_rate, /* device= */ device_id);
            sounddevice.wait();
            let mut recording = recording.flatten();
            let mut audio_level = numpy.max(numpy.abs(recording));
            let mut fft = numpy.fft.fft(recording);
            let mut freqs = numpy.fft.fftfreq(fft.len(), (1 / sample_rate));
            let mut freq_range = numpy.where((freqs > 800 & freqs < 1200))[0];
            if freq_range.len() > 0 {
                let mut peak_idx = freq_range[&numpy.argmax(numpy.abs(fft[&freq_range]))];
                let mut peak_freq = freqs[&peak_idx];
            } else {
                let mut peak_freq = 0;
            }
            let mut beep_detected = (peak_freq > 800 && peak_freq < 1200);
            HashMap::from([("success".to_string(), true), ("beep_detected".to_string(), beep_detected), ("audio_level".to_string(), audio_level.to_string().parse::<f64>().unwrap_or(0.0)), ("frequency".to_string(), peak_freq.to_string().parse::<f64>().unwrap_or(0.0)), ("error".to_string(), None)])
        }
        // except Exception as e:
    }
    /// Check if microphone captures real audio (not just silence).
    /// 
    /// Returns:
    /// {
    /// 'success': bool,
    /// 'level': float (0-1),
    /// 'quality': 'EXCELLENT' | 'GOOD' | 'LOW' | 'SILENT',
    /// 'error': str or None
    /// }
    pub fn audio_level_check(&self, device_id: i64, duration: f64) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
        // Check if microphone captures real audio (not just silence).
        // 
        // Returns:
        // {
        // 'success': bool,
        // 'level': float (0-1),
        // 'quality': 'EXCELLENT' | 'GOOD' | 'LOW' | 'SILENT',
        // 'error': str or None
        // }
        // try:
        {
            let mut recording = sounddevice.rec((duration * 16000).to_string().parse::<i64>().unwrap_or(0), /* samplerate= */ 16000, /* channels= */ 1, /* device= */ device_id, /* dtype= */ "float32".to_string());
            sounddevice.wait();
            let mut level = numpy.max(numpy.abs(recording));
            if level > 0.3_f64 {
                let mut quality = "EXCELLENT".to_string();
            } else if level > 0.1_f64 {
                let mut quality = "GOOD".to_string();
            } else if level > 0.01_f64 {
                let mut quality = "LOW".to_string();
            } else {
                let mut quality = "SILENT".to_string();
            }
            HashMap::from([("success".to_string(), true), ("level".to_string(), level.to_string().parse::<f64>().unwrap_or(0.0)), ("quality".to_string(), quality), ("error".to_string(), None)])
        }
        // except Exception as e:
    }
}

/// Full diagnostic part3 part 4.
pub fn _full_diagnostic_part3_part4(r#self: String) -> () {
    // Full diagnostic part3 part 4.
    if !avail["available".to_string()] {
        results["recommendations".to_string()].push(format!("Device is locked: {}. Close other apps using this microphone.", avail["reason".to_string()]));
    }
    println!("  [2/3] Testing audio level (2 seconds, speak now!)...");
    let mut level = self.audio_level_check(device_id, /* duration= */ 2);
    results["tests".to_string()]["audio_level".to_string()] = level;
    println!("    ✓ Level: {:.4} ({})", level["level".to_string()], level["quality".to_string()]);
    if level["quality".to_string()] == "SILENT".to_string() {
        results["recommendations".to_string()].push("Microphone is capturing silence. Check Windows Volume Mixer - increase microphone volume.".to_string());
    } else if level["quality".to_string()] == "LOW".to_string() {
        results["recommendations".to_string()].push("Audio level is very low. Increase microphone volume in system settings.".to_string());
    }
    println!("  [3/3] Testing loopback (play beep and record)...");
    let mut loopback = self.loopback_test(device_id, /* timeout= */ 3);
    results["tests".to_string()]["loopback".to_string()] = loopback;
    if loopback["success".to_string()] {
        if loopback["beep_detected".to_string()] {
            println!("    ✓ Beep detected at {:.0}Hz", loopback["frequency".to_string()]);
        } else {
            println!("    ⚠️ No beep detected (audio level: {:.4})", loopback["audio_level".to_string()]);
            results["recommendations".to_string()].push("Loopback test failed - microphone may be muted or disconnected.".to_string());
        }
    } else {
        println!("    ✗ Loopback failed: {}", loopback["error".to_string()][..50]);
        results["recommendations".to_string()].push(format!("Loopback test error: {}", loopback["error".to_string()][..100]));
    }
    _full_diagnostic_part3(self);
}

/// Full diagnostic part 3.
pub fn _full_diagnostic_part3(r#self: String) -> () {
    // Full diagnostic part 3.
    if (avail["available".to_string()] && ("EXCELLENT".to_string(), "GOOD".to_string()).contains(&level["quality".to_string()])) {
        results["overall_status".to_string()] = "OK".to_string();
    } else if (avail["available".to_string()] && ("LOW".to_string()).contains(&level["quality".to_string()])) {
        results["overall_status".to_string()] = "DEGRADED".to_string();
    } else {
        results["overall_status".to_string()] = "FAILED".to_string();
    }
    results
    let full_diagnostic = |device_id| {
        // Run full microphone diagnostic.
        // 
        // Returns:
        // {
        // 'device_id': int,
        // 'device_name': str,
        // 'overall_status': 'OK' | 'DEGRADED' | 'FAILED',
        // 'tests': {
        // 'availability': {...},
        // 'audio_level': {...},
        // 'loopback': {...}
        // },
        // 'recommendations': [str, ...],
        // 'timestamp': float
        // }
        if device_id.is_none() {
            let mut device_id = sounddevice.default.device[0];
        }
        let mut results = HashMap::from([("device_id".to_string(), device_id), ("device_name".to_string(), sounddevice.query_devices(device_id)["name".to_string()]), ("timestamp".to_string(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64()), ("tests".to_string(), HashMap::new()), ("recommendations".to_string(), vec![])]);
        println!("\n  [1/3] Testing device availability...");
        let mut avail = self.test_device_availability(device_id);
        results["tests".to_string()]["availability".to_string()] = avail;
        println!("    {} {}", if avail["available".to_string()] { "✓".to_string() } else { "✗".to_string() }, avail["reason".to_string()]);
    };
    _full_diagnostic_part3_part4(self);
}

/// Auto heal part1 part 2.
pub fn _auto_heal_part1_part2(r#self: String) -> () {
    // Auto heal part1 part 2.
    println!("{}", "\n🔧 AUTO-HEALING MICROPHONE SYSTEM".to_string());
    println!("{}", ("=".to_string() * 60));
    println!("{}", "\n[1] Discovering audio devices...".to_string());
    let mut devices = sounddevice.query_devices();
    let mut input_devices = devices.iter().enumerate().iter().filter(|(i, d)| d["max_input_channels".to_string()] > 0).map(|(i, d)| i).collect::<Vec<_>>();
    println!("  ✓ Found {} input device(s)", input_devices.len());
    actions::push(format!("Discovered {} input devices", input_devices.len()));
    let mut default_dev = sounddevice.default.device[0];
    println!("\n[2] Testing default device (#{})...", default_dev);
    let mut diag = self.full_diagnostic(default_dev);
    if diag["overall_status".to_string()] == "OK".to_string() {
        println!("  ✓ Default device is OK!");
        HashMap::from([("healed".to_string(), true), ("working_device".to_string(), default_dev), ("actions_taken".to_string(), (actions + vec!["Default device is healthy".to_string()])), ("status".to_string(), "OK".to_string())])
    }
    actions::push(format!("Default device status: {}", diag["overall_status".to_string()]));
    println!("\n[3] Trying alternate Logi devices...");
    let mut logi_devices = input_devices.iter().filter(|i| devices[&i]["name".to_string()].to_lowercase().contains(&"logi".to_string())).map(|i| i).collect::<Vec<_>>();
    for dev_id in logi_devices.iter() {
        if dev_id == default_dev {
            continue;
        }
        println!("  Trying device #{}: {}", dev_id, devices[&dev_id]["name".to_string()]);
        let mut avail = self.test_device_availability(dev_id);
        if avail["available".to_string()] {
            let mut level = self.audio_level_check(dev_id, /* duration= */ 1);
            if ("EXCELLENT".to_string(), "GOOD".to_string()).contains(&level["quality".to_string()]) {
                println!("  ✓ Found working device!");
                actions::push(format!("Switched to device #{}", dev_id));
                HashMap::from([("healed".to_string(), true), ("working_device".to_string(), dev_id), ("actions_taken".to_string(), actions), ("status".to_string(), "RECOVERED".to_string())])
            }
        }
    }
    actions::push("Could not find alternate working device".to_string());
    _auto_heal_part1(self);
}

/// Auto heal part 1.
pub fn _auto_heal_part1(r#self: String) -> () {
    // Auto heal part 1.
    println!("\n[4] Trying all other input devices...");
    for dev_id in input_devices.iter() {
        if (logi_devices.contains(&dev_id) || dev_id == default_dev) {
            continue;
        }
        let mut avail = self.test_device_availability(dev_id);
        if avail["available".to_string()] {
            let mut level = self.audio_level_check(dev_id, /* duration= */ 1);
            if ("EXCELLENT".to_string(), "GOOD".to_string()).contains(&level["quality".to_string()]) {
                println!("  ✓ Found working device: {}", avail["device_name".to_string()]);
                actions::push(format!("Fallback to device #{}", dev_id));
                HashMap::from([("healed".to_string(), true), ("working_device".to_string(), dev_id), ("actions_taken".to_string(), actions), ("status".to_string(), "FALLBACK".to_string())])
            }
        }
    }
    println!("\n[5] Healing failed. Recommendations:");
    for rec in diag["recommendations".to_string()].iter() {
        println!("  • {}", rec);
    }
    HashMap::from([("healed".to_string(), false), ("working_device".to_string(), None), ("actions_taken".to_string(), actions), ("status".to_string(), "FAILED - See recommendations".to_string())])
    let auto_heal = || {
        // Automatically diagnose and heal microphone issues.
        // 
        // Returns:
        // {
        // 'healed': bool,
        // 'working_device': int or None,
        // 'actions_taken': [str, ...],
        // 'status': str
        // }
    };
    _auto_heal_part1_part2(self);
}
