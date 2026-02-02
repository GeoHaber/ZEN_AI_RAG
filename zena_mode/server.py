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
from utils import (
    logger, HardwareProfiler, ensure_package, safe_print, 
    ProcessManager, is_port_active, kill_process_by_name
)
from config_system import config
ensure_package("psutil")
import psutil


# Global Variables (Derived from Config)
MODEL_PATH = config.MODEL_DIR / config.default_model
SERVER_EXE = config.BIN_DIR / "llama-server.exe"

# Suppress HuggingFace/Windows symlink warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# --- DEADLOCK FIX: Log Relay ---
# --- DEADLOCK FIX: Log Relay ---
class LogRelay(threading.Thread):
    """
    Reads stdout from a subprocess in a non-blocking thread and logs it.
    Prevents pipe buffer deadlocks on Windows.
    Hardened: Uses chunk-based reading to handle non-newline output and binary artifacts.
    """
    def __init__(self, process, prefix="[Engine]", chunk_size=1024):
        super().__init__(daemon=True)
        self.process = process
        self.prefix = prefix
        self.chunk_size = chunk_size
        self._stop_event = threading.Event()
        self.last_lines = [] # "Last Words" buffer
        self.buffer_lock = threading.Lock()

    def run(self):
        try:
            while not self._stop_event.is_set():
                if not self.process: break
                
                # Binary read of 1024 bytes
                try:
                    chunk = self.process.stdout.read(1024)
                except (ValueError, AttributeError, OSError):
                    break # Process closed
                
                if not chunk:
                    # Check if process died
                    try:
                        if self.process.poll() is not None: break
                    except AttributeError: break
                    time.sleep(0.1)
                    continue

                # Simple decode and log
                try:
                    text = chunk.decode('utf-8', errors='replace').strip()
                    if text:
                        # Log non-empty blocks
                        for line in text.split('\n'):
                            clean_line = line.strip()
                            if clean_line:
                                logger.info(f"{self.prefix} {clean_line}")
                                with self.buffer_lock:
                                    self.last_lines.append(clean_line)
                                    if len(self.last_lines) > 10:
                                        self.last_lines.pop(0)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"{self.prefix} Log Relay Error: {e}")
        finally:
            try:
                if self.process and self.process.stdout:
                    self.process.stdout.close()
            except:
                pass

def safe_exit(code: int = 0, delay: float = 0.5):
    """Safely exit the application, ensuring all output is flushed first."""
    time.sleep(delay)
    sys.exit(code)

def validate_environment():
    """Pre-flight validation: Check binaries, models, and dependencies."""
    safe_print("[Pre-flight] Validating core components...")
    
    # 1. Engine Binary
    if not SERVER_EXE.exists():
        safe_print(f"❌ Error: Engine binary not found: {SERVER_EXE}")
        return False
    if SERVER_EXE.stat().st_size < 1000:
        safe_print(f"❌ Error: Engine binary seems corrupted (size too small).")
        return False

    # 2. Model File
    if not MODEL_PATH.exists():
        safe_print(f"❌ Error: Model file not found: {MODEL_PATH}")
        return False
    if MODEL_PATH.stat().st_size < 1000000: # < 1MB is likely a placeholder
        safe_print(f"❌ Error: Model file seems corrupted or incomplete: {MODEL_PATH}")
        return False
        
    # 3. Port Check (Self-Correction)
    critical_ports = [PORTS["LLM_API"], PORTS["MGMT_API"]]
    for port in critical_ports:
        if is_port_active(port):
            safe_print(f"⚠️ Port {port} is ALREADY ACTIVE. Attempting cleanup...")
            # This is a fallback in case zombie_killer missed it
            kill_process_by_port(port)
            time.sleep(1)
            if is_port_active(port):
                safe_print(f"❌ Error: Port {port} is held by an unkillable process.")
                return False

    safe_print("✅ Pre-flight validation: SUCCESS")
    return True



# Server lifecycle management
SERVER_PROCESS = None
EXPERT_PROCESSES = {}  # {port: subprocess.Popen}
EXPERT_LOCK = threading.Lock()

# Process Monitoring
MONITORED_PROCESSES = {}  # {name: {"process": Popen, "critical": bool, ...}}
PROCESS_LOCK = threading.Lock()
MODEL_PATH_LOCK = threading.Lock()

def register_process(name, process, critical=False):
    """Register a process for health monitoring."""
    with PROCESS_LOCK:
        MONITORED_PROCESSES[name] = {
            "process": process,
            "critical": critical,
            "restarts": 0,
            "max_restarts": 3 if critical else 1,
            "start_time": time.time()
        }
    logger.info(f"[Monitor] Registered {'CRITICAL ' if critical else ''}process: {name} (PID: {process.pid})")

def check_processes():
    """Check health of all monitored processes. Returns list of crashed ones."""
    crashed = []
    with PROCESS_LOCK:
        to_remove = []
        for name, info in MONITORED_PROCESSES.items():
            proc = info["process"]
            try:
                exit_code = proc.poll()
                if exit_code is not None:
                    crashed.append((name, exit_code, info["critical"]))
                    to_remove.append(name)
            except Exception as e:
                logger.error(f"[Monitor] Error checking {name}: {e}")
                to_remove.append(name)
        
        for name in to_remove:
            del MONITORED_PROCESSES[name]
    return crashed

# Lazy Loading Wrappers
_model_manager_cache = None
_voice_service_cache = None

def get_model_manager():
    global _model_manager_cache
    if _model_manager_cache is None:
        try:
            import model_manager
            _model_manager_cache = model_manager
        except ImportError:
            raise ImportError("model_manager module not found")
    return _model_manager_cache

def get_cached_voice_service():
    global _voice_service_cache
    if _voice_service_cache is None:
        try:
            import voice_service
            _voice_service_cache = voice_service
        except ImportError:
            raise ImportError("voice_service module not found")
    return _voice_service_cache

class ZenAIOrchestrator(BaseHTTPRequestHandler):
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
        if self.path == '/voice/lab':
             # Serve index.html or redirect
             lab_path = config.BASE_DIR / "experimental_voice_lab" / "templates" / "index.html"
             if not lab_path.exists():
                 self.send_json_response(404, {"error": "Voice Lab template not found"})
                 return
             with open(lab_path, 'r', encoding='utf-8') as f:
                 html = f.read()
             self.send_response(200)
             self.send_header('Content-Type', 'text/html')
             self.end_headers()
             self.wfile.write(html.encode('utf-8'))
             
        elif self.path.startswith('/voice/static/'):
             file_path = config.BASE_DIR / self.path.lstrip('/')
             if file_path.exists() and file_path.is_file():
                 self.send_response(200)
                 self.send_header('Access-Control-Allow-Origin', '*')
                 # Determine MIME type based on extension
                 mime_type, _ = mimetypes.guess_type(file_path)
                 if mime_type:
                     self.send_header('Content-Type', mime_type)
                 else:
                     self.send_header('Content-Type', 'application/octet-stream') # Default
                 self.end_headers()
                 with open(file_path, 'rb') as f:
                     self.wfile.write(f.read())
             else:
                 self.send_error(404, "Static file not found")
             return

        # Handle /updates/check first
        if self.path == '/updates/check':
             self.do_GET_updates()
             return
             
        if self.path == '/models/popular':
            try:
                mm = get_model_manager()
                results = mm.list_available_models()
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
             try:
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
                response_body = json.dumps({
                    "stage": "error",
                    "percent": 0,
                    "message": f"Error: {str(e)}",
                    "eta_seconds": 0
                }).encode()
             
             self.send_response(200)
             self.send_header('Access-Control-Allow-Origin', '*')
             self.send_header('Content-Type', 'application/json')
             self.send_header('Content-Length', str(len(response_body)))
             self.end_headers()
             self.wfile.write(response_body)

        elif self.path == '/model/status':
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
                mm = get_model_manager()
                installed = mm.get_installed_models()
                model_names = [m['name'] for m in installed]
                self.wfile.write(json.dumps(model_names).encode())
            except Exception as e:
                logger.error(f"Error listing models: {e}")
                self.wfile.write(json.dumps([]).encode())

        elif self.path.startswith('/models/progress/'):
            try:
                filename = self.path.split('/')[-1]
                mm = get_model_manager()
                progress = mm.get_download_progress(filename)
                
                if progress:
                    body = json.dumps(progress).encode()
                else:
                    body = json.dumps({"status": "not_found"}).encode()

                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                logger.error(f"Error getting progress: {e}")
                self.send_json_response(500, {"error": str(e)})
        else:
            self.send_json_response(200, {"status": "ZenAI Hub Active"})

    def do_GET_updates(self):
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
            
            threading.Thread(target=restart_with_model, args=(model_name,)).start()
            self.send_json_response(200, {"status": "accepted"})

        elif self.path == '/models/download':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data)
            repo_id = params.get('repo_id') or params.get('repo')
            filename = params.get('filename') or params.get('file')
            
            def safe_download_task(r_id, f_name):
                try:
                    mm = get_model_manager()
                    mm.download_model(r_id, f_name)
                except Exception as e:
                    logger.error(f"[HUB] Download failed: {e}")

            if not repo_id or not filename:
                 self.send_json_response(400, {"error": "Missing repo_id or filename"})
                 return

            threading.Thread(target=safe_download_task, args=(repo_id, filename)).start()
            self.send_json_response(200, {"status": "started"})
                
        elif self.path == '/models/search':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data)
            query = params.get('query', '')
            try:
                mm = get_model_manager()
                results = mm.search_huggingface(query)
                self.send_json_response(200, results)
            except Exception as e:
                self.send_json_response(500, {"error": str(e)})
        
        elif self.path == '/swarm/scale':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data)
            count = params.get('count', 3)
            threading.Thread(target=scale_swarm, args=(count,)).start()
            self.send_json_response(200, {"status": "scaling", "target": count})

        elif self.path == '/files/upload':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                filename = os.path.basename(self.headers.get('X-Filename', 'upload.bin'))
                UPLOAD_DIR = config.BASE_DIR / "uploads"
                UPLOAD_DIR.mkdir(exist_ok=True)
                with open(UPLOAD_DIR / filename, "wb") as f:
                    f.write(self.rfile.read(content_length))
                self.send_json_response(200, {"status": "success"})
            except Exception as e:
                self.send_json_response(500, {"error": str(e)})

        elif self.path == '/voice/transcribe':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                audio_data = self.rfile.read(content_length)
                vs = get_cached_voice_service()
                result = vs.transcribe_audio(io.BytesIO(audio_data))
                self.send_json_response(200, result)
            except Exception as e:
                self.send_json_response(500, {"error": str(e)})

        elif self.path == '/voice/tts':
            try:
                content_length = int(self.headers['Content-Length'])
                params = json.loads(self.rfile.read(content_length))
                vs = get_cached_voice_service()
                audio_bytes = vs.synthesize_speech(params.get('text', ''))
                self.send_response(200)
                self.send_header('Content-Type', 'audio/wav')
                self.end_headers()
                self.wfile.write(audio_bytes)
            except Exception as e:
                self.send_json_response(500, {"error": str(e)})

def env_int(name: str, default: int) -> int:
    """Read integer from environment variable with fallback to default."""
    val = os.environ.get(name, "").strip()
    if not val: return default
    try:
        return int(val)
    except ValueError:
        return default

def build_llama_cmd(port: int, threads: int, ctx: int = 4096, gpu_layers: int = 0, batch: int = 512, ubatch: int = 512, model_path: Path = None, timeout: int = -1, threads_batch: int = None) -> list:
    """Build llama-server.exe command arguments."""
    if model_path is None: model_path = MODEL_PATH
    if threads_batch is None: threads_batch = threads
    return [
        str(SERVER_EXE), "--model", str(model_path), "--host", "127.0.0.1", "--port", str(port),
        "--ctx-size", str(ctx), "--n-gpu-layers", str(gpu_layers), "--threads", str(threads),
        "--threads-batch", str(threads_batch), "--batch-size", str(batch), "--ubatch-size", str(ubatch),
        "--repeat-penalty", "1.1", "--repeat-last-n", "1024", "--min-p", "0.1",
        "--alias", "local-model", "--no-warmup", "--timeout", str(timeout), "-np", "1"
    ]

# Use the implementation from `utils.kill_process_by_name` which is
# imported at module top. Tests patch `utils.psutil.process_iter`, so
# delegating to `utils` ensures consistent, testable behavior.

def restart_with_model(name):
    """Restart engine with a new model using shared utils."""
    from utils import restart_program, kill_process_by_name
    
    kill_process_by_name("llama-server.exe")
    # We rely on the caller/wrapper to handle the model change 
    # (probably via an env var or a config update before restart)
    # But for now, we just restart the program itself.
    restart_program()

def launch_expert_process(port: int, threads: int, model_path: Path = None):
    """Cleanly launch an expert LLM instance."""
    env = os.environ.copy()
    env["LLM_PORT"] = str(port)
    env["LLM_THREADS"] = str(threads)
    script_path = os.path.abspath(__file__)
    cmd = [sys.executable, script_path, "--guard-bypass"]
    if model_path and model_path.exists(): cmd.extend(["--model", str(model_path)])
    elif MODEL_PATH.exists(): cmd.extend(["--model", str(MODEL_PATH)])
    
    # Experts run detached by default (subprocess.CREATE_NO_WINDOW)
    p = subprocess.Popen(cmd, env=env, cwd=os.path.dirname(script_path), creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    register_process(f"Expert-{port}", p)
    return p

def scale_swarm(target_count: int):
    """Dynamically adjust the number of running experts."""
    global EXPERT_PROCESSES
    with EXPERT_LOCK:
        current_ports = sorted(EXPERT_PROCESSES.keys())
        current_count = len(current_ports)
        if target_count > current_count:
            needed = target_count - current_count
            for i in range(needed):
                port = 8005 + len(EXPERT_PROCESSES)
                EXPERT_PROCESSES[port] = launch_expert_process(port, 2)
        elif target_count < current_count:
            to_remove = current_count - target_count
            for _ in range(to_remove):
                port, proc = EXPERT_PROCESSES.popitem()
                ProcessManager.kill_tree(proc.pid)

def start_hub():
    """Start the Management API (Hub)."""
    try:
        safe_print(f"[*] Attempting to start Hub API on port {config.mgmt_port}...")
        hub = ThreadingHTTPServer(('127.0.0.1', config.mgmt_port), ZenAIOrchestrator)
        threading.Thread(target=hub.serve_forever, daemon=True).start()
        safe_print(f"[*] Hub API listening on Port {config.mgmt_port}")
    except Exception as e:
        safe_print(f"❌ Hub Startup Failed: {e}")
        logger.error(f"Hub Startup Failed: {e}")

class VoiceStreamHandler:
    def __init__(self): self.clients = set()
    async def handle_client(self, ws):
        self.clients.add(ws)
        try:
            async for msg in ws: pass
        finally: self.clients.remove(ws)

async def run_ws_server():
    if websockets:
        try:
            async with websockets.serve(VoiceStreamHandler().handle_client, "0.0.0.0", 8003):
                safe_print("[*] Voice Stream Server listening on Port 8003")
                await asyncio.Future()
        except OSError as e:
            if e.errno == 10048:
                safe_print(f"⚠️ Voice Port 8003 busy. Voice features disabled for this session.")
            else:
                logger.error(f"Voice Server Error: {e}")
        except Exception as e:
            logger.error(f"Voice Server Startup Failed: {e}")

def start_voice_stream_server():
    if websockets:
        threading.Thread(target=lambda: asyncio.run(run_ws_server()), daemon=True).start()

def start_server() -> NoReturn:
    global MODEL_PATH, SERVER_PROCESS, EXPERT_PROCESSES
    relay = None
    # 1. Threading and Model Setup
    port = env_int("LLM_PORT", 8001)
    
    if not SERVER_EXE.exists():
        safe_print(f"❌ Critical Error: llama-server.exe NOT FOUND at {SERVER_EXE}")
        sys.exit(1)
    
    if not MODEL_PATH.exists():
        # Try to find any gguf in model dir
        ggufs = list(config.MODEL_DIR.glob("*.gguf"))
        if ggufs:
            MODEL_PATH = ggufs[0]
            logger.info(f"[Engine] Default model missing, using discovered: {MODEL_PATH.name}")
        else:
            safe_print(f"❌ ERROR: No .gguf models found in {config.MODEL_DIR}")
            sys.exit(1)
    
    # Dynamic Thread Scaling - Use tuned values from Orchestrator
    threads = env_int("LLM_THREADS", config.threads) 
    gpu_layers = env_int("LLM_GPU_LAYERS", config.gpu_layers)
    logger.info(f"[Engine] Configured with {threads} threads and {gpu_layers} GPU layers.")
    
    # TTFT Optimization: Increase batch size for faster prompt eval
    # RAG contexts are typically 500-1000 tokens. 2048 handles them in one pass.
    cmd = build_llama_cmd(
        port=port, 
        threads=threads, 
        ctx=config.context_size,
        batch=config.batch_size, 
        ubatch=config.ubatch_size
    ) 
    
    # Apply GPU layers set by Orchestrator
    if "--n-gpu-layers" not in cmd and "--n_gpu_layers" not in cmd:
        cmd.extend(["--n-gpu-layers", str(gpu_layers)])

    # Fix: --cache-reuse takes an integer (min chunk size)
    cmd.extend(["--cache-reuse", "256"])
    
    # Removed --flash-attn as it can cause crashes on unsupported hardware
    
    # 2. Robust Startup Cleanup
    # 2. Startup Guard - Orchestrator handles pruning, but we do a safe check
    if os.environ.get("ZENA_SKIP_PRUNE") != "1":
        safe_print(f"[*] Engine Guard: Ensuring ports are clean...")
        ProcessManager.prune(port, allowed_names=['llama-server.exe', 'python.exe'])
        kill_process_by_name("llama-server.exe")
        time.sleep(1)

    try:
        # Start Hub if this is the primary server or not in bypass mode
        safe_print(f"[*] Hub Check: port={port}, config.llm_port={config.llm_port}, bypass={('--guard-bypass' in sys.argv)}")
        if "--guard-bypass" not in sys.argv or port == config.llm_port:
            start_hub()
            start_voice_stream_server()
        
        if SERVER_PROCESS and SERVER_PROCESS.poll() is None:
            logger.info("[Engine] Existing SERVER_PROCESS detected (skipping native engine launch)")
        else:
            logger.info(f"[Engine] Launching: {' '.join(cmd)}")
            try:
                SERVER_PROCESS = subprocess.Popen(
                    cmd,
                    env=os.environ,
                    cwd=str(config.BIN_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=False,
                    bufsize=-1
                )
                relay = LogRelay(SERVER_PROCESS)
                relay.start()
                register_process("LLM-Server", SERVER_PROCESS, critical=True)
            except FileNotFoundError as e:
                logger.error(f"[Engine] Native server launch failed: {e}")
                if SERVER_PROCESS and SERVER_PROCESS.poll() is None:
                    logger.info("[Engine] Continuing with dummy server already running.")
                else:
                    raise
        
        # --- UI-FIRST LAUNCH ---
        # Launch the UI immediately so the user sees something happening.
        # We pass ZENA_SKIP_PRUNE=1 to prevent the UI from killing the backend we just started.
        if "--guard-bypass" not in sys.argv and "--no-ui" not in sys.argv:
            zena_script = str(config.BASE_DIR / "zena.py")
            ui_env = os.environ.copy()
            ui_env["ZENA_SKIP_PRUNE"] = "1"
            ui_process = subprocess.Popen(
                [sys.executable, zena_script], 
                cwd=str(config.BASE_DIR), 
                env=ui_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            # Relay UI logs to main log
            ui_relay = LogRelay(ui_process, prefix="[UI]", chunk_size=1024)
            ui_relay.start()
            
            register_process("Zena-UI", ui_process, critical=False)
            safe_print("[*] UI Launched (Logs proxied to debug log)")

        # 3. Health Check Wait
        safe_print(f"[*] Waiting for LLM-Server to bind to port {port}...")
        bound = False
        for _ in range(30):
            if is_port_active(port):
                bound = True
                break
            
            p_code = SERVER_PROCESS.poll()
            if p_code is not None:
                safe_print(f"❌ LLM-Server CRASHED during startup (exit code {p_code}).")
                if relay and relay.last_lines:
                    safe_print("\n" + "🏁" * 15 + "\n  ENGINE'S LAST WORDS:")
                    for l in relay.last_lines: safe_print(f"  > {l}")
                    safe_print("🏁" * 15 + "\n")
                sys.exit(1)
            
            if _ % 5 == 0: safe_print(f"[*] Port binding poll: {_}/30...")
            time.sleep(1)
        
        if not bound:
            safe_print(f"⚠️ Port {port} still not active after 30s. Check logs.")
        else:
            safe_print(f"✅ LLM-Server online on port {port}")

        # 4. Main Monitor Loop
        while True:
            crashed = check_processes()
            for name, code, critical in crashed:
                safe_print(f"[!] {name} crashed (exit code {code})")
                if critical:
                    if relay and relay.last_lines:
                        safe_print("\n" + "🏁" * 15 + "\n  ENGINE'S LAST WORDS:")
                        for l in relay.last_lines: safe_print(f"  > {l}")
                        safe_print("🏁" * 15 + "\n")
                    safe_print(f"❌ Critical process {name} died. System shutdown initiated.")
                    sys.exit(1)
            
            if SERVER_PROCESS:
                p_code = SERVER_PROCESS.poll()
                if p_code is not None:
                    safe_print(f"[*] Main Engine poll() returned {p_code}. Stopping orchestrator.")
                    break
            else:
                break
            time.sleep(5)

    except KeyboardInterrupt:
        safe_print("[*] Keyboard interrupt received. Cleaning up...")
    except Exception as e:
        safe_print(f"❌ Error in server loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        safe_print("[*] Shutting down all managed processes...")
        if SERVER_PROCESS:
            try: ProcessManager.kill_tree(SERVER_PROCESS.pid)
            except: pass
        with EXPERT_LOCK:
            for p in EXPERT_PROCESSES.values():
                try: ProcessManager.kill_tree(p.pid)
                except: pass
        safe_print("[*] Orchestrator shutdown complete.")

if __name__ == "__main__":
    try:
        # 0. Pre-flight
        validate_environment()

        # 1. Guard & Swarm
        if "--guard-bypass" not in sys.argv: 
            # instance_guard replaced by robust port cleanup in start_server()
            pass
            
        if "--swarm" in sys.argv:
            scale_swarm(int(sys.argv[sys.argv.index("--swarm")+1]))
            while True: time.sleep(1)
        
        # 3. Start Server
        start_server()
    except Exception as e:
        safe_print(f"\n❌ FATAL STARTUP ERROR: {e}")
        import traceback
        traceback.print_exc()
        try: input("\nPress Enter to exit...")
        except: pass
        safe_exit(1)
    except KeyboardInterrupt:
        safe_exit(0)
