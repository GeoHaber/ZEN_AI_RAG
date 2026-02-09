import sys
try:
    import torch
    print(f"✅ Torch: {torch.__version__}")
except ImportError as e:
    print(f"❌ Torch Missing: {e}")

try:
    import whisper
    print(f"✅ Whisper: {whisper.__version__ if hasattr(whisper, '__version__') else 'Installed'}")
except ImportError as e:
    print(f"❌ Whisper Missing: {e}")

try:
    import pyttsx3
    print(f"✅ Pyttsx3: Installed")
except ImportError as e:
    print(f"❌ Pyttsx3 Missing: {e}")

try:
    import sounddevice
    print(f"✅ SoundDevice: Installed")
except ImportError as e:
    print(f"❌ SoundDevice Missing: {e}")
