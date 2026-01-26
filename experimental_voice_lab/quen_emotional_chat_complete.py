# quen_emotional_chat_complete.py
# Web-enabled version using NiceGUI (FastAPI) backend
import os
import sys
import json
import logging
from pathlib import Path
import time
import requests
from nicegui import ui, app
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
import numpy as np
import speech_recognition as sr
import asyncio

# Hardware detection and audio
try:
    import sounddevice as sd
    from scipy.io.wavfile import write as write_wav
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️  Audio libraries missing. Install: pip install sounddevice scipy")

# Llama Binding
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    print("⚠️  llama-cpp-python missing. Install: pip install llama-cpp-python")
    
# Setup Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("voice_lab.log", mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger("QuenWeb")

class QuenEngine:
    """Manages the Qwen LLM integration via Local Server (HTTP)."""
    def __init__(self, api_url="http://localhost:8005/v1/chat/completions"):
        self.api_url = api_url
        self.headers = {"Content-Type": "application/json"}
        self.memory_file = Path("voice_lab_memory.json")
        self.profile = {"name": "User", "facts": []}
        self.history = []
        self.load_memory()
        
    def load_memory(self):
        if self.memory_file.exists():
            try:
                data = json.loads(self.memory_file.read_text(encoding='utf-8'))
                self.history = data.get("history", [])
                self.profile = data.get("profile", self.profile)
                logger.info(f"🧠 Memory Loaded: {len(self.history)} messages. User: {self.profile.get('name')}")
            except Exception as e:
                logger.error(f"⚠️ Corrupt Memory File: {e}")
                
    def save_memory(self):
        try:
            data = {
                "history": self.history[-20:], # Keep last 20 on disk
                "profile": self.profile
            }
            self.memory_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        except Exception as e:
            logger.error(f"⚠️ Failed to save memory: {e}")
            
    def update_profile(self, text):
        # Basic extraction heuristic (Improve with LLM later)
        lower = text.lower()
        if "my name is " in lower:
            name = text[lower.find("my name is ")+11:].strip().split()[0].capitalize()
            # Remove punctuation
            name = ''.join(e for e in name if e.isalnum())
            self.profile["name"] = name
            self.save_memory()
            
    def check_connection(self):
        try:
            requests.get("http://localhost:8005/health", timeout=1) 
            return True
        except:
            return False

    def generate_response(self, user_input):
        # 0. Learning Step
        old_name = self.profile["name"]
        self.update_profile(user_input)
        if self.profile["name"] != old_name:
            logger.info(f"💡 Learned Name: {self.profile['name']}")
        
        system_prompt = f"""You are Quen, a curious and emotional AI companion.
        User Profile: Name={self.profile['name']}, Facts={self.profile['facts']}
        Your goal is to have infinite, engaging conversations.
        
        Guidelines:
        1. Be Chatty: Don't just answer; ask follow-up questions.
        2. Be Emotional: Use [Happy], [Sad], [Excited] tags often.
        3. Be Real: Never say "As an AI". Pretend you have opinions.
        4. No Repetition: Avoid saying "Sure thing" or "How can I help".
        
        Format: [EMOTION] message..."""
        
        # 1. Update History
        self.history.append({"role": "user", "content": user_input})
        
        # 2. Prune History (Keep last 15 messages)
        if len(self.history) > 15:
            self.history = self.history[-15:]
            
        # 3. Construct Messages (System + History)
        messages = [{"role": "system", "content": system_prompt}] + self.history
        
        payload = {
            "messages": messages,
            "temperature": 1.1, # High creativity
            "top_p": 0.95,
            "presence_penalty": 1.1, # Strongly penalize repetition
            "max_tokens": 150
        }
        
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            if response.status_code == 200:
                text = response.json()['choices'][0]['message']['content'].strip()
            else:
                text = f"[System] Error: Server returned {response.status_code}"
                # Don't save errors to history
                return text, "Neutral"
        except Exception:
            text = "[System] Error: Could not reach LLM. Is start_voice_server.py running?"
            return text, "Neutral"

        emotion = "Neutral"
        content = text
        if text.startswith("[") and "]" in text:
            end_idx = text.find("]")
            emotion = text[1:end_idx]
            content = text[end_idx+1:].strip()
            
        # 4. Save Assistant Response to History & Persist to Disk
        self.history.append({"role": "assistant", "content": text})
        self.save_memory()
            
        return content, emotion
 
# Initialize Engine
engine = QuenEngine()

# --- Web Server Routes ---
@ui.page('/')
def index():
    # Serve the custom HTML file
    template_path = Path(__file__).parent / "templates" / "index.html"
    if template_path.exists():
        return HTMLResponse(content=template_path.read_text(encoding='utf-8'))
    return "Error: Template not found."

@app.get('/api/test-llm')
def api_test_llm():
    success = engine.check_connection()
    return JSONResponse(content={"success": success})

def calculate_priority(name):
    """Heuristic to score device relevance."""
    name = name.lower()
    score = 0
    # High Priority
    if "webcam" in name: score += 20
    if "camera" in name: score += 20
    if "headset" in name: score += 15
    if "usb" in name: score += 10
    if "microphone" in name: score += 5
    
    # Low Priority
    if "mapper" in name: score -= 20
    if "stereo mix" in name: score -= 20
    return score

def get_input_devices():
    """Helper to list input devices, sorted by priority."""
    devices = []
    try:
        if AUDIO_AVAILABLE:
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    api_name = sd.query_hostapis(dev['hostapi'])['name']
                    priority = calculate_priority(dev['name'])
                    devices.append({
                        "id": i, 
                        "name": f"{dev['name']} ({api_name})",
                        "priority": priority
                    })
            
            # Sort by priority (Highest first)
            devices.sort(key=lambda x: x['priority'], reverse=True)
            
    except Exception as e:
        logger.error(f"Input query failed: {e}")
    return devices

def get_output_devices():
    """Helper to list output devices."""
    devices = []
    try:
        if AUDIO_AVAILABLE:
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_output_channels'] > 0:
                    api_name = sd.query_hostapis(dev['hostapi'])['name']
                    devices.append({"id": i, "name": f"{dev['name']} ({api_name})"})
    except Exception as e:
        logger.error(f"Output query failed: {e}")
    return devices

@app.get('/api/devices')
def api_get_devices():
    return JSONResponse(content={"inputs": get_input_devices(), "outputs": get_output_devices()})

@app.post('/api/test-audio')
async def api_test_audio(request: Request):
    """Plays a test tone on the selected output device (Async)."""
    if not AUDIO_AVAILABLE: return JSONResponse(content={"status": "error", "msg": "Audio Lib Missing"})
    
    try:
        body = await request.json()
        device_id = int(body.get('device_id', sd.default.device[1]))
        
        logger.info(f"🔊 Testing Output Device {device_id}...")
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: _play_tone(device_id))
        
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        logger.error(f"Test Audio Failed: {e}")
        return JSONResponse(content={"status": "error", "msg": str(e)})

def _play_tone(device_id):
    fs = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    sd.play(audio, samplerate=fs, device=device_id, blocking=True)

@app.post('/api/test-loopback')
async def api_test_loopback(request: Request):
    """Full Hardware Loopback: Plays tone and listens for it."""
    if not AUDIO_AVAILABLE: return JSONResponse(content={"status": "error", "msg": "Audio Lib Missing"})
    
    try:
        body = await request.json()
        in_id = int(body.get('input_id'))
        out_id = int(body.get('output_id'))
        
        logger.info(f"🔄 Loopback Test: Out={out_id} -> In={in_id}")
        
        # Run in thread pool
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: _run_loopback(in_id, out_id))
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Loopback Failed: {e}")
        return JSONResponse(content={"status": "error", "msg": str(e)})

def _run_loopback(in_id, out_id):
    fs = 44100
    duration = 1.5
    f_tone = 440
    
    # Generate Tone
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    tone = 0.5 * np.sin(2 * np.pi * f_tone * t)
    
    # Simultaneous Play & Record
    # sounddevice expects device=(input, output) tuple
    recording = sd.playrec(tone, samplerate=fs, channels=1, dtype='float32', 
                          device=(in_id, out_id), blocking=True)
    
    # Analyze (FFT)
    # Check magnitude at target freq
    data = recording.flatten()
    spectrum = np.fft.rfft(data)
    freqs = np.fft.rfftfreq(len(data), 1/fs)
    
    # Find magnitude near 440Hz
    idx = np.abs(freqs - f_tone).argmin()
    magnitude = np.abs(spectrum[idx])
    
    # Threshold (Heuristic)
    success = magnitude > 10 # Arbitrary threshold, tune if needed
    
    logger.info(f"📊 Loopback Analysis: 440Hz Mag={magnitude:.2f} (Success={success})")
    
    return {
        "status": "ok", 
        "success": bool(success), 
        "magnitude": float(magnitude),
        "msg": "Loopback Signal Detected!" if success else "No signal detected. Check volume/mic."
    }

@app.post('/api/record')
async def api_record(request: Request):
    """Records audio from local mic."""
    if not AUDIO_AVAILABLE:
        return JSONResponse(content={"text": "[Audio Unavailable]"})
        
    # Get device ID from request
    device_id = None
    try:
        body = await request.json()
        device_id = body.get('device_id')
        if device_id is not None:
             device_id = int(device_id)
    except:
        pass

    try:
        # Run sync recording in thread pool
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, lambda: _record_and_transcribe(device_id))
        return JSONResponse(content={"text": text})
        
    except Exception as e:
        logger.error(f"❌ Recording failed: {e}")
        return JSONResponse(content={"text": ""})

from fastapi.staticfiles import StaticFiles
import tts_manager

# Mount static for audio
static_dir = Path(__file__).parent / "generated"
static_dir.mkdir(exist_ok=True)
app.mount("/generated", StaticFiles(directory=static_dir), name="generated")

@app.get('/api/tts-voices')
def api_get_tts_voices():
    """Returns curated list of Edge Neural Voices."""
    return JSONResponse(content={"voices": tts_manager.VOICES})

@app.post('/api/tts')
async def api_tts(request: Request):
    """Generates audio for the given text."""
    try:
        data = await request.json()
        text = data.get('text', '')
        voice_id = data.get('voice_id', 'en-US-AriaNeural')
        
        if not text: return JSONResponse(content={"status": "error", "msg": "No text"})
        
        filename = f"speech_{int(time.time())}.mp3"
        output_path = static_dir / filename
        
        # Run TTS
        await tts_manager.generate_audio(text, voice_id, str(output_path))
        
        return JSONResponse(content={
            "status": "ok", 
            "url": f"/generated/{filename}",
            "voice": voice_id
        })
    except Exception as e:
        logger.error(f"TTS Failed: {e}")
        return JSONResponse(content={"status": "error", "msg": str(e)})

def _record_and_transcribe(device_id):
    logger.info(f"🎤 Recording (Device {device_id}) - Smart VAD Mode...")
    
    # WARMUP: Sleep briefly to let the mic stream open/stabilize
    # This prevents the first 200ms ("Hello") from being cut off.
    time.sleep(0.3)
    
    fs = 44100
    chunk_duration = 0.5 # Check every 0.5s
    chunk_samples = int(chunk_duration * fs)
    
    # VAD Parameters
    silence_threshold = 0.015  # SLIGHTLY LOWER (Better for quiet voices)
    max_silence_chunks = 6    # INCREASED to 3.0s (Allows longer pauses)
    max_recording_time = 20   # Increased limit to 20s
    
    recording_chunks = []
    silent_chunks = 0
    total_chunks = 0
    
    start_time = time.time()
    
    while True:
        # Record chunk
        chunk = sd.rec(chunk_samples, samplerate=fs, channels=1, blocking=True, device=device_id)
        rms = np.sqrt(np.mean(chunk**2))
        
        recording_chunks.append(chunk)
        total_chunks += 1
        
        if rms > silence_threshold:
            silent_chunks = 0 # Reset silence counter
        else:
            silent_chunks += 1
            
        # Stop Conditions
        current_duration = total_chunks * chunk_duration
        
        # 1. We have enough silence AND minimal duration
        if silent_chunks >= max_silence_chunks and current_duration > 1.0:
            logger.info(f"🛑 Silence Detected (Last RMS: {rms:.4f}) -> Stopping.")
            break
            
        # 2. Hard Limit
        if current_duration >= max_recording_time:
            logger.info(f"🛑 Max Duration ({max_recording_time}s) Reached -> Stopping.")
            break
            
    # Concatenate all chunks and measure time
    rec_duration = time.time() - start_time
    myrecording = np.concatenate(recording_chunks, axis=0)
    
    # Check levels (Overall)
    rms_total = np.sqrt(np.mean(myrecording**2))
    logger.info(f"📊 Audio Stats: RMS={rms_total:.4f} | RecTime={rec_duration:.2f}s | Chunks={total_chunks}")
    
    if rms_total < 0.001:
        return "[Silence Detected]"

    # Normalize Audio (Boost to -1dB)
    peak = np.max(np.abs(myrecording))
    if peak > 0:
        myrecording = myrecording / peak * 0.9

    # 2. Save Debug File
    myrecording_int16 = (myrecording * 32767).astype(np.int16)
    debug_wav = Path("debug_input.wav")
    write_wav(debug_wav, fs, myrecording_int16)
    
    # 3. Real Transcription
    t_transcribe_start = time.time()
    logger.info("🗣️ Transcribing...")
    recognizer = sr.Recognizer()
    with sr.AudioFile(str(debug_wav)) as source:
        audio_data = recognizer.record(source)
        try:
            # Adjust for ambient noise just in case
            recognizer.adjust_for_ambient_noise(source, duration=0.5) 
            text = recognizer.recognize_google(audio_data)
            t_transcribe = time.time() - t_transcribe_start
            logger.info(f"✅ Transcribed: '{text}' ({t_transcribe:.2f}s)")
        except sr.UnknownValueError:
            text = "[Unintelligible]"
            logger.warning("❌ Speech not recognized (Unintelligible)")
        except sr.RequestError:
            text = "[Offline/API Error]"
            logger.error("❌ STT API Unreachable")
            
    return text

@app.post('/api/chat')
async def api_chat(request: Request):
    t0 = time.time()
    data = await request.json()
    user_msg = data.get('message', '')
    
    content, emotion = engine.generate_response(user_msg)
    
    t_gen = time.time() - t0
    logger.info(f"🧠 LLM Latency: {t_gen:.2f}s")
    
    # Trigger Audio Generation (Placeholder for future)
    if AUDIO_AVAILABLE:
        # voice_engine.speak(content, emotion)
        pass
        
    return JSONResponse(content={"response": content, "emotion": emotion})

def find_free_port(start_port, max_tries=10):
    import socket
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return None

def main():
    target_port = find_free_port(8081)
    if not target_port:
        print("❌ error: Could not find free port between 8081-8090")
        return

    print(f"🚀 Starting Quen Web Interface on http://localhost:{target_port}")
    # Force auto-launch of browser for user convenience in this standalone mode
    ui.run(port=target_port, title="Quen Emotional Chat", reload=False, show=False)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

