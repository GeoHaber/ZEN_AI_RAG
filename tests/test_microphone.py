#!/usr/bin/env python
"""
Microphone Diagnostic Test
Test audio input capabilities and troubleshoot issues
"""
import sounddevice as sd
import numpy as np
import sys

print("🔍 MICROPHONE DIAGNOSTIC TEST")
print("=" * 70)

# List all devices
print("\n📋 Available Audio Devices:")
devices = sd.query_devices()
for i, dev in enumerate(devices):
    is_input = dev['max_input_channels'] > 0
    is_output = dev['max_output_channels'] > 0
    marker = ''
    if is_input:
        marker = '🎤 INPUT'
    if is_output:
        marker += ' 🔊 OUTPUT'
    name = dev["name"][:35]
    print(f"  [{i:2d}] {name:<35} {marker}")

# Test default input device
print("\n🎯 Testing Default Input Device...")
try:
    input_device = sd.default.device[0]
    print(f"  Default: Device #{input_device}")
    dev_info = sd.query_devices(input_device)
    print(f"  Name: {dev_info['name']}")
    print(f"  Channels: {dev_info['max_input_channels']}")
    print(f"  Sample Rate: {dev_info['default_samplerate']} Hz")
    
    # Try to record 2 seconds
    print("\n🎙️ Recording 2 seconds test (speak now!)...")
    duration = 2
    fs = int(dev_info['default_samplerate'])
    print(f"  Recording at {fs} Hz...")
    
    try:
        audio_data = sd.rec(int(duration * fs), samplerate=fs, channels=1, device=input_device)
        sd.wait()
        
        # Check if any audio was captured
        audio_level = np.max(np.abs(audio_data))
        print(f"  ✓ Recording successful!")
        print(f"  Audio level: {audio_level:.4f}")
        
        if audio_level < 0.001:
            print("  ⚠️ WARNING: Very low audio level - microphone may be muted or disconnected")
        elif audio_level < 0.01:
            print("  ⚠️ WARNING: Low audio level - check microphone volume")
        else:
            print("  ✓ Audio capture working!")
            
    except Exception as e:
        print(f"  ✗ Recording failed: {e}")
        sys.exit(1)
        
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Test VoiceManager integration
print("\n🔗 Testing VoiceManager Integration...")
try:
    from zena_mode.voice_manager import VoiceManager
    vm = VoiceManager()
    
    print(f"  ✓ VoiceManager loaded")
    devices = vm.enumerate_devices()
    print(f"  Available devices: {len(devices)}")
    
    # List input devices
    print("\n  Input Devices:")
    for dev in devices:
        if dev.is_input:
            print(f"    - {dev.name} (ID: {dev.id}, channels: {dev.channels})")
    
    # Try to record audio
    print("\n  Testing recording (2 seconds, speak now!)...")
    result = vm.record_audio(duration=2)
    if result.success and result.audio_data:
        # Convert bytes to numpy array for level calculation
        import struct
        samples = struct.unpack('<' + 'h' * (len(result.audio_data) // 2), result.audio_data)
        samples = np.array(samples, dtype=np.float32) / 32768.0
        level = np.max(np.abs(samples))
        
        print(f"  ✓ Recorded successfully")
        print(f"  Duration: {result.duration:.2f}s")
        print(f"  Sample rate: {result.sample_rate} Hz")
        print(f"  Audio level: {level:.4f}")
        
        if level > 0.05:
            print("  ✓ Audio level good!")
        elif level > 0.01:
            print("  ⚠️ Audio level low - consider increasing microphone volume")
        else:
            print("  ✗ Audio level very low - microphone may be muted")
    else:
        print(f"  ✗ Recording failed: {result.error}")
        
except Exception as e:
    print(f"  ✗ VoiceManager error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("Diagnostic complete!")
print("\n📝 SOLUTIONS:")
print("  1. Low microphone volume → Check Windows sound settings")
print("     - Right-click speaker icon → Open Volume mixer")
print("     - Find 'Microphone (Logi Webcam C920e)' and increase level")
print("  2. No audio capture → Check device is set as default input")
print("  3. UI microphone not working → Test voice endpoint via:")
print("     - curl -X GET http://localhost:8006/devices")
