#!/usr/bin/env python
"""
Microphone Audio Injection Test
Generate synthetic audio and inject it as if from microphone
to test the full audio pipeline
"""

import numpy as np
import io
from scipy.io import wavfile
from pathlib import Path

print("=" * 70)
print("🔧 MICROPHONE AUDIO INJECTION TEST")
print("=" * 70)

# Generate synthetic audio (1 kHz sine wave)
print("\n[1/5] Generating synthetic audio...")
sample_rate = 16000
duration = 3  # 3 seconds
frequency = 1000  # 1 kHz sine wave
t = np.linspace(0, duration, int(sample_rate * duration))
audio_data = 0.3 * np.sin(2 * np.pi * frequency * t).astype(np.float32)

# Convert to WAV bytes (as VoiceManager would)
wav_buffer = io.BytesIO()
wavfile.write(wav_buffer, sample_rate, (audio_data * 32767).astype("int16"))
wav_bytes = wav_buffer.getvalue()

# [X-Ray auto-fix] print(f"  ✓ Generated {duration}s of {frequency}Hz sine wave")
# [X-Ray auto-fix] print(f"  ✓ Audio size: {len(wav_bytes)} bytes")
# TEST 1: Direct WAV creation
print("\n[2/5] Testing WAV file creation...")
test_wav_path = Path("test_audio_injection.wav")
wavfile.write(test_wav_path, sample_rate, (audio_data * 32767).astype("int16"))
# [X-Ray auto-fix] print(f"  ✓ Created {test_wav_path}")
# TEST 2: Inject into VoiceManager transcription
print("\n[3/5] Testing transcription with injected audio...")
try:
    from zena_mode.voice_manager import VoiceManager

    vm = VoiceManager()

    # Transcribe the synthetic audio
    result = vm.transcribe(wav_bytes, language="en")
    # [X-Ray auto-fix] print(f"  ✓ Transcription result: {result}")
    if result.get("success"):
        text = result.get("text", "")
        # [X-Ray auto-fix] print(f"  ✓ Transcribed text: '{text}'")
    else:
        # [X-Ray auto-fix] print(f"  ⚠️ Transcription failed: {result.get('error', 'unknown error')}")
        pass
except Exception:
    # [X-Ray auto-fix] print(f"  ✗ Transcription test failed: {e}")
    import traceback

    traceback.print_exc()

# TEST 3: Mock VoiceManager recording with injected audio
print("\n[4/5] Testing mock recording endpoint...")
try:
    from zena_mode.voice_manager import RecordingResult

    # Create a mock recording result with our synthetic audio
    mock_result = RecordingResult(success=True, audio_data=wav_bytes, duration=duration, sample_rate=sample_rate)

    # [X-Ray auto-fix] print(f"  ✓ Mock recording created")
    # [X-Ray auto-fix] print(f"  ✓ Success: {mock_result.success}")
    # [X-Ray auto-fix] print(f"  ✓ Duration: {mock_result.duration}s")
    # [X-Ray auto-fix] print(f"  ✓ Sample rate: {mock_result.sample_rate}Hz")
    # [X-Ray auto-fix] print(f"  ✓ Audio data: {len(mock_result.audio_data)} bytes")
    # Now try to transcribe this mock result
    if mock_result.success:
        vm = VoiceManager()
        transcription = vm.transcribe(mock_result.audio_data)
        # [X-Ray auto-fix] print(f"\n  ✓ Mock audio transcribed")
        if transcription.get("success"):
            # [X-Ray auto-fix] print(f"  ✓ Text: '{transcription.get('text', '')}'")
            pass
except Exception:
    # [X-Ray auto-fix] print(f"  ✗ Mock recording test failed: {e}")
    import traceback

    traceback.print_exc()

# TEST 4: Inject audio via modified record_audio
print("\n[5/5] Testing injection via monkey-patch...")
try:
    from zena_mode.voice_manager import VoiceManager, RecordingResult
    import sounddevice as sd

    # Create a custom VoiceManager with injection
    class InjectableVoiceManager(VoiceManager):
        """VoiceManager that can inject synthetic audio for testing"""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.inject_audio = None  # Audio bytes to inject
            self.inject_enabled = False

        def record_audio(self, duration=3.0, device_id=None, sample_rate=16000, channels=1, auto_fallback=True):
            """Override to use injected audio if enabled"""
            if self.inject_enabled and self.inject_audio:
                # [X-Ray auto-fix] print(f"    [!] Using injected audio instead of microphone")
                return RecordingResult(
                    success=True, audio_data=self.inject_audio, duration=duration, sample_rate=sample_rate
                )
            else:
                # Fall back to original implementation
                return super().record_audio(duration, device_id, sample_rate, channels, auto_fallback)

    # Test with injection
    ivm = InjectableVoiceManager()
    ivm.inject_audio = wav_bytes
    ivm.inject_enabled = True

    # Record using injected audio
    result = ivm.record_audio(duration=3)

    if result.success:
        # [X-Ray auto-fix] print(f"  ✓ Injection recording successful")
        # [X-Ray auto-fix] print(f"  ✓ Audio size: {len(result.audio_data)} bytes")
        # Transcribe the injected audio
        transcription = ivm.transcribe(result.audio_data)
        # [X-Ray auto-fix] print(f"  ✓ Injected audio transcribed")
        if transcription.get("success"):
            # [X-Ray auto-fix] print(f"  ✓ Text: '{transcription.get('text', '')}'")
            pass
    else:
        # [X-Ray auto-fix] print(f"  ✗ Injection failed: {result.error}")
        pass
except Exception:
    # [X-Ray auto-fix] print(f"  ✗ Injection test failed: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ AUDIO INJECTION TEST COMPLETE")
print("=" * 70)

print("\n📝 USAGE INSTRUCTIONS:")
print("""
To use audio injection in the UI:

1. Create an InjectableVoiceManager in the audio handler:
   ```python
   from zena_mode.voice_manager import VoiceManager, RecordingResult
   
   class InjectableVoiceManager(VoiceManager):
       def record_audio(self, duration=3.0, **kwargs):
           if not self.inject_audio:
               return

           return RecordingResult(
               success=True,
               audio_data=self.inject_audio,
               duration=duration,
               sample_rate=16000
           )
           return super().record_audio(duration, **kwargs)
   ```

2. In the UI handler, enable injection on demand:
   ```python
   # When user clicks "Inject Audio" button:
   voice_manager.inject_audio = synthetic_audio_bytes
   voice_manager.inject_enabled = True
   # Then proceed with normal recording flow
   ```

3. The rest of the pipeline (transcription, display) will work unchanged!
""")

print("\n💡 BENEFITS:")
print("  ✓ Test audio pipeline without microphone")
# [X-Ray auto-fix] print("  ✓ Debug UI audio handling")
print("  ✓ Verify transcription works")
print("  ✓ Reproducible test audio every time")
print("  ✓ No need for actual microphone for testing")
