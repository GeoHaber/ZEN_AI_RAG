# voice_pipeline/test_pipeline.py

def test_pipeline_profiling():
    """
    Test and profile the full voice pipeline using modular components.
    """
    from voice_pipeline.vad import listen_and_buffer
    from voice_pipeline.stt import transcribe_audio
    from voice_pipeline.llm import generate_response
    from voice_pipeline.tts import synthesize_speech
    import time

    timings = {}

    # Step 1: Listening (VAD)
    t0 = time.time()
    audio = listen_and_buffer()
    timings['vad'] = time.time() - t0

    # Step 2: Transcribing (STT)
    t1 = time.time()
    text = transcribe_audio(audio)
    timings['stt'] = time.time() - t1

    # Step 3: Thinking (LLM)
    t2 = time.time()
    response = generate_response(text)
    timings['llm'] = time.time() - t2

    # Step 4: Speaking (TTS)
    t3 = time.time()
    mp3 = synthesize_speech(response)
    timings['tts'] = time.time() - t3

    print("Profiling Results:")
    for stage, duration in timings.items():
        print(f"{stage.upper()}: {duration:.2f}s")

    # Assert all stages complete (dummy check)
    assert all(t > 0 for t in timings.values())
