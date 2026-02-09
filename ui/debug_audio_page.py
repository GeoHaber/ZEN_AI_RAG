#!/usr/bin/env python
"""
Debug Audio Panel for ZEN_AI_RAG UI
Allows testing audio injection in the interface
"""
import sys
from nicegui import ui, app
from ui.injectable_voice import InjectableVoiceManager, create_audio_test_panel

# Initialize injectable voice manager
voice_manager = InjectableVoiceManager()

# Simple debug page
@ui.page('/debug/audio')
async def debug_audio_page():
    """Debug page for audio testing"""
    
    ui.add_head_html("""
    <style>
        .debug-panel {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
        }
    </style>
    """)
    
    with ui.column().classes('w-full gap-4 p-4'):
        
        # Header
        with ui.row().classes('items-center gap-3'):
            ui.icon('bug_report').classes('text-3xl')
            ui.label('🔧 Audio Debug Panel').classes('text-2xl font-bold')
        
        ui.separator()
        
        # Audio Injection Controls
        with ui.card().classes('w-full bg-blue-50 border-l-4 border-blue-500'):
            ui.label('📡 Audio Injection (Test Mode)').classes('text-lg font-bold text-blue-900')
            
            with ui.row().classes('gap-2 flex-wrap'):
                
                async def inject_sine():
                    voice_manager.enable_injection('sine')
                    ui.notify('🎵 Injecting 1kHz sine wave', type='info')
                
                async def inject_noise():
                    voice_manager.enable_injection('noise')
                    ui.notify('🌊 Injecting white noise', type='info')
                
                async def inject_voice():
                    voice_manager.enable_injection('voice')
                    ui.notify('🗣️ Injecting voice-like audio', type='info')
                
                async def use_real_mic():
                    voice_manager.disable_injection()
                    ui.notify('🎤 Using real microphone', type='info')
                
                ui.button('🎵 1kHz Sine', on_click=inject_sine).props('color=blue')
                ui.button('🌊 White Noise', on_click=inject_noise).props('color=cyan')
                ui.button('🗣️ Voice-like', on_click=inject_voice).props('color=green')
                ui.button('🎤 Real Mic', on_click=use_real_mic).props('color=gray')
            
            # Status
            status_display = ui.label('Status: Ready')
            status_display.classes('text-sm text-gray-700 mt-2')
            
            async def update_injection_status():
                status = voice_manager.get_injection_status()
                if status['enabled']:
                    label = status['last_injection'].get('label', 'Injected')
                    status_display.text = f"✓ Audio Injection ON ({label})"
                    status_display.classes('text-green-700 font-bold', remove='text-gray-700')
                else:
                    status_display.text = "⚪ Using real microphone"
                    status_display.classes('text-gray-700', remove='text-green-700 font-bold')
            
            ui.timer(0.5, update_injection_status)
        
        # Test Recording
        with ui.card().classes('w-full bg-purple-50 border-l-4 border-purple-500'):
            ui.label('🎙️ Test Recording').classes('text-lg font-bold text-purple-900')
            
            duration_slider = ui.slider(min=1, max=10, value=2).props('label')
            duration_slider.bind_value_to(duration_slider, 'label', lambda x: f'Duration: {x}s')
            
            recording_result = ui.label('Ready to record')
            
            async def test_record():
                recording_result.text = f"🔄 Recording {int(duration_slider.value)}s..."
                recording_result.classes('text-yellow-700')
                recording_result.update()
                
                try:
                    result = voice_manager.record_audio(duration=duration_slider.value)
                    
                    if result.success:
                        recording_result.text = f"✓ Recorded {len(result.audio_data)} bytes at {result.sample_rate}Hz"
                        recording_result.classes('text-green-700 font-bold', remove='text-yellow-700')
                        ui.notify(f'✓ Recording successful ({len(result.audio_data)} bytes)', type='positive')
                    else:
                        recording_result.text = f"✗ Recording failed: {result.error}"
                        recording_result.classes('text-red-700', remove='text-yellow-700')
                        ui.notify(f'✗ {result.error}', type='negative')
                except Exception as e:
                    recording_result.text = f"✗ Error: {str(e)[:100]}"
                    recording_result.classes('text-red-700', remove='text-yellow-700')
                    ui.notify(f'✗ Error: {e}', type='negative')
            
            with ui.row().classes('gap-2'):
                ui.button('🎙️ Record Audio', on_click=test_record).props('color=purple')
            
            recording_result.classes('text-sm mt-2')
        
        # Device Information
        with ui.card().classes('w-full bg-green-50 border-l-4 border-green-500'):
            ui.label('📊 Device Information').classes('text-lg font-bold text-green-900')
            
            devices = voice_manager.enumerate_devices()
            input_devices = [d for d in devices if d.is_input]
            output_devices = [d for d in devices if d.is_output]
            
            ui.label(f"Input Devices: {len(input_devices)}")
            ui.label(f"Output Devices: {len(output_devices)}")
            
            with ui.expansion('Show Device List').classes('w-full'):
                for dev in input_devices[:5]:  # Show first 5
                    ui.label(f"🎤 [{dev.id}] {dev.name} ({dev.channels}ch, {int(dev.default_sample_rate)}Hz)")
        
        # Troubleshooting
        with ui.card().classes('w-full bg-yellow-50 border-l-4 border-yellow-500'):
            ui.label('💡 Troubleshooting Tips').classes('text-lg font-bold text-yellow-900')
            
            tips = [
                ("Microphone not responding?", "Try injecting audio first to test if UI works"),
                ("Still no audio in chat?", "Check Windows Volume Mixer (right-click speaker icon)"),
                ("Permission denied?", "Reload page and allow microphone access when prompted"),
                ("Only silence recorded?", "Increase microphone volume in system settings"),
            ]
            
            for question, answer in tips:
                with ui.expansion(question).classes('text-sm'):
                    ui.label(answer).classes('text-gray-700')
        
        ui.separator()
        
        # Quick Start
        with ui.row().classes('gap-4 items-start'):
            with ui.card().classes('w-full'):
                ui.label('🚀 Quick Start').classes('font-bold')
                ui.label('1. Click "🗣️ Voice-like" to inject test audio')
                ui.label('2. Click "🎙️ Record Audio" to test recording')
                ui.label('3. If successful, real microphone should also work')


# Run if called directly (for testing)
if __name__ == "__main__":
    print("Starting debug audio page at http://localhost:8080/debug/audio")
    ui.run(host='127.0.0.1', port=8080, reload=False)
