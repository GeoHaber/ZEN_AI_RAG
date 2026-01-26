# TODO.md

## User Prompt
Voice Lab Pipeline: Architecture & Profiling
1. Functional Diagram
This diagram maps the journey of your voice through the system.

Speakers
Edge TTS (Cloud)
Llama Server (Port 8005)
Backend (FastAPI)
Google STT (Cloud)
Frontend (sounddevice)
User (Microphone)
Speakers
Edge TTS (Cloud)
Llama Server (Port 8005)
Backend (FastAPI)
Google STT (Cloud)
Frontend (sounddevice)
User (Microphone)
1. Listening (VAD)
2. Transcribing
3. Thinking (Inference)
4. Speaking (TTS)
Speaks ("Hello Quen")
Buffers Audio (0.5s chunks)
Detect Silence (Threshold 0.02)
Sends .WAV (SpeechRecognition)
Returns Text ("Hello Quen")
POST /api/chat ("Hello Quen")
POST /v1/chat/completions
CPU Inference (Qwen2.5-7B)
Response ("Hi there!")
Returns Text + Emotion
POST /api/tts ("Hi there!")
Request Audio (edge-tts)
Returns .MP3
Returns MP3 URL
Plays Audio
2. Technical Breakdown (Step-by-Step)
Step 1: Listening (The Ear)
Code: 
quen_emotional_chat_complete.py
 -> 
_record_and_transcribe()
Library: sounddevice (PortsAudio).
Mechanism:
Records continuous 0.5s chunks.
Calculates RMS (Volume).
VAD Logic: Keeps recording until 0.02 silence threshold is met for >2 seconds.
Optimization: A "Warmup" sleep (0.3s) ensures the first word is not cut off.
Step 2: Transcribing (The Translator)
Code: 
_record_and_transcribe()
Library: SpeechRecognition (Google Web Speech API).
Data: Uploads raw 
.wav
 to Google, receives Text.
Why: Lightweight. Alternatives like Whisper (Local) are too heavy for this "Ant-Sized" CPU lab.
Step 3: Thinking (The Brain)
Code: QuenEngine.generate_response() -> 
api_chat
Engine: llama-server.exe (llama.cpp) running on Port 8005.
Model: qwen2.5-coder-7b-instruct-q4_k_m.gguf.
Hardware: Running on CPU (system_info: AVX2=1).
Context: Short-term memory is managed in Python list self.history.
Step 4: Speaking (The Voice)
Code: 
api_tts
 -> 
tts_manager.py
Library: edge-tts.
Mechanism:
Sends text to Microsoft Edge Online TTS API.
Downloads .mp3 to generated/ folder.
Frontend plays it using HTML5 new Audio().
3. Profiling Data (Where is the lag?)
We stress-tested the system with 20 concurrent requests. Here are the bottlenecks:

Component	Average Latency	Status	Note
VAD (Input)	~2-3s	🟢 Fast	Delay is mostly user speaking time.
STT (Google)	~1-2s	🟢 Good	Depends on internet speed.
LLM (Thinking)	3.5s - 11.0s	🔴 BOTTLENECK	7B Model on CPU is heavy.
TTS (Output)	~1-3s	🟡 Medium	generating MP3 takes time.
Conclusion
The Slowest Link: The Local LLM (llama-server).

Your CPU takes ~3.5s to generate a short response when idle.
Under load, this spikes to 11s+.
4. Optimization Plan
To make it faster, we must attack the Red bottleneck (The LLM).

Option A: Make the Model Smaller (Recommended)
Switch from Qwen 2.5 (7B) to Qwen 2.5 (3B) or 1.5B.

Impact: 2x - 4x Faster speed.
Trade-off: Slightly less "smart", but conversational flow will be instant.
Option B: Use GPU (If available)
If you have an NVIDIA GPU, we can offload layers to it.

Current State: Running pure CPU (-ngl 0).
Option C: Optimistic UI
We can "stream" the text to the TTS engine sentence-by-sentence (Complex architecture shift).

## Copilot Analysis & Recommendations

### Architecture
- Modularize each pipeline stage (VAD, STT, LLM, TTS, Audio I/O)
- Implement a VoicePipeline class to orchestrate the flow
- Use async I/O for network-bound steps
- Allow easy backend/model switching via config

### Performance
- Switch to a smaller LLM model (3B or 1.5B) for speed
- Enable GPU acceleration if possible
- Consider quantized models
- Pre-warm and cache TTS responses
- Implement streaming from LLM to TTS for optimistic UI

### Profiling
- Add profiling hooks/timestamps at each stage
- Expose metrics via FastAPI or Prometheus

### Scalability
- Use async FastAPI and/or task queues for concurrency
- Consider horizontal scaling for LLM server

### User Experience
- Show "thinking..." indicator for slow LLM
- Stream partial responses/audio to frontend

### Next Steps
1. Scaffold modular pipeline structure
2. Write tests to validate and profile each stage
3. Refactor code into modules/classes
4. Add profiling hooks
5. Research further optimizations

---

This TODO will be updated as progress is made.
