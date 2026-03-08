#!/usr/bin/env python3
"""Test Piper directly with proper usage"""

from pathlib import Path
import io

print("Testing Piper TTS API...\n")

try:
    from piper import PiperVoice

    print("✓ Piper imported successfully")

    # Download/verify model
    model_dir = Path.home() / ".zena" / "models" / "piper"
    model_dir.mkdir(exist_ok=True, parents=True)

    voice_file = model_dir / "en_US-lessac-medium.onnx"
    config_file = model_dir / "en_US-lessac-medium.onnx.json"

    # [X-Ray auto-fix] print(f"\n Model file exists: {voice_file.exists()}")
    # [X-Ray auto-fix] print(f"Config file exists: {config_file.exists()}")
    if voice_file.exists() and config_file.exists():
        print("\n✓ Loading voice model...")
        voice = PiperVoice.load(str(voice_file), config_path=str(config_file))
        print("✓ Voice loaded")

        print("\nTesting synthesize...")
        # Try different ways
        print("\n1️⃣ Method 1: Direct synthesize (may return generator)...")
        try:
            result = voice.synthesize("Hello world")
            # [X-Ray auto-fix] print(f"   Result type: {type(result)}")
            if hasattr(result, "__iter__"):
                print("   Result is iterable (audio chunks)")
                chunks = list(result)
                # [X-Ray auto-fix] print(f"   Got {len(chunks)} chunks")
        except Exception as e:
            print(f"   Error: {e}")

        print("\n2️⃣ Method 2: Synthesize with output file...")
        try:
            output = io.BytesIO()
            voice.synthesize("Hello world", output)
            output.seek(0)
            audio_bytes = output.getvalue()
            # [X-Ray auto-fix] print(f"   Generated {len(audio_bytes)} bytes")
        except Exception as e:
            print(f"   Error: {e}")

        print("\n3️⃣ Method 3: Synthesize_stream...")
        try:
            if hasattr(voice, "synthesize_stream"):
                audio_data = b""
                for chunk in voice.synthesize_stream("Hello world"):
                    audio_data += chunk
                # [X-Ray auto-fix] print(f"   Generated {len(audio_data)} bytes via stream")
            else:
                print("   No synthesize_stream method")
        except Exception as e:
            print(f"   Error: {e}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
