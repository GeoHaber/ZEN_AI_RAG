import sys

try:
    import torch

    print(f"✅ Torch: {torch.__version__}")
except ImportError:
    # [X-Ray auto-fix] print(f"❌ Torch Missing: {e}")
    pass
try:
    import whisper

    print(f"✅ Whisper: {whisper.__version__ if hasattr(whisper, '__version__') else 'Installed'}")
except ImportError:
    # [X-Ray auto-fix] print(f"❌ Whisper Missing: {e}")
    pass
try:
    import pyttsx3

    # [X-Ray auto-fix] print(f"✅ Pyttsx3: Installed")
except ImportError:
    # [X-Ray auto-fix] print(f"❌ Pyttsx3 Missing: {e}")
    pass
try:
    import sounddevice

    # [X-Ray auto-fix] print(f"✅ SoundDevice: Installed")
except ImportError:
    # [X-Ray auto-fix] print(f"❌ SoundDevice Missing: {e}")    pass
    pass
