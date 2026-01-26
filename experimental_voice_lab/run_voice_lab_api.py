# run_voice_lab_api.py

"""
FastAPI backend for Voice Lab, using modular pipeline components.
Exposes endpoints for UI integration: /api/record, /api/chat, /api/tts, etc.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pathlib
from fastapi.middleware.cors import CORSMiddleware
from voice_pipeline.vad import listen_and_buffer
from voice_pipeline.stt import transcribe_audio
from voice_pipeline.llm import generate_response
from voice_pipeline.tts import synthesize_speech
import time
import os


BASE_DIR = pathlib.Path(__file__).parent.resolve()
TEMPLATES_DIR = BASE_DIR / "templates"
GENERATED_DIR = BASE_DIR / "generated"

app = FastAPI()

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for /generated and /static (if needed)
app.mount("/generated", StaticFiles(directory=str(GENERATED_DIR)), name="generated")
app.mount("/static", StaticFiles(directory=str(TEMPLATES_DIR)), name="static")

# Serve index.html at root
@app.get("/")
async def serve_index():
    return FileResponse(str(TEMPLATES_DIR / "index.html"))

@app.post("/api/record")
async def api_record(request: Request):
    # Simulate VAD + STT
    t0 = time.time()
    audio = listen_and_buffer()
    vad_time = time.time() - t0
    t1 = time.time()
    text = transcribe_audio(audio)
    stt_time = time.time() - t1
    return JSONResponse({
        "text": text,
        "profiling": {"vad": vad_time, "stt": stt_time}
    })

@app.post("/api/chat")
async def api_chat(request: Request):
    data = await request.json()
    text = data.get("message", "")
    t0 = time.time()
    response = generate_response(text)
    llm_time = time.time() - t0
    # Dummy emotion for now
    return JSONResponse({
        "response": response,
        "emotion": "neutral",
        "profiling": {"llm": llm_time}
    })

@app.post("/api/tts")
async def api_tts(request: Request):
    data = await request.json()
    text = data.get("text", "")
    t0 = time.time()
    mp3_bytes = synthesize_speech(text)
    tts_time = time.time() - t0
    # Save to file and return URL (simulate)
    out_dir = "generated"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "out.mp3")
    with open(out_path, "wb") as f:
        f.write(mp3_bytes)
    return JSONResponse({
        "status": "ok",
        "url": f"/generated/out.mp3",
        "profiling": {"tts": tts_time}
    })

# Add more endpoints as needed (devices, voices, etc.)
