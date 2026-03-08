#!/usr/bin/env python3
"""
Microphone Permission Checker for NiceGUI
Tests browser microphone access and displays status
"""


def add_microphone_permission_check(ui, container):
    """
    Add a microphone permission check widget to the UI.

    Args:
        ui: NiceGUI ui module
        container: Parent container to add the check to
    """

    # JavaScript to check microphone permissions
    check_mic_permission_js = """
    async function checkMicrophonePermission() {
        try {
            // Check if mediaDevices API is available
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                return {
                    status: 'error',
                    message: 'MediaDevices API not supported',
                    icon: '❌'
                };
            }
            
            // Request microphone permission
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Clean up - stop the stream
            stream.getTracks().forEach(track => track.stop());
            
            // Enumerate devices to get more info
            const devices = await navigator.mediaDevices.enumerateDevices();
            const audioInputs = devices.filter(dev => dev.kind === 'audioinput');
            
            return {
                status: 'success',
                message: `Microphone access granted (${audioInputs.length} device(s))`,
                icon: '✓',
                devices: audioInputs.length
            };
        } catch (error) {
            let message = 'Microphone access denied';
            
            if (error.name === 'NotAllowedError') {
                message = 'Microphone permission denied by user';
            } else if (error.name === 'NotFoundError') {
                message = 'No microphone found on this device';
            } else if (error.name === 'NotReadableError') {
                message = 'Microphone in use by another application';
            } else if (error.name === 'SecurityError') {
                message = 'HTTPS required for microphone access';
            }
            
            return {
                status: 'denied',
                message: message,
                icon: '🔇',
                error: error.name
            };
        }
    }
    
    checkMicrophonePermission();
    """

    with container:
        # Status label
        status_label = ui.label().classes("text-sm font-medium")

        # Check button
        async def check_microphone():
            """Check microphone."""
            status_label.text = "🔄 Checking microphone access..."
            status_label.update()

            # Run JavaScript check
            result = await ui.run_javascript(check_mic_permission_js)

            if result["status"] == "success":
                status_label.text = f"✓ Microphone Ready ({result['devices']} device(s))"
                status_label.classes("text-green-600")
                ui.notify("Microphone access granted!", type="positive")
            elif result["status"] == "denied":
                status_label.text = f"🔇 {result['message']}"
                status_label.classes("text-red-600")
                ui.notify(result["message"], type="negative")
            else:
                status_label.text = f"❌ {result['message']}"
                status_label.classes("text-red-600")
                ui.notify(result["message"], type="negative")

        with ui.row().classes("gap-2 items-center"):
            ui.button("🎤 Test Microphone", on_click=check_microphone).classes("text-sm")
            ui.label("Click to verify browser microphone access").classes("text-xs text-gray-500")


def add_advanced_microphone_panel(ui, backend, container):
    """
    Add an advanced microphone diagnostics panel.

    Args:
        ui: NiceGUI ui module
        backend: AsyncBackend instance for API calls
        container: Parent container
    """

    with container, ui.column().classes("gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200"):
        ui.label("🎤 Microphone Diagnostics").classes("font-bold")

        # Browser status
        with ui.row().classes("gap-2 items-center"):
            browser_status = ui.label("🔄 Checking browser...")

            async def check_browser():
                browser_status.text = "✓ Browser OK"
                browser_status.classes("text-green-600")

        ui.timer(0.5, check_browser, once=True)

        # Backend status
        with ui.row().classes("gap-2 items-center"):
            backend_status = ui.label("🔄 Checking backend...")

            async def check_backend():
                """Check backend."""
                try:
                    if hasattr(backend, "get_status"):
                        response = await backend.get_status()
                        if response and response.get("status") == "online":
                            backend_status.text = "✓ Backend OK"
                            backend_status.classes("text-green-600")
                        else:
                            backend_status.text = "❌ Backend offline"
                            backend_status.classes("text-red-600")
                    else:
                        backend_status.text = "⚠️ Cannot check backend"
                        backend_status.classes("text-yellow-600")
                except Exception as e:
                    backend_status.text = f"❌ Error: {str(e)[:30]}"
                    backend_status.classes("text-red-600")

        ui.timer(1.0, check_backend, once=True)

        # Troubleshooting tips
        with ui.expansion("Troubleshooting Guide").classes("w-full"):
            tips = [
                ("🔇 No microphone found", "Connect a microphone or webcam with audio"),
                ("🔒 Permission denied", "Allow microphone access when browser prompts"),
                ("🔴 Another app using mic", "Close other apps using the microphone"),
                ("🌐 HTTPS required", "Only localhost works without HTTPS"),
                ("🔊 Audio too quiet", "Increase microphone volume in system settings"),
            ]

            for issue, solution in tips:
                with (
                    ui.row().classes("gap-2 p-2 border-l-4 border-amber-300 bg-amber-50"),
                    ui.column().classes("gap-1"),
                ):
                    ui.label(issue).classes("font-medium text-sm")
                    ui.label(solution).classes("text-xs text-gray-600")


# Example usage in a NiceGUI page:
"""
from nicegui import ui
from ui.microphone_checker import add_microphone_permission_check, add_advanced_microphone_panel

@ui.page('/')
async def main_page():
    with ui.card():
        ui.label('Audio Settings').classes('text-lg font-bold')
        
        # Simple permission check
        add_microphone_permission_check(ui, ui.column())
        
        ui.separator()
        
        # Advanced diagnostics panel
        from async_backend import AsyncZenAIBackend
        backend = AsyncZenAIBackend()
        add_advanced_microphone_panel(ui, backend, ui.column())

ui.run()
"""
