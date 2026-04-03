/// Debug Audio Panel for ZEN_AI_RAG UI
/// Allows testing audio injection in the interface

use anyhow::{Result, Context};
use crate::injectable_voice::{InjectableVoiceManager, create_audio_test_panel};
use tokio;

pub static VOICE_MANAGER: std::sync::LazyLock<InjectableVoiceManager> = std::sync::LazyLock::new(|| Default::default());

/// Helper: setup phase for debug_audio_page.
pub fn _do_debug_audio_page_setup() -> () {
    // Helper: setup phase for debug_audio_page.
    ui.add_head_html("\n    <style>\n        .debug-panel {\n            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n            color: white;\n            border-radius: 10px;\n            padding: 20px;\n            margin: 10px 0;\n        }\n    </style>\n    ".to_string());
}

/// Debug audio page part 1.
pub fn _debug_audio_page_part1() -> () {
    // Debug audio page part 1.
    let _ctx = ui.row().classes("gap-4 items-start".to_string());
    let _ctx = ui.card().classes("w-full".to_string());
    {
        ui.label("🚀 Quick Start".to_string()).classes("font-bold".to_string());
        ui.label("1. Click \"🗣️ Voice-like\" to inject test audio".to_string());
        ui.label("2. Click \"🎙️ Record Audio\" to test recording".to_string());
        ui.label("3. If successful, real microphone should also work".to_string());
    }
}

/// Debug page for audio testing
pub async fn debug_audio_page() -> Result<()> {
    // Debug page for audio testing
    _do_debug_audio_page_setup();
    let _ctx = ui.column().classes("w-full gap-4 p-4".to_string());
    {
        let _ctx = ui.row().classes("items-center gap-3".to_string());
        {
            ui.icon("bug_report".to_string()).classes("text-3xl".to_string());
            ui.label("🔧 Audio Debug Panel".to_string()).classes("text-2xl font-bold".to_string());
        }
        ui.separator();
        let _ctx = ui.card().classes("w-full bg-blue-50 border-l-4 border-blue-500".to_string());
        {
            ui.label("📡 Audio Injection (Test Mode)".to_string()).classes("text-lg font-bold text-blue-900".to_string());
            let _ctx = ui.row().classes("gap-2 flex-wrap".to_string());
            {
                let inject_sine = || {
                    voice_manager::enable_injection("sine".to_string());
                    ui.notify("🎵 Injecting 1kHz sine wave".to_string(), /* type= */ "info".to_string());
                };
                let inject_noise = || {
                    voice_manager::enable_injection("noise".to_string());
                    ui.notify("🌊 Injecting white noise".to_string(), /* type= */ "info".to_string());
                };
                let inject_voice = || {
                    voice_manager::enable_injection("voice".to_string());
                    ui.notify("🗣️ Injecting voice-like audio".to_string(), /* type= */ "info".to_string());
                };
                let use_real_mic = || {
                    voice_manager::disable_injection();
                    ui.notify("🎤 Using real microphone".to_string(), /* type= */ "info".to_string());
                };
                ui.button("🎵 1kHz Sine".to_string(), /* on_click= */ inject_sine).props("color=blue".to_string());
                ui.button("🌊 White Noise".to_string(), /* on_click= */ inject_noise).props("color=cyan".to_string());
                ui.button("🗣️ Voice-like".to_string(), /* on_click= */ inject_voice).props("color=green".to_string());
                ui.button("🎤 Real Mic".to_string(), /* on_click= */ use_real_mic).props("color=gray".to_string());
            }
            let mut status_display = ui.label("Status: Ready".to_string());
            status_display.classes("text-sm text-gray-700 mt-2".to_string());
            let update_injection_status = || {
                // Update injection status.
                let mut status = voice_manager::get_injection_status();
                if status["enabled".to_string()] {
                    let mut label = status["last_injection".to_string()].get(&"label".to_string()).cloned().unwrap_or("Injected".to_string());
                    status_display.text = format!("✓ Audio Injection ON ({})", label);
                    status_display.classes("text-green-700 font-bold".to_string(), /* remove= */ "text-gray-700".to_string());
                } else {
                    status_display.text = "⚪ Using real microphone".to_string();
                    status_display.classes("text-gray-700".to_string(), /* remove= */ "text-green-700 font-bold".to_string());
                }
            };
            ui.timer(0.5_f64, update_injection_status);
        }
        let _ctx = ui.card().classes("w-full bg-purple-50 border-l-4 border-purple-500".to_string());
        {
            ui.label("🎙️ Test Recording".to_string()).classes("text-lg font-bold text-purple-900".to_string());
            let mut duration_slider = ui.slider(/* min= */ 1, /* max= */ 10, /* value= */ 2).props("label".to_string());
            duration_slider.bind_value_to(duration_slider, "label".to_string(), |x| format!("Duration: {}s", x));
            let mut recording_result = ui.label("Ready to record".to_string());
            let test_record = || {
                // Test record.
                recording_result.text = format!("🔄 Recording {}s...", duration_slider.value.to_string().parse::<i64>().unwrap_or(0));
                recording_result.classes("text-yellow-700".to_string());
                recording_result.update();
                // try:
                {
                    let mut result = voice_manager::record_audio(/* duration= */ duration_slider.value);
                    if result.success {
                        recording_result.text = format!("✓ Recorded {} bytes at {}Hz", result.audio_data.len(), result.sample_rate);
                        recording_result.classes("text-green-700 font-bold".to_string(), /* remove= */ "text-yellow-700".to_string());
                        ui.notify(format!("✓ Recording successful ({} bytes)", result.audio_data.len()), /* type= */ "positive".to_string());
                    } else {
                        recording_result.text = format!("✗ Recording failed: {}", result.error);
                        recording_result.classes("text-red-700".to_string(), /* remove= */ "text-yellow-700".to_string());
                        ui.notify(format!("✗ {}", result.error), /* type= */ "negative".to_string());
                    }
                }
                // except Exception as e:
            };
            let _ctx = ui.row().classes("gap-2".to_string());
            {
                ui.button("🎙️ Record Audio".to_string(), /* on_click= */ test_record).props("color=purple".to_string());
            }
            recording_result.classes("text-sm mt-2".to_string());
        }
        let _ctx = ui.card().classes("w-full bg-green-50 border-l-4 border-green-500".to_string());
        {
            ui.label("📊 Device Information".to_string()).classes("text-lg font-bold text-green-900".to_string());
            let mut devices = voice_manager::enumerate_devices();
            let mut input_devices = devices.iter().filter(|d| d.is_input).map(|d| d).collect::<Vec<_>>();
            let mut output_devices = devices.iter().filter(|d| d.is_output).map(|d| d).collect::<Vec<_>>();
            ui.label(format!("Input Devices: {}", input_devices.len()));
            ui.label(format!("Output Devices: {}", output_devices.len()));
            let _ctx = ui.expansion("Show Device List".to_string()).classes("w-full".to_string());
            {
                for dev in input_devices[..5].iter() {
                    ui.label(format!("🎤 [{}] {} ({}ch, {}Hz)", dev.id, dev.name, dev.channels, dev.default_sample_rate.to_string().parse::<i64>().unwrap_or(0)));
                }
            }
        }
        let _ctx = ui.card().classes("w-full bg-yellow-50 border-l-4 border-yellow-500".to_string());
        {
            ui.label("💡 Troubleshooting Tips".to_string()).classes("text-lg font-bold text-yellow-900".to_string());
            let mut tips = vec![("Microphone not responding?".to_string(), "Try injecting audio first to test if UI works".to_string()), ("Still no audio in chat?".to_string(), "Check Windows Volume Mixer (right-click speaker icon)".to_string()), ("Permission denied?".to_string(), "Reload page and allow microphone access when prompted".to_string()), ("Only silence recorded?".to_string(), "Increase microphone volume in system settings".to_string())];
            for (question, answer) in tips.iter() {
                let _ctx = ui.expansion(question).classes("text-sm".to_string());
                {
                    ui.label(answer).classes("text-gray-700".to_string());
                }
            }
        }
        ui.separator();
    }
    Ok(_debug_audio_page_part1())
}
