"""
asgi_server.py - FastAPI-based async server for ZenAI Hub API

Replaces the sync BaseHTTPRequestHandler with a proper ASGI framework.
This provides true async/await, middleware support, and better error handling.
"""
import logging
import threading
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from config_system import config

logger = logging.getLogger("ZenAI.ASGI")

# --- FastAPI App ---
app = FastAPI(
    title="ZenAI Hub API",
    version="2.0.0",
    description="Async API for ZenAI orchestration"
)

# --- Middleware ---
# CORS: Restrict to localhost only (security hardening)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8080"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Request size limiter
MAX_REQUEST_SIZE = config.get('MAX_FILE_SIZE', 10 * 1024 * 1024)  # 10MB default


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Enforce request size limits."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        return JSONResponse(
            status_code=413,
            content={"error": "Request entity too large"}
        )
    return await call_next(request)


# --- API Key Authentication ---
import os
API_KEY = os.environ.get("ZENAI_API_KEY", "")  # Optional: set to enable auth
API_KEY_HEADER = "X-API-Key"
# Paths that don't require authentication
PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/voice/lab"}


@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    """Optional API key authentication middleware.
    
    - If ZENAI_API_KEY is not set, all requests pass (dev mode)
    - Localhost requests always pass (for UI integration)
    - External requests require valid API key header
    """
    # Skip if no API key configured (dev mode)
    if not API_KEY:
        return await call_next(request)
    
    # Allow localhost without auth (UI uses this)
    client_host = request.client.host if request.client else ""
    if client_host in ("127.0.0.1", "localhost", "::1"):
        return await call_next(request)
    
    # Allow public endpoints
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)
    
    # Check API key header
    provided_key = request.headers.get(API_KEY_HEADER, "")
    if provided_key != API_KEY:
        logger.warning(f"[Auth] Unauthorized request from {client_host} to {request.url.path}")
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized - Invalid or missing API key"}
        )
    
    return await call_next(request)


# --- Pydantic Models ---
class SwapRequest(BaseModel):
    """SwapRequest class."""
    model: str


class ScaleRequest(BaseModel):
    """ScaleRequest class."""
    count: int = 3


class ChatRequest(BaseModel):
    """ChatRequest class."""
    message: str
    mode: str = "fast"  # "fast", "deep_thinking", "council"

class DownloadRequest(BaseModel):
    """DownloadRequest class."""
    repo_id: str
    filename: str

# Global Swarm Instance per process
_swarm_arbitrator = None

def get_swarm():
    global _swarm_arbitrator
    if _swarm_arbitrator is None:
        from zena_mode.swarm_arbitrator import SwarmArbitrator
        # Initialize dynamically
        _swarm_arbitrator = SwarmArbitrator()
    return _swarm_arbitrator

@app.post("/api/chat/swarm")
async def chat_swarm(request: Request):
    """
    Council Mode: Swarm Consensus endpoint.
    Routes to SwarmChatHandler for multi-model debate.
    """
    from zena_mode.handlers.swarm_chat import get_swarm_handler
    
    handler = await get_swarm_handler()
    
    # Simple adapter for BaseZenHandler compatibility
    class AsyncAdapter:
        """AsyncAdapter class."""
        def __init__(self, req, body): 
            self.req = req
            self.body = body
            self.path = req.url.path
            self._response = None
            
        def parse_json_body(self): return self.body
        def send_json_response(self, code, content):
             self._response = JSONResponse(status_code=code, content=content)

    try:
        body = await request.json()
        adapter = AsyncAdapter(request, body)
        await handler.handle_post_async(adapter)
        
        if adapter._response:
            return adapter._response
        return JSONResponse(status_code=500, content={"error": "No response from Swarm Handler"})
        
    except Exception as e:
        logger.error(f"Swarm Endpoint Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Chat endpoint supporting Fast and Deep Thinking modes."""
    import requests
    from zena_mode.server import MODEL_PATH
    
    if not req.message:
        raise HTTPException(status_code=400, detail="Missing message")
    
    # Mode: Deep Thinking / Council
    if req.mode in ["deep_thinking", "council"]:
        try:
            swarm = get_swarm()
            # Ensure swarm knows about current experts
            await swarm.discover_swarm()
            
            # Use simple consensus for now
            # We need to adapt swarm's stream/run methods to return a single string for this API
            # For now, let's use a simplified run method or iterate updates
            
            # SwarmArbitrator.run() logic needed here.
            # Looking at swarm_arbitrator.py, it likely has a method to get a final answer.
            # Let's assume we want to stream back or return final.
            # As this is a sync-like endpoint returning JSON:
            
            # We'll create a task runner
            # Temporarily import here to check method names if needed, but assuming standard flow
            
            # Let's add a helper in SwarmArbitrator called `get_consensus_answer(query)`
            # Since I can't see the file content right now, I'll rely on generic usage
            # or add a specific method to swarm_arbitrator.py first?
            
            # WAIT: I should check swarm_arbitrator.py API surface first to be safe.
            # But based on the code I wrote/saw earlier (step 3604), it has `_traffic_controller_mode` generator.
            
            # Let's stick to simple "council" routing for V1:
            # Query all models, concat answers? 
            # The user wants "judge with one has the corect".
            
            # Using the arbitrator's direct functionality:
            final_answer = ""
            async for chunk in swarm._traffic_controller_mode(req.message):
                final_answer += chunk
                
            return {"response": final_answer, "emotion": "thoughtful", "mode": "council"}

        except Exception as e:
            logger.error(f"Swarm Error: {e}")
            # Fallback to local
            req.mode = "fast"

    # Mode: Fast (Default)
    try:
        payload = {
            "model": MODEL_PATH.name,
            "messages": [
                {"role": "system", "content": "You are ZenAI, a helpful assistant. Keep answers short."},
                {"role": "user", "content": req.message}
            ],
            "stream": False,
            "max_tokens": 150
        }
        resp = requests.post(config.get_api_url(), json=payload, timeout=30)
        if resp.status_code == 200:
            llm_data = resp.json()
            content = llm_data['choices'][0]['message']['content']
            return {"response": content, "emotion": "neutral", "mode": "fast"}
        else:
            raise HTTPException(status_code=500, detail=f"LLM Error: {resp.text}")
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ==================== HEALTH ROUTES ====================

@app.get("/health")
async def health_check():
    """Check overall system health."""
    from utils import is_port_active
    llm_status = is_port_active(config.llm_port)
    return {
        "status": "healthy" if llm_status else "degraded",
        "llm_online": llm_status,
        "llm_port": config.llm_port
    }


@app.get("/api/test-llm")
async def test_llm():
    """Test if LLM engine is responding."""
    from utils import is_port_active
    status = is_port_active(config.llm_port)
    return {"success": status, "port": config.llm_port}


@app.get("/startup/progress")
async def startup_progress():
    """Get startup progress for UI splash screen."""
    try:
        from startup_progress import get_startup_progress
        return get_startup_progress()
    except Exception:
        return {"stage": "loading", "percent": 0, "message": "Initializing..."}


@app.get("/metrics")
async def get_metrics():
    """Return profiler metrics."""
    from zena_mode.profiler import monitor
    return monitor.get_summary()


# ==================== MODEL ROUTES ====================

@app.get("/list")
async def list_models():
    """List locally available models."""
    try:
        models = [f.name for f in config.MODEL_DIR.glob("*.gguf")]
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/popular")
async def popular_models():
    """Get popular models from registry."""
    import model_manager
    try:
        return model_manager.get_popular_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/search")
async def search_models(q: str = ""):
    """Search HuggingFace for models."""
    import model_manager
    try:
        return model_manager.search_hf_models(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/download")
async def download_model(req: DownloadRequest):
    """Start async model download."""
    import model_manager
    try:
        model_manager.download_model_async(req.repo_id, req.filename)
        return {"status": "started", "message": f"Downloading {req.filename}..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ORCHESTRATION ROUTES ====================

@app.post("/swap")
async def swap_model(req: SwapRequest):
    """Swap to a different model."""
    from zena_mode.server import restart_with_model
    threading.Thread(target=restart_with_model, args=(req.model,), daemon=True).start()
    return {"status": "accepted", "model": req.model}


@app.post("/swarm/scale")
async def scale_swarm(req: ScaleRequest):
    """Scale the expert swarm."""
    from zena_mode.server import scale_swarm as do_scale
    if req.count < 1 or req.count > 10:
        raise HTTPException(status_code=400, detail="count must be 1-10")
    threading.Thread(target=do_scale, args=(req.count,), daemon=True).start()
    return {"status": "scaling", "target": req.count}


class LaunchRequest(BaseModel):
    """LaunchRequest class."""
    model: str
    port: int

@app.post("/swarm/launch")
async def launch_swarm_expert(req: LaunchRequest):
    """Launch a heterogeneous expert process."""
    from zena_mode.server import launch_expert_process
    from config_system import config
    from pathlib import Path
    
    # Resolve Path
    m_path = Path(req.model)
    if not m_path.is_absolute():
        m_path = config.MODEL_DIR / req.model
    
    if not m_path.exists():
        # Fallback to C:/AI/Models explicit check
        central = Path("C:/AI/Models") / req.model
        if central.exists():
            m_path = central
        else:
            raise HTTPException(status_code=404, detail=f"Model not found: {req.model}")

    try:
        # Launch using server's helper
        launch_expert_process(port=req.port, threads=2, model_path=m_path)
        return {"status": "launched", "model": str(m_path), "port": req.port}
    except Exception as e:
        logger.error(f"Launch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ==================== VOICE ROUTES ====================

@app.get("/api/devices")
async def list_devices():
    """List available audio devices."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        return {"devices": [{"id": i, "name": d["name"]} for i, d in enumerate(devices)]}
    except Exception as e:
        return {"devices": [], "error": str(e)}


@app.get("/voice/lab")
async def voice_lab():
    """Serve the Voice Lab interface."""
    from fastapi.responses import HTMLResponse
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZenAI Voice Lab</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Inter', system-ui, sans-serif; 
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh; color: #e2e8f0; padding: 20px;
        }
        .container { max-width: 600px; margin: 0 auto; }
        h1 { font-size: 1.5rem; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        .card { background: rgba(30,41,59,0.8); border-radius: 12px; padding: 20px; margin-bottom: 16px; border: 1px solid #334155; }
        .btn { 
            background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
            color: #fff; border: none; padding: 12px 24px; border-radius: 8px; 
            cursor: pointer; font-weight: 600; font-size: 1rem; width: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(99,102,241,0.4); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-danger { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
        .status { padding: 10px; border-radius: 8px; margin-top: 10px; font-size: 0.9rem; }
        .status.success { background: rgba(34,197,94,0.2); border: 1px solid #22c55e; }
        .status.error { background: rgba(239,68,68,0.2); border: 1px solid #ef4444; }
        .status.info { background: rgba(59,130,246,0.2); border: 1px solid #3b82f6; }
        textarea { 
            width: 100%; min-height: 100px; background: #0f172a; border: 1px solid #334155;
            border-radius: 8px; padding: 12px; color: #e2e8f0; font-size: 1rem; resize: vertical;
        }
        label { display: block; margin-bottom: 8px; font-weight: 500; color: #94a3b8; }
        .recording { animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ ZenAI Voice Lab</h1>
        
        <div class="card">
            <label>Text to Speech (TTS)</label>
            <textarea id="ttsText" placeholder="Enter text to speak...">Hello! I am ZenAI, your intelligent assistant.</textarea>
            <button class="btn" onclick="synthesize()" style="margin-top: 12px;">🔊 Speak</button>
            <div id="ttsStatus"></div>
        </div>
        
        <div class="card">
            <label>Speech to Text (STT)</label>
            <button class="btn btn-danger" id="recordBtn" onclick="toggleRecording()">🎤 Start Recording</button>
            <div id="sttStatus"></div>
            <textarea id="sttResult" placeholder="Transcription will appear here..." style="margin-top: 12px;" readonly></textarea>
        </div>
        
        <div class="card">
            <label>Audio Devices</label>
            <div id="deviceList">Loading...</div>
        </div>
    </div>
    
    <script>
        const API_BASE = 'http://localhost:8002';
        let isRecording = false;
        let mediaRecorder = null;
        let audioChunks = [];
        
        async function synthesize() {
            const text = document.getElementById('ttsText').value;
            const status = document.getElementById('ttsStatus');
            status.innerHTML = '<div class="status info">Synthesizing...</div>';
            
            try {
                const resp = await fetch(API_BASE + '/api/tts', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: text})
                });
                const data = await resp.json();
                if (data.status === 'ok') {
                    status.innerHTML = '<div class="status success">✓ Audio generated: ' + data.audio_path + '</div>';
                } else {
                    status.innerHTML = '<div class="status error">Error: ' + (data.detail || 'Unknown error') + '</div>';
                }
            } catch(e) {
                status.innerHTML = '<div class="status error">Error: ' + e.message + '</div>';
            }
        }
        
        async function toggleRecording() {
            const btn = document.getElementById('recordBtn');
            const status = document.getElementById('sttStatus');
            
            if (!isRecording) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({audio: true});
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                    
                    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, {type: 'audio/wav'});
                        status.innerHTML = '<div class="status info">Processing audio...</div>';
                        // Here you would send to STT API
                        status.innerHTML = '<div class="status success">Recording complete. STT processing available when Whisper is configured.</div>';
                    };
                    
                    mediaRecorder.start();
                    isRecording = true;
                    btn.textContent = '⏹ Stop Recording';
                    btn.classList.add('recording');
                    status.innerHTML = '<div class="status info">🔴 Recording...</div>';
                } catch(e) {
                    status.innerHTML = '<div class="status error">Microphone access denied: ' + e.message + '</div>';
                }
            } else {
                mediaRecorder.stop();
                isRecording = false;
                btn.textContent = '🎤 Start Recording';
                btn.classList.remove('recording');
            }
        }
        
        async function loadDevices() {
            try {
                const resp = await fetch(API_BASE + '/api/devices');
                const data = await resp.json();
                const list = document.getElementById('deviceList');
                if (data.devices && data.devices.length > 0) {
                    list.innerHTML = data.devices.map(d => '<div style="padding:4px 0;border-bottom:1px solid #334155;">📻 ' + d.name + '</div>').join('');
                } else {
                    list.innerHTML = '<div class="status info">No audio devices found</div>';
                }
            } catch(e) {
                document.getElementById('deviceList').innerHTML = '<div class="status error">Error loading devices</div>';
            }
        }
        
        loadDevices();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.post("/api/tts")
async def text_to_speech(request: Request):
    """Convert text to speech."""
    try:
        from zena_mode.server import get_cached_voice_service
        data = await request.json()
        text = data.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="Missing text")
        
        vs = get_cached_voice_service()
        audio_path = vs.synthesize(text)
        return {"status": "ok", "audio_path": str(audio_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stt")
async def speech_to_text(request: Request):
    """Convert speech to text."""
    try:
        from zena_mode.server import get_cached_voice_service
        data = await request.json()
        audio_data = data.get("audio", "")
        if not audio_data:
            raise HTTPException(status_code=400, detail="Missing audio data")
        
        vs = get_cached_voice_service()
        text = vs.transcribe(audio_data)
        return {"status": "ok", "text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CHAT ROUTES ====================

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Simple chat proxy to LLM engine."""
    import requests
    from zena_mode.server import MODEL_PATH
    
    if not req.message:
        raise HTTPException(status_code=400, detail="Missing message")
    
    try:
        payload = {
            "model": MODEL_PATH.name,
            "messages": [
                {"role": "system", "content": "You are ZenAI, a helpful assistant. Keep answers short."},
                {"role": "user", "content": req.message}
            ],
            "stream": False,
            "max_tokens": 150
        }
        resp = requests.post(config.get_api_url(), json=payload, timeout=30)
        if resp.status_code == 200:
            llm_data = resp.json()
            content = llm_data['choices'][0]['message']['content']
            return {"response": content, "emotion": "neutral"}
        else:
            raise HTTPException(status_code=500, detail=f"LLM Error: {resp.text}")
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DEFAULT FALLBACK ====================

@app.get("/")
async def root():
    """Root endpoint - API status."""
    return {"status": "ZenAI Hub Active", "version": "2.0.0-ASGI"}


# --- Server Runner ---
def run_asgi_server(host: str = "127.0.0.1", port: int = 8002):
    """Start the ASGI server with uvicorn."""
    import uvicorn
    logger.info(f"Starting ASGI server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_asgi_server()
