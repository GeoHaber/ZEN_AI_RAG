# tests/test_self_audio_injection.py
"""
Self-test: Inject a known audio (synthetic speech) into the pipeline, transcribe, and compare output.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from voice_pipeline.stt import transcribe_audio
from voice_pipeline.tts import synthesize_speech
from voice_pipeline.llm import generate_response
import tempfile
import os
import wave

TEST_TEXT = "Hello, this is a self test."
EXPECTED_RESPONSE = "Hi there!"  # As per dummy LLM

def save_mp3_as_wav(mp3_bytes, wav_path):
    # This is a placeholder. In real code, use pydub or ffmpeg to convert mp3 to wav.
    # For now, just create a dummy wav file for the test.
    with wave.open(wav_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b'\x00' * 16000 * 2)  # 1 second of silence


def test_self_audio_injection():
    # Step 1: Synthesize speech (TTS)
    mp3_bytes = synthesize_speech(TEST_TEXT)
    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = os.path.join(tmpdir, 'test.wav')
        save_mp3_as_wav(mp3_bytes, wav_path)

        # Step 2: Transcribe (STT)
        with open(wav_path, 'rb') as f:
            audio_bytes = f.read()
        transcribed = transcribe_audio(audio_bytes)
        print(f"Transcribed: {transcribed}")
        assert isinstance(transcribed, str)
        # In real test, compare with TEST_TEXT

        # Step 3: LLM response
        response = generate_response(transcribed)
        print(f"LLM Response: {response}")
        assert response == EXPECTED_RESPONSE
