import os
import sys
import subprocess
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

try:
    import sounddevice as sd
    import numpy as np
    import scipy.io.wavfile as wav
except ImportError:
    sd = None
    np = None
    wav = None
# --- Shared Imports ---
from utils import (
    logger,
    ensure_package,
    safe_print,
    ProcessManager,
    is_port_active,
    kill_process_by_name,
    kill_process_by_port,
)
from config_system import config

ensure_package("psutil")

# --- Modular Handlers ---
from zena_mode.handlers import (  # noqa: E402
    BaseZenHandler,
    ModelHandler,
    VoiceHandler,
    StaticHandler,
    ChatHandler,
    HealthHandler,
    OrchestrationHandler,
)


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
        self.last_lines = []  # "Last Words" buffer
        self.buffer_lock = threading.Lock()

    def run(self):
        try:
            while not self._stop_event.is_set():
                if not self.process:
                    break

                # Binary read of 1024 bytes
                try:
                    chunk = self.process.stdout.read(1024)
                except (ValueError, AttributeError, OSError):
                    break  # Process likely dead

                if not chunk:
                    break

                try:
                    # Decode and print
                    text = chunk.decode("utf-8", errors="replace")
                    if text:
                        # Update Last Words
                        with self.buffer_lock:
                            self.last_lines.append(text.strip())
                            if len(self.last_lines) > 20:
                                self.last_lines.pop(0)

                        # Print
                        safe_print(f"{self.prefix} {text}", end="")
                except Exception as exc:
                    logger.debug("%s", exc)
        except Exception as exc:
            logger.debug("%s", exc)


# --- Swarm / Expert Management ---
EXPERT_PROCESSES = {}  # {port: subprocess.Popen}


class ZenAIOrchestrator(BaseHTTPRequestHandler):
    """
    Management API (Port 8002)
    Handles:
    - Model Swapping (Hot Swap)
    - Swarm Expert Launching
    - System Health & Telemetry
    - Voice Transcription Relay
    """

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body) if body else {}

            # Endpoint: /model/swap
            if self.path == "/model/swap":
                model_name = data.get("model")
                if not model_name:
                    self._send_json(400, {"error": "Missing model name"})
                    return

                safe_print(f"🔄 Request to swap to: {model_name}")
                global PENDING_MODEL_SWAP
                PENDING_MODEL_SWAP = model_name
                self._send_json(200, {"status": "swap_scheduled", "model": model_name})

            # Endpoint: /swarm/launch (NEW)
            elif self.path == "/swarm/launch":
                model_name = data.get("model")
                port = int(data.get("port", 8005))

                if not model_name:
                    self._send_json(400, {"error": "Missing model name"})
                    return

                target_path = config.MODEL_DIR / model_name
                if not target_path.exists():
                    # Fallback to central store
                    target_path = Path("C:/AI/Models") / model_name
                    if not target_path.exists():
                        self._send_json(404, {"error": f"Model {model_name} not found"})
                        return

                if port in EXPERT_PROCESSES and EXPERT_PROCESSES[port].poll() is None:
                    self._send_json(200, {"status": "already_running", "port": port})
                    return

                safe_print(f"🚀 Launching Expert: {model_name} on Port {port}...")

                # Build command for expert (lighter resources)
                cmd = build_llama_cmd(
                    port=port,
                    threads=4,  # Lower threads for experts
                    ctx=2048,  # Smaller context
                    batch=512,
                    ubatch=512,
                    model_path=target_path,
                )

                # Launch
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(config.BIN_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=False,
                )

                # Track
                EXPERT_PROCESSES[port] = proc
                relay = LogRelay(proc, prefix=f"[Expert-{port}]")
                relay.start()

                # Wait for bind
                active = False
                for _ in range(20):
                    if is_port_active(port):
                        active = True
                        break
                    time.sleep(1)

                if active:
                    self._send_json(200, {"status": "launched", "port": port, "pid": proc.pid})
                else:
                    self._send_json(500, {"error": "Expert process started but port unreachable"})

            # Endpoint: /voice/transcribe
            elif self.path == "/voice/transcribe":
                # Simplified relay to Whisper usage or similar if strictly needed here
                # For now just mock or log
                self._send_json(200, {"text": "[Voice transcription placeholder]"})

            else:
                self._send_json(404, {"error": "Unknown endpoint"})

        except Exception as e:
            logger.error(f"API Error: {e}")
            self._send_json(500, {"error": str(e)})

    def do_GET(self):
        if self.path == "/health":
            status = "online" if SERVER_PROCESS and SERVER_PROCESS.poll() is None else "offline"
            experts = {p: "running" if proc.poll() is None else "dead" for p, proc in EXPERT_PROCESSES.items()}
            self._send_json(200, {"status": status, "model": MODEL_PATH.name, "experts": experts})
        else:
            self._send_json(404, {"error": "Not found"})

    def _send_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


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
        safe_print("❌ Error: Engine binary seems corrupted (size too small).")
        return False

    # 2. Model File
    if not MODEL_PATH.exists():
        safe_print(f"❌ Error: Model file not found: {MODEL_PATH}")
        return False
    if MODEL_PATH.stat().st_size < 1000000:  # < 1MB is likely a placeholder
        safe_print(f"❌ Error: Model file seems corrupted or incomplete: {MODEL_PATH}")
        return False

    # 3. Port Check (Self-Correction)
    critical_ports = [config.llm_port, config.mgmt_port]
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
PENDING_MODEL_SWAP = None  # Global flag for Hot Swap


def register_process(name, process, critical=False):
    """Register a process for health monitoring."""
    with PROCESS_LOCK:
        MONITORED_PROCESSES[name] = {
            "process": process,
            "critical": critical,
            "restarts": 0,
            "max_restarts": 3 if critical else 1,
            "start_time": time.time(),
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


class ZenAIOrchestrator(BaseZenHandler):  # noqa: F811
    def do_GET(self):
        """Main GET routing entry point."""
        # Delegate to Modular Handlers (priority order)
        if HealthHandler.handle_get(self):
            return
        if ModelHandler.handle_get(self):
            return
        if VoiceHandler.handle_get(self):
            return
        if StaticHandler.handle_get(self):
            return

        # Default fallback
        self.send_json_response(200, {"status": "ZenAI Hub Active", "path": self.path})

    def do_POST(self):
        """Main POST routing entry point."""
        # Security: check request size (Phase 1 hardening)
        if not self.check_request_size():
            return

        # Delegate to Modular Handlers (priority order)
        if OrchestrationHandler.handle_post(self):
            return
        if ModelHandler.handle_post(self):
            return
        if VoiceHandler.handle_post(self):
            return
        if ChatHandler.handle_post(self):
            return

        # Default fallback
        self.send_json_response(404, {"error": "Endpoint not found"})


def env_int(name: str, default: int) -> int:
    """Read integer from environment variable with fallback to default."""
    val = os.environ.get(name, "").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def build_llama_cmd(
    port: int,
    threads: int,
    ctx: int = 4096,
    gpu_layers: int = 0,
    batch: int = 512,
    ubatch: int = 512,
    model_path: Path = None,
    timeout: int = -1,
    threads_batch: int = None,
    parallel: int = 1,
) -> list:
    """Build llama-server.exe command arguments."""
    if model_path is None:
        model_path = MODEL_PATH
    if threads_batch is None:
        threads_batch = threads
    return [
        str(SERVER_EXE),
        "--model",
        str(model_path),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--ctx-size",
        str(ctx),
        "--n-gpu-layers",
        str(gpu_layers),
        "--threads",
        str(threads),
        "--threads-batch",
        str(threads_batch),
        "--batch-size",
        str(batch),
        "--ubatch-size",
        str(ubatch),
        "--repeat-penalty",
        "1.1",
        "--repeat-last-n",
        "1024",
        "--min-p",
        "0.1",
        "--alias",
        "local-model",
        "--no-warmup",
        "--timeout",
        str(timeout),
        "-np",
        str(parallel),
    ]


# Use the implementation from `utils.kill_process_by_name` which is
# imported at module top. Tests patch `utils.psutil.process_iter`, so
# delegating to `utils` ensures consistent, testable behavior.


def restart_with_model(name):
    """Signal the main loop to perform a Hot Swap."""
    global PENDING_MODEL_SWAP, SERVER_PROCESS

    logger.info(f"[Orchestrator] Initiating Hot Swap to: {name}")
    # Set the flag
    PENDING_MODEL_SWAP = name

    # Kill the current engine to trigger the restart logic in the main loop
    if SERVER_PROCESS:
        SERVER_PROCESS.terminate()
        # The main loop will wake up, see the exit code, check the flag, and re-launch.


def launch_expert_process(port: int, threads: int, model_path: Path = None):
    """Cleanly launch an expert LLM instance."""
    env = os.environ.copy()
    env["LLM_PORT"] = str(port)
    env["LLM_THREADS"] = str(threads)

    # Fix Import Error: Add project root to PYTHONPATH
    root_dir = str(config.BASE_DIR)
    current_pp = env.get("PYTHONPATH", "")
    sep = ";" if os.name == "nt" else ":"
    env["PYTHONPATH"] = f"{root_dir}{sep}{current_pp}" if current_pp else root_dir

    script_path = os.path.abspath(__file__)
    cmd = [sys.executable, script_path, "--guard-bypass"]
    if model_path and model_path.exists():
        cmd.extend(["--model", str(model_path)])
    elif MODEL_PATH.exists():
        cmd.extend(["--model", str(MODEL_PATH)])

    # Experts run detached by default (subprocess.CREATE_NO_WINDOW)
    p = subprocess.Popen(
        cmd,
        env=env,
        cwd=root_dir,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        shell=False,
    )
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
    """Start the Management API (Hub) - uses ASGI by default."""
    use_asgi = os.environ.get("ZENAI_USE_ASGI", "1") == "1"

    if use_asgi:
        try:
            import uvicorn
            from zena_mode.asgi_server import app

            safe_print(f"[*] Starting ASGI Hub API on 127.0.0.1:{config.mgmt_port}...")

            # Run uvicorn in a background thread with its own event loop
            # This avoids conflicts with asyncio.run() in start_llm.py
            def run_uvicorn():
                import asyncio

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                uvicorn_config = uvicorn.Config(
                    app,
                    host="127.0.0.1",
                    port=config.mgmt_port,
                    log_level="warning",
                    loop="asyncio",
                )
                server = uvicorn.Server(uvicorn_config)
                loop.run_until_complete(server.serve())

            threading.Thread(target=run_uvicorn, daemon=True).start()
            safe_print(f"[*] ASGI Hub API listening on 127.0.0.1:{config.mgmt_port}")
        except Exception as e:
            safe_print(f"⚠️ ASGI startup failed, falling back to sync server: {e}")
            import traceback

            traceback.print_exc()
            _start_sync_hub()
    else:
        _start_sync_hub()


def _start_sync_hub():
    """Legacy sync HTTP server fallback."""
    try:
        safe_print(f"[*] Starting sync Hub API on port {config.mgmt_port}...")
        hub = ThreadingHTTPServer(("127.0.0.1", config.mgmt_port), ZenAIOrchestrator)
        threading.Thread(target=hub.serve_forever, daemon=True).start()
        safe_print(f"[*] Sync Hub API listening on 127.0.0.1:{config.mgmt_port}")
    except Exception as e:
        safe_print(f"❌ Hub Startup Failed: {e}")
        logger.error(f"Hub Startup Failed: {e}")


class VoiceStreamHandler:
    def __init__(self):
        self.clients = set()

    async def handle_client(self, ws):
        self.clients.add(ws)
        try:
            async for msg in ws:
                pass
        finally:
            self.clients.remove(ws)


async def run_ws_server():
    if websockets:
        try:
            async with websockets.serve(VoiceStreamHandler().handle_client, "0.0.0.0", 8003):
                safe_print("[*] Voice Stream Server listening on Port 8003")
                await asyncio.Future()
        except OSError as e:
            if e.errno == 10048:
                safe_print("⚠️ Voice Port 8003 busy. Voice features disabled for this session.")
            else:
                logger.error(f"Voice Server Error: {e}")
        except Exception as e:
            logger.error(f"Voice Server Startup Failed: {e}")


def start_voice_stream_server():
    if websockets:
        threading.Thread(target=lambda: asyncio.run(run_ws_server()), daemon=True).start()


def start_server() -> NoReturn:
    global MODEL_PATH, SERVER_PROCESS, EXPERT_PROCESSES, PENDING_MODEL_SWAP
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
        ubatch=config.ubatch_size,
    )

    # Apply GPU layers set by Orchestrator
    if "--n-gpu-layers" not in cmd and "--n_gpu_layers" not in cmd:
        cmd.extend(["--n-gpu-layers", str(gpu_layers)])

    # Removed --cache-reuse as it can cause instability with parallel slots

    # Removed --flash-attn as it can cause crashes on unsupported hardware

    # 2. Robust Startup Cleanup
    # 2. Startup Guard - Orchestrator handles pruning, but we do a safe check
    if os.environ.get("ZENA_SKIP_PRUNE") != "1":
        safe_print("[*] Engine Guard: Ensuring ports are clean...")
        ProcessManager.prune(port, allowed_names=["llama-server.exe", "python.exe"])
        kill_process_by_name("llama-server.exe")
        time.sleep(1)

    try:
        # Start Hub if this is the primary server or not in bypass mode
        safe_print(
            f"[*] Hub Check: port={port}, config.llm_port={config.llm_port}, bypass={('--guard-bypass' in sys.argv)}"
        )
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
                    bufsize=-1,
                    shell=False,
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
            # Try app.py first (current Streamlit UI), fall back to zena.py if needed
            ui_script = config.BASE_DIR / "app.py"
            if not ui_script.exists():
                ui_script = config.BASE_DIR / "zena.py"

            ui_env = os.environ.copy()
            ui_env["ZENA_SKIP_PRUNE"] = "1"
            ui_process = subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", str(ui_script)],
                cwd=str(config.BASE_DIR),
                env=ui_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
            )
            # Relay UI logs to main log
            ui_relay = LogRelay(ui_process, prefix="[UI]", chunk_size=1024)
            ui_relay.start()

            register_process("RAG-UI", ui_process, critical=False)
            safe_print(f"[*] UI Launched ({ui_script.name}) - Logs proxied to debug log")

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
                    for line in relay.last_lines:
                        safe_print(f"  > {line}")
                    safe_print("🏁" * 15 + "\n")
                sys.exit(1)

            if _ % 5 == 0:
                safe_print(f"[*] Port binding poll: {_}/30...")
            time.sleep(1)

        if not bound:
            safe_print(f"⚠️ Port {port} still not active after 30s. Check logs.")
        else:
            safe_print(f"✅ LLM-Server online on port {port}")

        # 4. Main Monitor Loop
        while True:
            crashed = check_processes()
            for name, code, critical in crashed:
                # Override for Hot Swap
                if name == "LLM-Server" and PENDING_MODEL_SWAP:
                    safe_print(f"[Monitor] LLM-Server stopped for swap (code {code}). Proceeding to restart...")
                    continue

                safe_print(f"[!] {name} crashed (exit code {code})")
                if critical:
                    if relay and relay.last_lines:
                        safe_print("\n" + "🏁" * 15 + "\n  ENGINE'S LAST WORDS:")
                        for line in relay.last_lines:
                            safe_print(f"  > {line}")
                        safe_print("🏁" * 15 + "\n")
                    safe_print(f"❌ Critical process {name} died. System shutdown initiated.")
                    sys.exit(1)

            if SERVER_PROCESS:
                p_code = SERVER_PROCESS.poll()
                if p_code is not None:
                    # CHECK FOR HOT SWAP
                    if PENDING_MODEL_SWAP:
                        safe_print(f"🔄 Hot Swap Detected! Switching to {PENDING_MODEL_SWAP}...")

                        # 1. Update Global Model Path
                        new_model_path = config.MODEL_DIR / PENDING_MODEL_SWAP
                        if not new_model_path.exists():
                            safe_print(f"❌ Swap Error: Model {PENDING_MODEL_SWAP} not found! Reverting to default.")
                            PENDING_MODEL_SWAP = None
                            # Should probably restart old model or fail
                        else:
                            MODEL_PATH = new_model_path

                        # 2. Re-launch Engine
                        cmd = build_llama_cmd(
                            port=port,
                            threads=threads,
                            ctx=config.context_size,
                            batch=config.batch_size,
                            ubatch=config.ubatch_size,
                            model_path=MODEL_PATH,  # Use updated path
                        )
                        # Add GPU layers if needed (reusing logic from above would be better, but this is patch)
                        if "--n-gpu-layers" not in cmd:
                            cmd.extend(["--n-gpu-layers", str(gpu_layers)])

                        safe_print(f"[*] Re-launching Engine: {' '.join(cmd)}")
                        try:
                            SERVER_PROCESS = subprocess.Popen(
                                cmd,
                                env=os.environ,
                                cwd=str(config.BIN_DIR),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=False,
                                bufsize=-1,
                                shell=False,
                            )
                            relay = LogRelay(SERVER_PROCESS)
                            relay.start()
                            register_process("LLM-Server", SERVER_PROCESS, critical=True)

                            # Reset Flag
                            PENDING_MODEL_SWAP = None

                            # Wait for bind (briefly)
                            safe_print(f"[*] Waiting for swap to complete (port {port})...")
                            # We let the content loop handle the waiting naturally?
                            # No, we should probably block briefly to ensure stability before next loop
                            time.sleep(2)
                            continue  # Skip the "break" that implies crash

                        except Exception as e:
                            safe_print(f"❌ Hot Swap Failed: {e}")
                            sys.exit(1)

                    safe_print(f"[*] Main Engine poll() returned {p_code}.")
                    if relay and relay.last_lines:
                        safe_print("\n" + "🏁" * 15 + "\n  ENGINE'S LAST WORDS:")
                        for line in relay.last_lines:
                            safe_print(f"  > {line}")
                        safe_print("🏁" * 15 + "\n")
                    break  # Real crash
            else:
                break

            time.sleep(2)

    except KeyboardInterrupt:
        safe_print("[*] Keyboard interrupt received. Cleaning up...")
    except Exception as e:
        safe_print(f"❌ Error in server loop: {e}")
        import traceback

        traceback.print_exc()
    finally:
        safe_print("[*] Shutting down all managed processes...")
        if SERVER_PROCESS:
            try:
                ProcessManager.kill_tree(SERVER_PROCESS.pid)
            except Exception as exc:
                logger.debug("%s", exc)
        with EXPERT_LOCK:
            for p in EXPERT_PROCESSES.values():
                try:
                    ProcessManager.kill_tree(p.pid)
                except Exception as exc:
                    logger.debug("%s", exc)
        safe_print("[*] Orchestrator shutdown complete.")


if __name__ == "__main__":
    try:
        # 0. Pre-flight
        # Handle CLI overrides
        if "--model" in sys.argv:
            try:
                m_arg_idx = sys.argv.index("--model") + 1
                if m_arg_idx < len(sys.argv):
                    custom_model = Path(sys.argv[m_arg_idx])
                    if custom_model.exists():
                        MODEL_PATH = custom_model
                        logger.info(f"[Startup] Overriding model path to: {MODEL_PATH}")
            except Exception as e:
                logger.error(f"Failed to parse --model: {e}")

        validate_environment()

        # 1. Guard & Swarm
        if "--guard-bypass" not in sys.argv:
            # instance_guard replaced by robust port cleanup in start_server()
            pass

        if "--swarm" in sys.argv:
            scale_swarm(int(sys.argv[sys.argv.index("--swarm") + 1]))
            while True:
                time.sleep(1)

        # 3. Start Server
        start_server()
    except Exception as e:
        safe_print(f"\n❌ FATAL STARTUP ERROR: {e}")
        import traceback

        traceback.print_exc()
        try:
            input("\nPress Enter to exit...")
        except Exception as exc:
            logger.debug("%s", exc)
        safe_exit(1)
    except KeyboardInterrupt:
        safe_exit(0)
