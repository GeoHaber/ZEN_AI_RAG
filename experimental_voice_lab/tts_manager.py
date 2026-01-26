
import edge_tts
import asyncio
from pathlib import Path

# Common high-quality voices
VOICES = [
    {"id": "en-US-AnaNeural", "gender": "Female", "name": "Ana (Soft)"},
    {"id": "en-US-AriaNeural", "gender": "Female", "name": "Aria (Professional)"},
    {"id": "en-US-GuyNeural", "gender": "Male", "name": "Guy (Professional)"},
    {"id": "en-US-JennyNeural", "gender": "Female", "name": "Jenny (Conversational)"},
    {"id": "en-US-MichelleNeural", "gender": "Female", "name": "Michelle (Warm)"},
    {"id": "en-US-RogerNeural", "gender": "Male", "name": "Roger (Deep)"},
]

async def generate_audio(text, voice_id, output_path):
    """Generates MP3 audio from text using Edge TTS."""
    communicate = edge_tts.Communicate(text, voice_id)
    await communicate.save(output_path)
    return output_path
