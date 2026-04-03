/// Microphone Permission Checker for NiceGUI
/// Tests browser microphone access and displays status

use anyhow::{Result, Context};
use tokio;

/// Add a microphone permission check widget to the UI.
/// 
/// Args:
/// ui: NiceGUI ui module
/// container: Parent container to add the check to
pub fn add_microphone_permission_check(ui: String, container: String) -> () {
    // Add a microphone permission check widget to the UI.
    // 
    // Args:
    // ui: NiceGUI ui module
    // container: Parent container to add the check to
    let mut check_mic_permission_js = "\n    async function checkMicrophonePermission() {\n        try {\n            // Check if mediaDevices API is available\n            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {\n                return {\n                    status: 'error',\n                    message: 'MediaDevices API not supported',\n                    icon: '❌'\n                };\n            }\n            \n            // Request microphone permission\n            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });\n            \n            // Clean up - stop the stream\n            stream.getTracks().forEach(track => track.stop());\n            \n            // Enumerate devices to get more info\n            const devices = await navigator.mediaDevices.enumerateDevices();\n            const audioInputs = devices.filter(dev => dev.kind === 'audioinput');\n            \n            return {\n                status: 'success',\n                message: `Microphone access granted (${audioInputs.length} device(s))`,\n                icon: '✓',\n                devices: audioInputs.length\n            };\n        } catch (error) {\n            let message = 'Microphone access denied';\n            \n            if (error.name === 'NotAllowedError') {\n                message = 'Microphone permission denied by user';\n            } else if (error.name === 'NotFoundError') {\n                message = 'No microphone found on this device';\n            } else if (error.name === 'NotReadableError') {\n                message = 'Microphone in use by another application';\n            } else if (error.name === 'SecurityError') {\n                message = 'HTTPS required for microphone access';\n            }\n            \n            return {\n                status: 'denied',\n                message: message,\n                icon: '🔇',\n                error: error.name\n            };\n        }\n    }\n    \n    checkMicrophonePermission();\n    ".to_string();
    let _ctx = container;
    {
        let mut status_label = ui.label().classes("text-sm font-medium".to_string());
        let check_microphone = || {
            // Check microphone.
            status_label.text = "🔄 Checking microphone access...".to_string();
            status_label.update();
            let mut result = ui.run_javascript(check_mic_permission_js).await;
            if result["status".to_string()] == "success".to_string() {
                status_label.text = format!("✓ Microphone Ready ({} device(s))", result["devices".to_string()]);
                status_label.classes("text-green-600".to_string());
                ui.notify("Microphone access granted!".to_string(), /* type= */ "positive".to_string());
            } else if result["status".to_string()] == "denied".to_string() {
                status_label.text = format!("🔇 {}", result["message".to_string()]);
                status_label.classes("text-red-600".to_string());
                ui.notify(result["message".to_string()], /* type= */ "negative".to_string());
            } else {
                status_label.text = format!("❌ {}", result["message".to_string()]);
                status_label.classes("text-red-600".to_string());
                ui.notify(result["message".to_string()], /* type= */ "negative".to_string());
            }
        };
        let _ctx = ui.row().classes("gap-2 items-center".to_string());
        {
            ui.button("🎤 Test Microphone".to_string(), /* on_click= */ check_microphone).classes("text-sm".to_string());
            ui.label("Click to verify browser microphone access".to_string()).classes("text-xs text-gray-500".to_string());
        }
    }
}

/// Add an advanced microphone diagnostics panel.
/// 
/// Args:
/// ui: NiceGUI ui module
/// backend: AsyncBackend instance for API calls
/// container: Parent container
pub fn add_advanced_microphone_panel(ui: String, backend: String, container: String) -> Result<()> {
    // Add an advanced microphone diagnostics panel.
    // 
    // Args:
    // ui: NiceGUI ui module
    // backend: AsyncBackend instance for API calls
    // container: Parent container
    let _ctx = container;
    let _ctx = ui.column().classes("gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200".to_string());
    {
        ui.label("🎤 Microphone Diagnostics".to_string()).classes("font-bold".to_string());
        let _ctx = ui.row().classes("gap-2 items-center".to_string());
        {
            let mut browser_status = ui.label("🔄 Checking browser...".to_string());
            let check_browser = || {
                browser_status.text = "✓ Browser OK".to_string();
                browser_status.classes("text-green-600".to_string());
            };
        }
        ui.timer(0.5_f64, check_browser, /* once= */ true);
        let _ctx = ui.row().classes("gap-2 items-center".to_string());
        {
            let mut backend_status = ui.label("🔄 Checking backend...".to_string());
            let check_backend = || {
                // Check backend.
                // try:
                {
                    if /* hasattr(backend, "get_status".to_string()) */ true {
                        let mut response = backend.get_status().await;
                        if (response && response.get(&"status".to_string()).cloned() == "online".to_string()) {
                            backend_status.text = "✓ Backend OK".to_string();
                            backend_status.classes("text-green-600".to_string());
                        } else {
                            backend_status.text = "❌ Backend offline".to_string();
                            backend_status.classes("text-red-600".to_string());
                        }
                    } else {
                        backend_status.text = "⚠️ Cannot check backend".to_string();
                        backend_status.classes("text-yellow-600".to_string());
                    }
                }
                // except Exception as e:
            };
        }
        ui.timer(1.0_f64, check_backend, /* once= */ true);
        let _ctx = ui.expansion("Troubleshooting Guide".to_string()).classes("w-full".to_string());
        {
            let mut tips = vec![("🔇 No microphone found".to_string(), "Connect a microphone or webcam with audio".to_string()), ("🔒 Permission denied".to_string(), "Allow microphone access when browser prompts".to_string()), ("🔴 Another app using mic".to_string(), "Close other apps using the microphone".to_string()), ("🌐 HTTPS required".to_string(), "Only localhost works without HTTPS".to_string()), ("🔊 Audio too quiet".to_string(), "Increase microphone volume in system settings".to_string())];
            for (issue, solution) in tips.iter() {
                let _ctx = ui.row().classes("gap-2 p-2 border-l-4 border-amber-300 bg-amber-50".to_string());
                let _ctx = ui.column().classes("gap-1".to_string());
                {
                    ui.label(issue).classes("font-medium text-sm".to_string());
                    ui.label(solution).classes("text-xs text-gray-600".to_string());
                }
            }
        }
    }
}
