import os
import sys
import subprocess
import platform
import json
import time
import threading
from pathlib import Path
from typing import NoReturn
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import asyncio
try:
    import websockets
except ImportError:
    websockets = None

# --- Shared Imports ---
from config import BASE_DIR, MODEL_DIR, BIN_DIR, PORTS, HOST, DEFAULTS
from utils import logger, trace_log, kill_process_by_name, kill_process_by_port, HardwareProfiler, ensure_package

# Suppress HuggingFace/Windows symlink warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Ensure dependencies (psutil)
# Ensure dependencies (psutil)
ensure_package("psutil")

"""
start_llm.py - Nebula Management API (Ver 3.2 - Refactored)
Orchestrates model lifecycle and hot-swapping.
"""

# Alias needed for backwards compat if referenced dynamically, 
# but ideally we use config.MODEL_DIR now.
MODEL_PATH: Path = MODEL_DIR / "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
SERVER_EXE: Path = BIN_DIR / "llama-server.exe"
SERVER_PROCESS = None

class NebulaOrchestrator(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def send_json_response(self, status_code: int, data: dict):
        """Helper to standardize JSON responses."""
        try:
            body = json.dumps(data).encode()
            self.send_response(status_code)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            logger.error(f"Error sending JSON response: {e}")

    def do_GET(self):
        # Handle /updates/check first
        if self.path == '/updates/check':
             self.do_GET_updates()
             return
             
        if self.path == '/models/popular':
            try:
                import model_manager
                results = model_manager.list_available_models()
                self.send_json_response(200, results)
                return
            except Exception as e:
                logger.error(f"Popular Models Error: {e}")
                self.send_json_response(500, {"error": str(e)})
                return
             
        if self.path.startswith('/assets/'):
             # Serve static assets (worker.js etc) with correct MIME types
             file_path = BASE_DIR / self.path.lstrip('/')
             if file_path.exists() and file_path.is_file():
                 self.send_response(200)
                 self.send_header('Access-Control-Allow-Origin', '*')
                 if file_path.suffix == '.js':
                     self.send_header('Content-Type', 'application/javascript')
                 elif file_path.suffix == '.wasm':
                     self.send_header('Content-Type', 'application/wasm')
                 self.end_headers()
                 with open(file_path, 'rb') as f:
                     self.wfile.write(f.read())
             else:
                 self.send_error(404, "File not found")
             return

        if self.path == '/list':
            active_name = MODEL_PATH.name
            models = []
            if MODEL_DIR.exists():
                for f in MODEL_DIR.glob("*.gguf"):
                    models.append({"name": f.name, "active": f.name == active_name})
            self.send_json_response(200, models)
            
        elif self.path == '/startup/progress':
             # Build response body first, then send headers+body together
             try:
                # Check for Manager Mode flag (implicit if MODEL_PATH doesn't exist)
                if not MODEL_PATH.exists():
                     response_body = json.dumps({
                        "stage": "manager_mode",
                        "percent": 100, 
                        "message": "Manager Mode Active",
                        "eta_seconds": 0
                    }).encode()
                else:
                    from startup_progress import get_startup_progress
                    progress = get_startup_progress()
                    response_body = json.dumps(progress).encode()
             except ImportError:
                response_body = json.dumps({
                    "stage": "unknown",
                    "percent": 0,
                    "message": "Initializing...",
                    "eta_seconds": 0
                }).encode()
             except Exception as e:
                # Catch-all to prevent ERR_EMPTY_RESPONSE
                response_body = json.dumps({
                    "stage": "error",
                    "percent": 0,
                    "message": f"Error: {str(e)}",
                    "eta_seconds": 0
                }).encode()
             
             # Now send headers and body atomically
             self.send_response(200)
             self.send_header('Access-Control-Allow-Origin', '*')
             self.send_header('Content-Type', 'application/json')
             self.send_header('Content-Length', str(len(response_body)))
             self.end_headers()
             self.wfile.write(response_body)

        elif self.path == '/model/status':
            # USE GLOBAL MODEL_PATH
            info = {
                "model": MODEL_PATH.name,
                "loaded": bool(SERVER_PROCESS),
                "engine_port": 8001
            }
            self.send_json_response(200, info)
            return
        elif self.path == '/models/available':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            try:
                # FIX: Use get_installed_models (local files) instead of list_available_models (catalog)
                from model_manager import get_installed_models
                installed = get_installed_models()
                # UI expects a list of strings (filenames), not dicts
                model_names = [m['name'] for m in installed]
                self.wfile.write(json.dumps(model_names).encode())
            except Exception as e:
                logger.error(f"Error listing models: {e}")
                self.wfile.write(json.dumps([]).encode())

        elif self.path.startswith('/models/progress/'):
            # Get progress for specific file: /models/progress/filename.gguf
            try:
                filename = self.path.split('/')[-1]
                from model_manager import get_download_progress
                progress = get_download_progress(filename)
                
                if progress:
                    body = json.dumps(progress).encode()
                else:
                    body = json.dumps({"status": "not_found"}).encode()

                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body))) # Critical for robust client parsing
                self.end_headers()
                self.wfile.write(body)

            except Exception as e:
                logger.error(f"Error getting progress for {self.path}: {e}")
                # Try to return valid JSON error
                try:
                    err_body = json.dumps({"error": str(e)}).encode()
                    self.send_response(500)
                    self.send_header('Content-Length', str(len(err_body)))
                    self.end_headers()
                    self.wfile.write(err_body)
                except: pass
        else:
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Nebula Hub Active")

    def do_GET_updates(self):
        """Handle /updates/check request."""
        try:
            import update_checker
            report = update_checker.check_all()
            self.send_json_response(200, report)
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            self.send_json_response(500, {"error": str(e)})
            
    def do_POST(self):
        if self.path == '/swap':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data)
            model_name = params.get('model')
            logger.info(f"[HUB] Swap requested: {model_name}")
            
            # Initiate restart in a separate thread so we can reply to UI
            threading.Thread(target=restart_with_model, args=(model_name,)).start()
            
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b"Accepted")
        elif self.path == '/models/download':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data)
            # Support both new (repo_id) and legacy (repo) keys
            repo_id = params.get('repo_id') or params.get('repo')
            filename = params.get('filename') or params.get('file')
            
            logger.info(f"[HUB] Download requested: {repo_id}/{filename}")
            
            def safe_download_task(r_id, f_name):
                try:
                    import model_manager
                    model_manager.download_model(r_id, f_name)
                    logger.info(f"[HUB] Download completed: {f_name}")
                except ImportError:
                    logger.error("[HUB] Critical: model_manager module not found!")
                except Exception as e:
                    logger.error(f"[HUB] Download thread failed: {e}", exc_info=True)

            # Check inputs
            if not repo_id or not filename:
                 self.send_json_response(400, {"error": "Missing repo_id or filename"})
                 return

            # Start background thread
            threading.Thread(target=safe_download_task, args=(repo_id, filename)).start()
            
            self.send_json_response(200, {"status": "started", "message": f"Downloading {filename}..."})
                
        elif self.path == '/models/search':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data)
            query = params.get('query', '')
            
            try:
                import model_manager
                results = model_manager.search_huggingface(query)
                # Enhance with smart parsing
                for r in results:
                    info = model_manager.parse_model_info(r['name'])
                    r.update(info)
                    
                self.send_json_response(200, results)
            except Exception as e:
                logger.error(f"Search Error: {e}")
                self.send_json_response(500, {"error": str(e)})





        elif self.path == '/files/upload':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                filename = self.headers.get('X-Filename', f"upload_{int(time.time())}.bin")
                filename = os.path.basename(filename) # Sanitize
                
                UPLOAD_DIR = BASE_DIR / "uploads"
                UPLOAD_DIR.mkdir(exist_ok=True)
                
                file_data = self.rfile.read(content_length)
                target_path = UPLOAD_DIR / filename
                
                with open(target_path, "wb") as f:
                    f.write(file_data)
                    
                logger.info(f"[Upload] Saved {filename} ({content_length} bytes)")
                
                logger.info(f"[Upload] Saved {filename} ({content_length} bytes)")
                
                self.send_json_response(200, {"status": "success", "path": str(target_path)})
            except Exception as e:
                logger.error(f"[Upload] Error: {e}")
                self.send_json_response(500, {"error": str(e)})

        elif self.path == '/voice/transcribe':
            # Security: Limit upload size to prevent memory exhaustion
            MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length > MAX_UPLOAD_SIZE:
                self.send_json_response(413, {"error": f"File too large. Max size: {MAX_UPLOAD_SIZE // 1024 // 1024} MB"})
                logger.warning(f"[Voice] Upload rejected: {content_length} bytes exceeds limit")
                return
            
            audio_data = self.rfile.read(content_length)
            
            logger.info(f"[Voice] Transcribing {len(audio_data)} bytes...")
            
            try:
                from voice_service import get_voice_service
                # Use a BytesIO wrapper for the raw data
                import io
                audio_file = io.BytesIO(audio_data)
                
                # Get service (lazy loads model)
                vs = get_voice_service(BASE_DIR / "voice_models")
                result = vs.transcribe_audio(audio_file)
                
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            except Exception as e:
                logger.error(f"[Voice] Transcription error: {e}")
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif self.path == '/voice/tts':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data)
            text = params.get('text', '')
            
            logger.info(f"[Voice] TTS Request: {text[:50]}...")
            
            try:
                from voice_service import get_voice_service
                vs = get_voice_service(BASE_DIR / "voice_models")
                audio_bytes = vs.synthesize_speech(text)
                
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'audio/wav')
                self.end_headers()
                self.wfile.write(audio_bytes)
                
            except Exception as e:
                logger.error(f"[Voice] TTS error: {e}")
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(str(e).encode())

        elif self.path == '/agents/list':
            # List all available agents
            try:
                from agent_manager import get_agent_manager
                manager = get_agent_manager(BASE_DIR / "agents")
                agents = manager.list_agents()
                
                self.send_json_response(200, {"agents": agents})
            except Exception as e:
                logger.error(f"[Agents] List error: {e}")
                self.send_json_response(500, {"error": str(e)})

        elif self.path == '/agents/create':
            # Create new agent
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                params = json.loads(post_data)
                
                from agent_manager import get_agent_manager
                manager = get_agent_manager(BASE_DIR / "agents")
                
                success, error, agent_id = manager.create_agent(
                    name=params.get('name'),
                    description=params.get('description', ''),
                    system_prompt=params.get('systemPrompt'),
                    model=params.get('model', 'auto'),
                    temperature=params.get('temperature', 0.7)
                )
                
                if success:
                    self.send_json_response(200, {"success": True, "agentId": agent_id})
                else:
                    self.send_json_response(400, {"success": False, "error": error})
                    
            except Exception as e:
                logger.error(f"[Agents] Create error: {e}")
                self.send_json_response(500, {"error": str(e)})

        elif self.path.startswith('/agents/delete/'):
            # Delete agent by ID
            try:
                agent_id = self.path.split('/')[-1]
                
                from agent_manager import get_agent_manager
                manager = get_agent_manager(BASE_DIR / "agents")
                
                success, error = manager.delete_agent(agent_id)
                
                if success:
                    self.send_json_response(200, {"success": True})
                else:
                    self.send_json_response(400, {"success": False, "error": error})
                    
            except Exception as e:
                logger.error(f"[Agents] Delete error: {e}")
                self.send_json_response(500, {"error": str(e)})

        elif self.path == '/search':
            # Perform web search
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                params = json.loads(post_data)
                query = params.get('query')
                
                if not query:
                    raise ValueError("Query parameter required")
                
                from search_engine import perform_search
                results = perform_search(query)
                
                self.send_json_response(200, {"results": results})
                
            except Exception as e:
                logger.error(f"[Search] Error: {e}")
                self.send_json_response(500, {"error": str(e)})

def restart_with_model(name):
    logger.info(f"[HUB] Killing model engine...")
    kill_process_by_name("llama-server.exe")
    time.sleep(2)
    logger.info(f"[HUB] Relaunching with {name}...")
    # Pass the model name as an argument to the NEXT instance
    cmd = [sys.executable, __file__, "--guard-bypass", "--model", name]
    subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
    os._exit(0)

def instance_guard():
    """Ensure no other LLM servers or launchers are running."""
    logger.info("[*] Instance Guard: Cleaning environment...")
    kill_process_by_name("llama-server.exe")

# --- Voice Streaming Server ---
class VoiceStreamHandler:
    def __init__(self):
        self.clients = set()

    async def handle_client(self, websocket):
        """
        Handle WebSocket connection for voice streaming.
        Protocol:
        - Client sends binary audio chunks (Int16 PCM)
        - Server sends JSON: {"text": "...", "is_final": bool}
        """
        from voice_service import get_voice_service
        
        logger.info(f"[WS] Client connected: {websocket.remote_address}")
        self.clients.add(websocket)
        
        # Create a new processor for this session
        try:
            vs = get_voice_service(BASE_DIR / "voice_models")
            processor = vs.create_stream_processor()
            
            async for message in websocket:
                if isinstance(message, bytes):
                    # Audio chunk
                    processor.add_audio(message)
                    
                    # Process periodically (or every chunk if fast enough)
                    result = processor.process()
                    
                    if result:
                        await websocket.send(json.dumps(result))
                        
                elif isinstance(message, str):
                    # Control messages (e.g. "stop", "reset")
                    try:
                        cmd = json.loads(message)
                        if cmd.get("action") == "stop":
                             final_result = processor.finish()
                             await websocket.send(json.dumps(final_result))
                    except: pass
        
        except Exception as e:
            logger.error(f"[WS] Error: {e}")
        finally:
            self.clients.remove(websocket)
            logger.info(f"[WS] Client disconnected")

async def run_ws_server():
    if websockets is None:
        logger.error("[WS] 'websockets' lib not found. Streaming disabled.")
        return

    handler = VoiceStreamHandler()
    logger.info("[WS] Starting Voice Stream Server on Port 8003...")
    # Ping interval checks connection health every 20s
    async with websockets.serve(handler.handle_client, "0.0.0.0", 8003, ping_interval=20):
        await asyncio.Future()  # Run forever

def start_voice_stream_server():
    """Start the WebSocket server in a background thread."""
    if websockets is None:
        print("[!] 'websockets' library missing. Streaming voice disabled.")
        return

    # Kill any existing process on port 8003 to prevent OSError [Errno 10048]
    try:
        kill_process_by_port(8003)
    except Exception as e:
        logger.warning(f"[WS] Port cleanup warning: {e}")
    
    def run_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_ws_server())
        except RuntimeError as e:
            logger.error(f"[WS] Thread Loop Error: {e}")
        finally:
            loop.close()

    t = threading.Thread(target=run_loop, daemon=True)
    t.start()
    
def env_int(name: str, default: int) -> int:
    val = os.environ.get(name, "").strip()
    if not val.isdigit():
        return default
    num = int(val)
    return max(0, min(num, 2**31 - 1))  # Clamp to safe range

def self_heal():
    logger.warning("[!] Missing components detected (binaries or models).")
    logger.warning("[!] Please run 'python Create_Local_LLM.py' to repair the environment.")
    sys.exit(1)

def start_hub():
    """Start the Management API (Hub) in a background thread"""
    try:
        hub = None
        mgmt_port = PORTS["MGMT_API"]
        for _ in range(3):
            try:
                hub = ThreadingHTTPServer(('127.0.0.1', mgmt_port), NebulaOrchestrator)
                break
            except:
                time.sleep(1)
        
        if not hub:
            print("[!] Could not bind Hub API to Port 8002. Port in use.")
            # Non-fatal for LLM, but fatal for UI control. 
            # We continue so at least the engine runs.
            return

        threading.Thread(target=hub.serve_forever, daemon=True).start()
        print("[*] Nebula Hub API listening on Port 8002")
    except Exception as e:
        print(f"[!] Hub Startup Failed: {e}")

def start_server() -> NoReturn:
    global MODEL_PATH
    # Critical Check: Binaries
    if not SERVER_EXE.exists():
        logger.error(f"[!] Server binary not found at {SERVER_EXE}")
        logger.error("    Please run: python download_deps.py")
        sys.exit(1)

    # Check for Visual C++ Redistributable (Windows Only)
    if sys.platform == "win32":
        import ctypes.util
        msvcp = ctypes.util.find_library("msvcp140")
        if not msvcp:
            # Fallback check in System32 directly if find_library fails
            sys32 = Path(os.environ["SystemRoot"]) / "System32"
            if not (sys32 / "msvcp140.dll").exists():
                 logger.error("="*60)
                 logger.error("CRITICAL ERROR: Visual C++ Redistributable 2015+ Missing")
                 logger.error("="*60)
                 logger.error("The Nebula Engine requires MSVCP140.dll to run.")
                 logger.error("Please download and install 'vc_redist.x64.exe' from Microsoft:")
                 logger.error("https://aka.ms/vs/17/release/vc_redist.x64.exe")
                 logger.error("="*60)
                 # We don't exit here, we let it try (and fail with popup), but the log is clear.
                 # Actually, better to pause so they see it?
                 # No, just log it clearly.
                 print("\n[!] MISSING DEPENDENCY: Visual C++ Redistributable (MSVCP140.dll)")
                 print("    Download: https://aka.ms/vs/17/release/vc_redist.x64.exe\n")
                 input("Press Enter to exit...") # Keep window open
                 sys.exit(1)

    # Partial Check: Models
    # Smart Detection: If default model missing, try to find ANY .gguf model
    if not MODEL_PATH.exists():
        candidates = list(MODEL_DIR.glob("*.gguf"))
        if candidates:
            # Sort by size (descending) as a heuristic for "main" model, or just pick first
            # Picking the largest file is usually safer than a tiny draft model
            candidates.sort(key=lambda x: x.stat().st_size, reverse=True)
            MODEL_PATH = candidates[0]
            print(f"\n[*] Auto-detected available model: {MODEL_PATH.name}")
        else:
            # TRULY missing -> Manager Mode
            print(f"\n[!] Default model not found: {MODEL_PATH.name}")
            print(f"[!] No models found in: {MODEL_DIR}")
            print("[*] Starting in MANAGER MODE (Hub Only)")
            print("    Please open the Web UI to download a model.")
            
            start_hub()
            print("    Hub Active on http://127.0.0.1:8002")
            
            # specific loop to keep main thread alive while Hub runs
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Exiting...")
                return
    
    # If we get here, model exists -> Full Launch

    # HARDCODED SAFE DEFAULTS (Prevent Startup Hangs)
    profile = {'cpu': 'Generic', 'ram_gb': 16, 'type': 'CPU'}
    print("[*] Universal Launcher: Starting...")
    print(f"[*] Config used: MODEL_DIR={MODEL_DIR}") 
    print(f"[*] Target Model: {MODEL_PATH}")

    # Dynamic Tuning
    try:
        import psutil
        physical_cores = psutil.cpu_count(logical=False) or 4
        logical_cores = psutil.cpu_count(logical=True) or 4
    except ImportError:
        logical_cores = os.cpu_count() or 4
        physical_cores = logical_cores // 2 # Rough heuristic for Hyperthreading
    
    # Heuristic: LLMs prefer physical cores. Using all logical cores often slows down due to context switching.
    default_threads = physical_cores
    
    port = env_int("LLM_PORT", 8001)
    
    # CLI Overrides for Context
    ctx = 8192 # Default reduced to 8k for speed. User can override.
    if "--ctx" in sys.argv:
        try:
            ctx_idx = sys.argv.index("--ctx")
            ctx = int(sys.argv[ctx_idx+1])
        except: pass
    else:
        ctx = env_int("LLM_CTX", 8192)

    threads = env_int("LLM_THREADS", default_threads)
    threads_batch = env_int("LLM_THREADS_BATCH", max(1, threads))
    
    # 96GB RAM Nitro vs 16GB RAM Safe
    is_high_end = profile['ram_gb'] > 32
    batch = env_int("LLM_BATCH", 512) # Lower batch for lower latency
    ubatch = env_int("LLM_UBATCH", 512) 
    
    gpu_layers = env_int("LLM_GPU_LAYERS", 0) 
    
    if os.environ.get("LLM_NITRO", "").lower() == "true":
        gpu_layers, ubatch = 99, 1024
        print("[!] NITRO MODE FORCED.")

    cmd = [
        str(SERVER_EXE),
        "--model", str(MODEL_PATH),
        "--host", "0.0.0.0",
        "--port", str(port),
        "--ctx-size", str(ctx),
        "--n-gpu-layers", str(gpu_layers),
        "--threads", str(threads),
        "--threads-batch", str(threads_batch),
        "--batch-size", str(batch),
        "--ubatch-size", str(ubatch),
        "--flash-attn",
        # Reverting to default f16 cache for compatibility with current binary
        "--repeat-penalty", "1.1",
        "--repeat-last-n", "1024",
        "--min-p", "0.1",
        "--alias", "local-model",
        "--no-warmup"
    ]

    try:
        # Start Hub API on MGMT_API (Moved to top for instant responsiveness)
        start_hub()
        
        # Start Voice Stream Server
        start_voice_stream_server()

        print(f"\n[*] Launching optimized llama.cpp (v0.5.4-REV3)")
        print(f"    Layers: {gpu_layers} | Threads: {threads} | Ubatch: {ubatch}")
        
        # --- PATH Injection Fix ---
        # Ensure binaries can find sibling DLLs (ggml.dll, etc.)
        current_path = os.environ.get("PATH", "")
        if str(BIN_DIR) not in current_path:
             os.environ["PATH"] = str(BIN_DIR) + os.pathsep + current_path
             logger.info(f"[Init] Added {BIN_DIR} to PATH")

        global SERVER_PROCESS
        SERVER_PROCESS = subprocess.Popen(cmd, env=os.environ, cwd=BIN_DIR) # Run inside BIN_DIR for safety
        print(f"[*] Engine Active (PID: {SERVER_PROCESS.pid})")
        
        # --- UI Launch (Early) ---
        print("[*] Launching Nebula UI...")
        print("[*] Launching Zena AI (NiceGUI)...")
        # Fix: Ensure we CD into the directory first so imports and file lookups work
        subprocess.Popen(f'start cmd /k "cd /d "{BASE_DIR}" && {sys.executable} zena.py"', shell=True)
        
        # --- BENCHMARK & WELCOME ---
        print("\n[*] Waiting for engine readiness & running benchmark...")
        try:
            import benchmark
            stats = benchmark.measure_tps(api_url="http://127.0.0.1:8001")
            
            print("\n" + "="*60)
            print("       ✨ WELCOME TO NEBULA LOCAL AI ✨")
            print("="*60)
            if stats["success"]:
                print(f"  Model:      {MODEL_PATH.name}")
                print(f"  Speed:      {stats['tps']:.2f} tokens/sec")
                print(f"  Rating:     {stats['rating']}")
                print(f"  Latency:    {stats['gen_time']:.2f}s")
            else:
                print(f"  Benchmark:  FAILED ({stats.get('error')})")
            print("="*60 + "\n")
            
        except ImportError:
            print("[!] Benchmark module not found.")
        except Exception as e:
            print(f"[!] Startup benchmark failed: {e}")


        
        exit_code = SERVER_PROCESS.wait()
        
        if exit_code != 0:
            logger.error(f"[!] Engine exited unexpectedly with code {exit_code}")
            print("[!] Possible causes: Missing VC++ Redistributable, incompatible CPU (AVX), or port conflict.")
            input("Press Enter to return to menu...")
            sys.exit(exit_code)
            
    except KeyboardInterrupt:
        logger.info("[!] Interrupt received. Shutting down engine...")
        try: kill_process_tree(process.pid)
        except: pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[!] Error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    if "--hub-only" in sys.argv:
        print("[*] Starting in HUB ONLY mode (No Engine)...")
        # Ensure dependencies for Hub
        try:
            import model_manager
        except ImportError:
            print("[!] Warning: model_manager not found")
            
        start_hub()
        print("    Hub Active on http://127.0.0.1:8002")
        print("    Press Ctrl+C to exit")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(0)
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        passed_model = sys.argv[idx+1]
        # Allow absolute path or relative to MODEL_DIR
        potential_path = Path(passed_model)
        if potential_path.is_absolute() and potential_path.exists():
             MODEL_PATH = potential_path
             print(f"[*] Dynamic Model Override (Absolute): {MODEL_PATH.name}")
        elif (MODEL_DIR / passed_model).exists():
            MODEL_PATH = MODEL_DIR / passed_model
            print(f"[*] Dynamic Model Override (Relative): {MODEL_PATH.name}")
        else:
            print(f"[!] Warning: override model {passed_model} not found.")

    if "--guard-bypass" not in sys.argv:
        instance_guard()
    start_server()
