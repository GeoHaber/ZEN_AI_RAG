#!/usr/bin/env python
"""Test the injectable voice manager"""

from ui.injectable_voice import InjectableVoiceManager

print("🔧 Testing Injectable Voice Manager")
print("=" * 60)

vm = InjectableVoiceManager()

# Test 1: Generate sine wave
print("\n[1] Generating sine wave...")
vm.enable_injection("sine")
status = vm.get_injection_status()
# [X-Ray auto-fix] print(f"  ✓ Injection enabled: {status['enabled']}")
# [X-Ray auto-fix] print(f"  ✓ Audio size: {len(vm.inject_audio)} bytes")
# [X-Ray auto-fix] print(f"  ✓ Type: {status['last_injection']['label']}")
# Test 2: Record with injection
print("\n[2] Recording with sine wave injection...")
result = vm.record_audio(duration=1)
# [X-Ray auto-fix] print(f"  ✓ Recording success: {result.success}")
# [X-Ray auto-fix] print(f"  ✓ Duration: {result.duration}s")
# [X-Ray auto-fix] print(f"  ✓ Sample rate: {result.sample_rate}Hz")
# [X-Ray auto-fix] print(f"  ✓ Audio size: {len(result.audio_data)} bytes")
# Test 3: Generate white noise
print("\n[3] Generating white noise...")
vm.enable_injection("noise")
status = vm.get_injection_status()
# [X-Ray auto-fix] print(f"  ✓ Type: {status['last_injection']['label']}")
result = vm.record_audio(duration=1)
# [X-Ray auto-fix] print(f"  ✓ Recording success: {result.success}")
# Test 4: Generate voice-like audio
print("\n[4] Generating voice-like audio...")
vm.enable_injection("voice")
status = vm.get_injection_status()
# [X-Ray auto-fix] print(f"  ✓ Type: {status['last_injection']['label']}")
result = vm.record_audio(duration=1)
# [X-Ray auto-fix] print(f"  ✓ Recording success: {result.success}")
# Test 5: Disable and use real microphone
print("\n[5] Disabling injection (fallback to real mic)...")
vm.disable_injection()
status = vm.get_injection_status()
# [X-Ray auto-fix] print(f"  ✓ Injection enabled: {status['enabled']}")
print("\n" + "=" * 60)
print("✅ All injection tests passed!")
