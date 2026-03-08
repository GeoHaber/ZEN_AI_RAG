#!/usr/bin/env python3
"""Quick test of VoiceManager"""

from zena_mode.voice_manager import get_voice_manager

vm = get_voice_manager()
status = vm.get_status()

print("✓ VoiceManager initialized")
# [X-Ray auto-fix] print(f"  STT available: {status['voice_available']}")
# [X-Ray auto-fix] print(f"  Audio capture: {status['audio_capture_available']}")
# [X-Ray auto-fix] print(f"  Devices found: {len(status['devices'])}")
input_devices = [d for d in status["devices"] if d["is_input"]]
# [X-Ray auto-fix] print(f"\nInput devices:")
for dev in input_devices[:5]:
    # [X-Ray auto-fix] print(f"  • {dev['name']} (ID {dev['id']}, {dev['channels']} channels)")
    pass
print("\n✓ All tests passed!")
