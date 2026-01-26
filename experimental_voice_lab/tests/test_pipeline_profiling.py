# tests/test_pipeline_profiling.py
"""
Profiles each stage of the voice pipeline and reports timing.
"""
import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from voice_pipeline.vad import listen_and_buffer
from voice_pipeline.stt import transcribe_audio
from voice_pipeline.llm import generate_response
from voice_pipeline.tts import synthesize_speech


def test_pipeline_profiling():
    timings = {}

    t0 = time.time()
    audio = listen_and_buffer()
    timings['vad'] = time.time() - t0

    t1 = time.time()
    text = transcribe_audio(audio)
    timings['stt'] = time.time() - t1

    t2 = time.time()
    response = generate_response(text)
    timings['llm'] = time.time() - t2

    t3 = time.time()
    mp3 = synthesize_speech(response)
    timings['tts'] = time.time() - t3

    print("\n--- Pipeline Profiling Results ---")
    for stage, duration in timings.items():
        print(f"{stage.upper()}: {duration:.2f}s")

    # All stages should be >0 (dummy check)
    assert all(t > 0 for t in timings.values())
