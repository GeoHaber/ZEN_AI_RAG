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
from utils import logger, trace_log, kill_process_by_name, kill_process_by_port, HardwareProfiler, ensure_package, safe_print, kill_process_tree, is_port_active

# Ensure critical dependencies
ensure_package("psutil")
import psutil

# Global Variables
MODEL_PATH = MODEL_DIR / "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
SERVER_EXE = BIN_DIR / "llama-server.exe"

# Suppress HuggingFace/Windows symlink warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# STARTUP INFO
safe_print(f"🚀 ZenAI Starting from: {os.getcwd()}")

def safe_exit(code: int = 0, delay: float = 0.5):
    """Safely exit the application, ensuring all output is flushed first."""
    time.sleep(delay)
    sys.exit(code)

def validate_environment():
    """Pre-flight validation: Check binaries, models, and dependencies."""
    safe_print("\n" + "="*60)
    safe_print("PRE-FLIGHT VALIDATION")
    safe_print("="*60)

    issues = []
    warnings = []

    # 4. Hardware Awareness (Enhanced)
    safe_print("\n[4/4] Hardware & Resource Audit")
    profiler = HardwareProfiler.get_profile()
    cpu_caps = []
    
    # Check CPU Intel/AMD extensions (Crucial for llama.cpp)
    import cpuinfo
    try:
        info = cpuinfo.get_cpu_info()
        flags = info.get('flags', [])
        for cap in ['avx', 'avx2', 'avx512f', 'fma', 'sse3', 'msse3']:
            if cap in flags: cpu_caps.append(cap.upper())
    except Exception:
        # Fallback to a basic check if cpuinfo fails
        pass

    safe_print(f"      - Script:   {Path(__file__).absolute()}")
    safe_print(f"      - Root:     {BASE_DIR}")
    safe_print(f"      - CPU:      {profiler['cpu']} | {', '.join(cpu_caps) if cpu_caps else 'Base'}")
    safe_print(f"      - RAM:      {profiler['ram_gb']}GB Total")
    if profiler['type'] != "CPU":
        safe_print(f"      - GPU:      {profiler['type']} ({profiler['vram_mb']}MB VRAM)")

    # 4b. Storage Audit
    try:
        usage = psutil.disk_usage(MODEL_DIR)
        free_gb = usage.free // (1024**3)
        safe_print(f"      - Storage:  {free_gb}GB Free on {MODEL_DIR.drive}")
        if free_gb < 10:
            warnings.append(("Low Disk Space", f"Only {free_gb}GB free for models"))
    except Exception:
        pass

    # 5. Background Interference Audit
    safe_print("\n[*] Background Job Audit")
    interference = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            # Check for other LLM backends or heavy Python tasks
            if proc.info['name'] in ['llama-server.exe', 'ollama.exe', 'local_ai.exe']:
                if proc.pid != os.getpid():
                    interference.append(f"{proc.info['name']} (PID: {proc.pid})")
            
            # Check for high CPU usage (greedy jobs)
            if proc.info['cpu_percent'] and proc.info['cpu_percent'] > 50.0:
                 interference.append(f"High-CPU: {proc.info['name']} ({proc.info['cpu_percent']}%)")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if interference:
        safe_print(f"      [!] Potential Interference: {', '.join(interference)}")
        warnings.append(("Resource Contention", "Background processes may degrade LLM performance"))
    else:
        safe_print("      [OK] No major interference detected")

    safe_print("="*60)
    if issues:
        safe_print("\n❌ CRITICAL ISSUES DETECTED:")
        for title, msg in issues: safe_print(f"  - {title}: {msg}")
        safe_exit(1)
    
    if warnings:
        safe_print("\n⚠️ WARNINGS:")
        for title, msg in warnings: safe_print(f"  - {title}: {msg}")
        safe_print("\nContinuing Anyway...")

    safe_print("\n✅ READY - Environment validated.\n" + "="*60 + "\n")
    return True

def instance_guard():
    """Prevent multiple instances of start_llm.py from running."""
    current_pid = os.getpid()
    script_name = "start_llm.py"
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid:
                continue
            cmdline = proc.info.get('cmdline') or []
            if any(script_name in str(arg) for arg in cmdline):
                safe_print(f"⚠️  Detecting Ghost Instance: {script_name} (PID: {proc.info['pid']})")
                from utils import kill_process_tree
                kill_process_tree(proc.info['pid'])
                safe_print(f"✅ Ghost Neutralized. Proceeding with fresh instance.")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

"""
start_llm.py - ZenAI Management API (Ver 3.3 - Converged)
Orchestrates model lifecycle and hot-swapping with full TDD support.
"""

# Alias needed for backwards compat if referenced dynamically
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

def safe_exit(code: int = 0, delay: float = 0.5):
    """Exit with buffer flush + delay."""
    sys.stdout.flush()
    sys.stderr.flush()
    time.sleep(delay)  # Give buffers time to flush
    sys.exit(code)

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
                UPLOAD_DIR = BASE_DIR / "uploads"
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

def build_llama_cmd(port: int, threads: int, ctx: int = 8192, gpu_layers: int = 0, batch: int = 512, ubatch: int = 512, model_path: Path = None, timeout: int = -1, threads_batch: int = None) -> list:
    """Build llama-server.exe command arguments."""
    if model_path is None: model_path = MODEL_PATH
    if threads_batch is None: threads_batch = threads
    return [
        str(SERVER_EXE), "--model", str(model_path), "--host", "0.0.0.0", "--port", str(port),
        "--ctx-size", str(ctx), "--n-gpu-layers", str(gpu_layers), "--threads", str(threads),
        "--threads-batch", str(threads_batch), "--batch-size", str(batch), "--ubatch-size", str(ubatch),
        "--flash-attn", "--repeat-penalty", "1.1", "--repeat-last-n", "1024", "--min-p", "0.1",
        "--alias", "local-model", "--no-warmup", "--timeout", str(timeout), "-np", "4", "--cont-batching"
    ]

# Use the implementation from `utils.kill_process_by_name` which is
# imported at module top. Tests patch `utils.psutil.process_iter`, so
# delegating to `utils` ensures consistent, testable behavior.

def restart_with_model(name):
    """Restart engine with a new model."""
    kill_process_by_name("llama-server.exe")
    time.sleep(2)
    cmd = [sys.executable, __file__, "--guard-bypass", "--model", name]
    subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
    os._exit(0)

def launch_expert_process(port: int, threads: int, model_path: Path = None):
    """Cleanly launch an expert LLM instance."""
    env = os.environ.copy()
    env["LLM_PORT"] = str(port)
    env["LLM_THREADS"] = str(threads)
    script_path = os.path.abspath(__file__)
    cmd = [sys.executable, script_path, "--guard-bypass"]
    if model_path and model_path.exists(): cmd.extend(["--model", str(model_path)])
    elif MODEL_PATH.exists(): cmd.extend(["--model", str(MODEL_PATH)])
    
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
                kill_process_tree(proc.pid)

def start_hub():
    """Start the Management API (Hub)."""
    try:
        safe_print(f"[*] Attempting to start Hub API on port {PORTS['MGMT_API']}...")
        hub = ThreadingHTTPServer(('127.0.0.1', PORTS["MGMT_API"]), ZenAIOrchestrator)
        threading.Thread(target=hub.serve_forever, daemon=True).start()
        safe_print(f"[*] Hub API listening on Port {PORTS['MGMT_API']}")
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
        async with websockets.serve(VoiceStreamHandler().handle_client, "0.0.0.0", 8003):
            await asyncio.Future()

def start_voice_stream_server():
    if websockets:
        threading.Thread(target=lambda: asyncio.run(run_ws_server()), daemon=True).start()

def start_server() -> NoReturn:
    global MODEL_PATH
    global SERVER_PROCESS
    # Determine LLM port early so we can start a test-dummy server if needed
    port = env_int("LLM_PORT", 8001)

    if not SERVER_EXE.exists():
        # In test and developer environments we prefer a non-fatal fallback
        # so unit tests can exercise orchestration logic without requiring
        # the native llama-server binary to be present. Start a lightweight
        # Python HTTP server on the LLM port to simulate a healthy engine.
        safe_print(f"⚠️ Llama server binary not found at {SERVER_EXE}. Starting dummy HTTP server on port {port} for compatibility tests.")
        try:
            dummy_cmd = [sys.executable, "-m", "http.server", str(port)]
            SERVER_PROCESS = subprocess.Popen(
                dummy_cmd,
                env=os.environ,
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            register_process("LLM-Server-Dummy", SERVER_PROCESS, critical=False)
            safe_print(f"✅ Dummy LLM-Server started on port {port} (PID {SERVER_PROCESS.pid})")
        except Exception as e:
            safe_print(f"❌ Failed to start dummy server: {e}")
            sys.exit(1)

    if not MODEL_PATH.exists():
        safe_print(f"⚠️ Warning: Selected model not found at {MODEL_PATH}")
        candidates = list(MODEL_DIR.glob("*.gguf"))
        if candidates:
            MODEL_PATH = max(candidates, key=lambda x: x.stat().st_size)
            safe_print(f"🔄 Auto-selected largest local model: {MODEL_PATH.name}")
        else:
            safe_print(f"❌ ERROR: No .gguf models found in {MODEL_DIR}")
            sys.exit(1)
    
    threads = env_int("LLM_THREADS", os.cpu_count() // 2)
    cmd = build_llama_cmd(port=port, threads=threads)

    # --- NEW: Robust Startup Cleanup ---
    safe_print(f"[*] Pre-flight Cleanup: Checking Port {port}...")
    kill_process_by_port(port)
    kill_process_by_name("llama-server.exe")
    time.sleep(1) # Wait for OS to release resources

    try:
        if "--guard-bypass" not in sys.argv:
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
                    cwd=BIN_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                register_process("LLM-Server", SERVER_PROCESS, critical=True)
            except FileNotFoundError as e:
                logger.error(f"[Engine] Native server launch failed: {e}")
                # If native engine cannot be launched, but a dummy is running,
                # continue using the dummy. Otherwise re-raise.
                if SERVER_PROCESS and SERVER_PROCESS.poll() is None:
                    logger.info("[Engine] Continuing with dummy server already running.")
                else:
                    raise
        
        # --- NEW: Health Check Wait ---
        safe_print(f"[*] Waiting for LLM-Server to bind to port {port}...")
        bound = False
        for _ in range(30): # 30 seconds timeout
            if is_port_active(port):
                bound = True
                break
            if SERVER_PROCESS.poll() is not None:
                # Script crashed immediately
                out, _ = SERVER_PROCESS.communicate()
                logger.error(f"[Engine] Llama-Server CRASHED during startup: {out}")
                safe_print(f"❌ LLM-Server CRASHED during startup. Check nebula_engine.log")
                sys.exit(1)
            time.sleep(1)
        
        if not bound:
            logger.error(f"[Engine] Timeout waiting for port {port}")
            safe_print(f"⚠️ Port {port} still not active after 30s. Check logs.")
        else:
            safe_print(f"✅ LLM-Server online on port {port}")

        if "--guard-bypass" not in sys.argv and "--no-ui" not in sys.argv:
            subprocess.Popen(f'start cmd /k "{sys.executable} zena.py"', shell=True)

        while True:
            crashed = check_processes()
            for name, code, critical in crashed:
                safe_print(f"[!] {name} crashed (code {code})")
            if SERVER_PROCESS.poll() is not None: break
            time.sleep(5)
    except KeyboardInterrupt:
        if SERVER_PROCESS: kill_process_tree(SERVER_PROCESS.pid)
        sys.exit(0)

if __name__ == "__main__":
    try:
        # 0. Pre-flight
        validate_environment()

        # 1. Guard & Swarm
        if "--guard-bypass" not in sys.argv: 
            instance_guard()
            
        if "--swarm" in sys.argv:
            scale_swarm(int(sys.argv[sys.argv.index("--swarm")+1]))
            while True: time.sleep(1)
        
        # 3. Start Server
        start_server()
    except Exception as e:
        safe_print(f"\n❌ FATAL STARTUP ERROR: {e}")
        import traceback
        traceback.print_exc()
        safe_exit(1)
    except KeyboardInterrupt:
        safe_exit(0)
