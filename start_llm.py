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
from datetime import datetime

# --- Core Imports (Required) ---
from config import BASE_DIR, MODEL_DIR, BIN_DIR, PORTS, HOST, DEFAULTS
from utils import logger, trace_log, kill_process_by_name, kill_process_by_port, HardwareProfiler, ensure_package

# --- Optional Imports (Lazy-loaded for performance) ---
# These are imported on-demand to avoid loading heavy dependencies when not needed:
# - model_manager: HuggingFace models (only for download/search features)
# - voice_service: Whisper/TTS models (only for voice features)
# - websockets: Only for voice streaming server

try:
    import websockets
except ImportError:
    websockets = None
    logger.warning("websockets not available - voice streaming disabled")

# Suppress HuggingFace/Windows symlink warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Ensure dependencies (psutil)
ensure_package("psutil")

def validate_environment():
    """
    Pre-flight validation: Check binaries, models, and dependencies.
    Provides clear error messages and remediation steps.
    """
    safe_print("\n" + "="*60)
    safe_print("PRE-FLIGHT VALIDATION")
    safe_print("="*60)

    issues = []
    warnings = []

    # 1. Check Binary Existence
    safe_print(f"[1/4] Checking binary at: {SERVER_EXE}")
    if not SERVER_EXE.exists():
        issues.append(("Binary Not Found", f"llama-server.exe not found at:\n       {SERVER_EXE}\n\n       Fix: Run 'python download_deps.py' to download binaries"))
    else:
        safe_print(f"      [OK] Binary found: {SERVER_EXE.name} ({SERVER_EXE.stat().st_size // (1024*1024)} MB)")

    # 2. Check Model Availability
    safe_print(f"[2/4] Checking models in: {MODEL_DIR}")
    if not MODEL_DIR.exists():
        issues.append(("Model Directory Missing", f"Model directory not found:\n       {MODEL_DIR}\n\n       Fix: Create directory and download a model"))
    else:
        gguf_models = list(MODEL_DIR.glob("*.gguf"))
        if not gguf_models:
            warnings.append(("No Models Found", f"No .gguf models in {MODEL_DIR}\n       App will start in MANAGER MODE (Hub only)\n       Use the UI to download a model"))
        else:
            safe_print(f"      [OK] Found {len(gguf_models)} model(s):")
            for model in gguf_models[:3]:  # Show first 3
                size_mb = model.stat().st_size // (1024*1024)
                safe_print(f"         - {model.name} ({size_mb} MB)")
            if len(gguf_models) > 3:
                safe_print(f"         ... and {len(gguf_models) - 3} more")

    # 3. Check Required Python Packages
    safe_print("[3/4] Checking Python dependencies...")
    required_packages = [
        ("nicegui", "NiceGUI (UI framework)"),
        ("httpx", "HTTP client"),
        ("faiss", "FAISS (vector search)"),
    ]

    missing_packages = []
    for package_name, description in required_packages:
        try:
            __import__(package_name)
            safe_print(f"      [OK] {description}")
        except ImportError:
            missing_packages.append((package_name, description))

    if missing_packages:
        pkg_list = ", ".join([pkg[0] for pkg in missing_packages])
        issues.append(("Missing Python Packages", f"Required packages not installed:\n       {pkg_list}\n\n       Fix: Run 'pip install -r requirements.txt'"))

    # 4. Check Optional Dependencies (non-blocking)
    safe_print("[4/4] Checking optional features...")
    optional_packages = [
        ("torch", "Voice STT (Whisper)"),
        ("pyttsx3", "Voice TTS"),
        ("PyPDF2", "PDF support"),
    ]

    for package_name, description in optional_packages:
        try:
            __import__(package_name)
            safe_print(f"      [OK] {description}")
        except ImportError:
            safe_print(f"      [SKIP] {description} - not available")

    safe_print("="*60)

    # Display Issues
    if issues:
        safe_print("\n[X] CRITICAL ISSUES DETECTED:\n")
        for idx, (title, message) in enumerate(issues, 1):
            safe_print(f"{idx}. {title}:")
            safe_print(f"   {message}\n")
        safe_print("="*60)

        # Check if we can offer automatic setup
        has_binary_issue = any("Binary Not Found" in issue[0] for issue in issues)
        has_package_issue = any("Missing Python Packages" in issue[0] for issue in issues)

        if has_binary_issue or has_package_issue:
            safe_print("\n[*] AUTOMATIC SETUP AVAILABLE")
            safe_print("="*60)
            safe_print("\nWould you like to run automatic setup?")
            safe_print("This will:")
            if has_binary_issue:
                safe_print("  - Detect your CPU/GPU")
                safe_print("  - Download optimal llama.cpp binaries")
            if has_package_issue:
                safe_print("  - Install missing Python packages")
            safe_print("\nOptions:")
            safe_print("  Y - Run automatic setup (recommended)")
            safe_print("  N - Exit and fix manually")
            safe_print("  M - Show manual commands")

            try:
                choice = input("\nYour choice [Y/n/m]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = 'n'
                safe_print()

            if choice in ['', 'y', 'yes']:
                # Run automatic setup
                safe_print("\n[*] Starting automatic setup...\n")
                try:
                    from setup_manager import SetupManager
                    manager = SetupManager(BASE_DIR)
                    success = manager.run_full_setup(auto_install=True, force_binaries=False)

                    if success:
                        safe_print("\n[*] Setup completed successfully!")
                        safe_print("[*] Please restart the application: python start_llm.py")
                        safe_exit(0)
                    else:
                        safe_print("\n[!] Setup encountered errors. Please check messages above.")
                        safe_exit(1)
                except ImportError:
                    safe_print("\n[!] setup_manager.py not found!")
                    safe_print("[!] Please run: python setup_manager.py --auto-install")
                    safe_exit(1)
                except Exception as e:
                    safe_print(f"\n[!] Setup failed: {e}")
                    import traceback
                    traceback.print_exc()
                    safe_exit(1)

            elif choice in ['m', 'manual']:
                safe_print("\n" + "="*60)
                safe_print("MANUAL SETUP COMMANDS")
                safe_print("="*60)
                safe_print("\n1. Download binaries:")
                safe_print("   python setup_manager.py --binaries-only")
                safe_print("\n2. Install dependencies:")
                safe_print("   python setup_manager.py --deps-only --auto-install")
                safe_print("\n3. Full automated setup:")
                safe_print("   python setup_manager.py --auto-install")
                safe_print("\n" + "="*60 + "\n")
                safe_exit(1)
            else:
                safe_print("\n[!] Please fix the issues above and try again.\n")
                safe_exit(1)
        else:
            safe_print("\n[!] Cannot start application due to critical issues.")
            safe_print("[!] Please fix the issues above and try again.\n")
            safe_exit(1)

    # Display Warnings (non-blocking)
    if warnings:
        safe_print("\n[!] WARNINGS:\n")
        for idx, (title, message) in enumerate(warnings, 1):
            safe_print(f"{idx}. {title}:")
            safe_print(f"   {message}\n")
        safe_print("="*60)
        safe_print("\n[*] Continuing with warnings...\n")
    else:
        safe_print("\n[OK] ALL CHECKS PASSED - Environment ready!\n")
        safe_print("="*60 + "\n")

    return True

def instance_guard():
    """Prevent multiple instances of start_llm.py from running."""
    import psutil
    current_pid = os.getpid()
    current_process = psutil.Process(current_pid)
    script_name = "start_llm.py"

    safe_print(f"[DEBUG] Instance guard: Current PID = {current_pid}")

    # Get the absolute path of the current script
    try:
        current_cmdline = current_process.cmdline()
        safe_print(f"[DEBUG] Current cmdline: {current_cmdline}")
        current_script_path = None
        for arg in current_cmdline:
            if script_name in arg:
                current_script_path = str(Path(arg).resolve())
                break
        safe_print(f"[DEBUG] Current script path: {current_script_path}")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        current_script_path = None

    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid']):
        try:
            # Skip the current process
            if proc.info['pid'] == current_pid:
                continue

            # Skip child processes of current process (like llama-server)
            if proc.info.get('ppid') == current_pid:
                continue

            # Only check Python processes (ignore timeout.exe, bash.exe, etc.)
            proc_name = proc.info.get('name', '').lower()
            if 'python' not in proc_name:
                continue

            cmdline = proc.info.get('cmdline') or []

            # Check if this process is running start_llm.py
            for arg in cmdline:
                if script_name in str(arg):
                    safe_print(f"[DEBUG] Found potential instance: PID={proc.info['pid']}, PPID={proc.info.get('ppid')}, cmdline={cmdline}")

                    # If we can determine paths, compare them
                    if current_script_path:
                        try:
                            other_script_path = str(Path(arg).resolve())
                            safe_print(f"[DEBUG] Comparing paths: '{other_script_path}' vs '{current_script_path}'")

                            # Only complain if it's the SAME script file
                            if other_script_path == current_script_path:
                                safe_print(f"\n[!] Another instance of {script_name} is already running:")
                                safe_print(f"    PID: {proc.info['pid']}")
                                safe_print(f"    Command: {' '.join(cmdline)}")
                                safe_print(f"\n[*] To kill the old instance, run: taskkill /PID {proc.info['pid']} /F")
                                safe_print(f"[*] Or use --guard-bypass to skip this check\n")
                                safe_exit(1)
                        except (OSError, ValueError) as e:
                            safe_print(f"[DEBUG] Path resolution failed: {e}")
                            # Can't resolve path, skip this check (might be a different script with same name)
                            continue
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    safe_print(f"[DEBUG] Instance guard passed: No other instances detected")

"""
start_llm.py - Nebula Management API (Ver 3.2 - Refactored)
Orchestrates model lifecycle and hot-swapping.
"""

# Global log file for this session (initialized once)
_LOG_FILE = None
_LOG_LOCK = threading.Lock()

def safe_print(*args, **kwargs):
    """
    Thread-safe print that immediately flushes output and writes to log file.

    In multithreaded contexts, print() buffers output which can cause:
    - Silent crashes (output lost when process terminates)
    - Out-of-order messages (race conditions in buffer)
    - Missing error messages before sys.exit()

    This function ensures immediate output visibility for debugging and
    writes all output to a timestamped log file for post-crash analysis.

    Log file format: YYYY-MM-DD_HH-MM-SS.log (one per session)
    """
    global _LOG_FILE

    kwargs['flush'] = True  # Force immediate flush

    # Print to console
    print(*args, **kwargs)

    # Write to timestamped log file for post-crash analysis
    try:
        # Initialize log file once per session (thread-safe)
        if _LOG_FILE is None:
            with _LOG_LOCK:
                if _LOG_FILE is None:
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    _LOG_FILE = Path(f"{timestamp}.log")

        # Format the message (convert args to string)
        message = " ".join(str(arg) for arg in args)

        # Append to log file with timestamp prefix (thread-safe)
        with _LOG_LOCK:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                log_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{log_timestamp}] {message}\n")
                f.flush()  # Ensure immediate write
    except Exception:
        # Silently ignore logging errors to avoid breaking the application
        pass

def safe_exit(code: int = 0, delay: float = 0.5):
    """
    Safely exit the application, ensuring all output is flushed first.

    In multithreaded contexts, safe_print() buffers output and sys.exit() can
    terminate before the buffer is flushed, causing "silent" crashes.

    Args:
        code: Exit code (0=success, non-zero=error)
        delay: Seconds to wait before exit (default 0.5s to ensure flush)
    """
    sys.stdout.flush()
    sys.stderr.flush()
    time.sleep(delay)  # Give buffers time to flush in multithreaded context
    sys.exit(code)

# Alias needed for backwards compat if referenced dynamically,
# but ideally we use config.MODEL_DIR now.
MODEL_PATH: Path = MODEL_DIR / "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
SERVER_EXE: Path = BIN_DIR / "llama-server.exe"
SERVER_PROCESS = None
EXPERT_PROCESSES = {}  # {port: subprocess.Popen}
EXPERT_LOCK = threading.Lock()
MODEL_PATH_LOCK = threading.Lock()  # Protect MODEL_PATH from race conditions

# ============================================================================
# PROCESS MONITORING (Track ALL spawned processes)
# ============================================================================
MONITORED_PROCESSES = {}  # {name: {"process": subprocess.Popen, "critical": bool, "restarts": int}}
PROCESS_LOCK = threading.Lock()

def register_process(name: str, process: subprocess.Popen, critical: bool = False):
    """Register a process for monitoring."""
    with PROCESS_LOCK:
        MONITORED_PROCESSES[name] = {
            "process": process,
            "critical": critical,
            "restarts": 0,
            "max_restarts": 3 if critical else 1
        }
        logger.info(f"[Monitor] Registered process: {name} (PID: {process.pid}, Critical: {critical})")

def check_processes():
    """Check all monitored processes and report crashes."""
    crashed = []
    with PROCESS_LOCK:
        for name, info in list(MONITORED_PROCESSES.items()):
            proc = info["process"]
            exit_code = proc.poll()  # Non-blocking check
            if exit_code is not None:
                # Process has exited
                if exit_code != 0:
                    crashed.append((name, exit_code, info["critical"]))
                    logger.error(f"[Monitor] Process '{name}' crashed with exit code {exit_code}")
                else:
                    logger.info(f"[Monitor] Process '{name}' exited normally")
                # Remove from monitoring
                del MONITORED_PROCESSES[name]
    return crashed

# ============================================================================
# LAZY-LOADED OPTIONAL MODULES (Performance Optimization)
# ============================================================================
# These modules have heavy dependencies (HuggingFace, PyTorch, Whisper, etc.)
# and are only needed for specific features. Lazy-loading them:
# 1. Reduces startup time (don't load 500MB+ of ML models if not needed)
# 2. Allows running without optional dependencies (e.g., --hub-only mode)
# 3. Caches on first use to avoid repeated imports in hot paths
# ============================================================================

_model_manager_cache = None
_voice_service_cache = None

def get_model_manager():
    """
    Lazy-load model_manager module (HuggingFace model download/search).
    Only imports when needed to avoid loading heavy dependencies.
    Thread-safe via GIL (import is atomic in CPython).
    """
    global _model_manager_cache
    if _model_manager_cache is None:
        try:
            import model_manager as mm
            _model_manager_cache = mm
        except ImportError as e:
            logger.error(f"model_manager not available: {e}")
            raise ImportError("model_manager module not found. Run: pip install huggingface_hub")
    return _model_manager_cache

def get_cached_voice_service():
    """
    Lazy-load voice_service (Whisper ASR + TTS).
    Only imports when voice features are used to avoid loading Whisper models at startup.
    Thread-safe via GIL.
    """
    global _voice_service_cache
    if _voice_service_cache is None:
        try:
            from voice_service import get_voice_service
            _voice_service_cache = get_voice_service(BASE_DIR / "voice_models")
        except ImportError as e:
            logger.error(f"voice_service not available: {e}")
            raise ImportError("voice_service module not found. Install whisper dependencies.")
    return _voice_service_cache

class NebulaOrchestrator(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def read_json_post(self) -> dict:
        """Safely read and parse JSON POST body with Content-Length."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                raise ValueError("Empty request body")
            post_data = self.rfile.read(content_length)
            return json.loads(post_data)
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Invalid JSON body: {e}")
            raise ValueError(f"Invalid JSON body: {e}")

    def send_json_response(self, status_code: int, data: dict):
        """Helper to standardize JSON responses with proper Content-Length."""
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
            # Send error response if headers not yet sent
            if not hasattr(self, '_headers_sent'):
                try:
                    err_body = json.dumps({"error": "Internal server error"}).encode()
                    self.send_response(500)
                    self.send_header('Content-Length', str(len(err_body)))
                    self.end_headers()
                    self.wfile.write(err_body)
                except Exception:
                    pass  # Connection already broken

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
            with MODEL_PATH_LOCK:
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
                with MODEL_PATH_LOCK:
                    model_exists = MODEL_PATH.exists()
                if not model_exists:
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
                except Exception as write_err:
                    logger.error(f"Failed to send error response: {write_err}")
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
            try:
                params = self.read_json_post()
                model_name = params.get('model')
                logger.info(f"[HUB] Swap requested: {model_name}")
            except ValueError as e:
                self.send_json_response(400, {"error": str(e)})
                return
            
            # Initiate restart in a separate thread so we can reply to UI
            threading.Thread(target=restart_with_model, args=(model_name,)).start()
            
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b"Accepted")
        elif self.path == '/models/download':
            try:
                params = self.read_json_post()
                # Support both new (repo_id) and legacy (repo) keys
                repo_id = params.get('repo_id') or params.get('repo')
                filename = params.get('filename') or params.get('file')

                logger.info(f"[HUB] Download requested: {repo_id}/{filename}")
            except ValueError as e:
                self.send_json_response(400, {"error": str(e)})
                return
            
            def safe_download_task(r_id, f_name):
                try:
                    mm = get_model_manager()
                    mm.download_model(r_id, f_name)
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
            try:
                params = self.read_json_post()
                query = params.get('query', '')

                mm = get_model_manager()
                results = mm.search_huggingface(query)
                # Enhance with smart parsing
                for r in results:
                    info = mm.parse_model_info(r['name'])
                    r.update(info)

                self.send_json_response(200, results)
            except ValueError as e:
                self.send_json_response(400, {"error": str(e)})
            except Exception as e:
                logger.error(f"Search Error: {e}")
                self.send_json_response(500, {"error": str(e)})
        
        elif self.path == '/swarm/scale':
            try:
                params = self.read_json_post()
                count = params.get('count', 3)

                logger.info(f"[HUB] Swarm Scale requested: {count}")
            except ValueError as e:
                self.send_json_response(400, {"error": str(e)})
                return
            
            # Run scaling in background thread
            threading.Thread(target=scale_swarm, args=(count,)).start()
            
            self.send_json_response(200, {"status": "scaling", "target": count})





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
                # Use a BytesIO wrapper for the raw data
                import io
                audio_file = io.BytesIO(audio_data)

                # Get service (lazy loads model)
                vs = get_cached_voice_service()
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
                vs = get_cached_voice_service()
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

def launch_expert_process(port: int, threads: int, model_path: Path = None):
    """Cleanly launch an expert LLM instance."""
    env = os.environ.copy()
    env["LLM_PORT"] = str(port)
    env["LLM_THREADS"] = str(threads)
    env["LLM_THREADS_BATCH"] = str(threads)
    
    script_path = os.path.abspath(__file__)
    cmd = [sys.executable, script_path, "--guard-bypass"]
    
    # Ensure we use a valid file path for the model
    if model_path and model_path.exists() and model_path.is_file():
        cmd.extend(["--model", str(model_path)])
    else:
        with MODEL_PATH_LOCK:
            if MODEL_PATH.exists() and MODEL_PATH.is_file():
                cmd.extend(["--model", str(MODEL_PATH)])
        
    logger.info(f"[SWARM] Launching Expert on Port {port}: {' '.join(cmd)}")
    
    # Capture logs to file for each expert
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = open(log_dir / f"expert_{port}.log", "w")
    
    p = subprocess.Popen(
        cmd, 
        env=env, 
        stdout=log_file, 
        stderr=log_file,
        cwd=os.path.dirname(script_path),
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )
    return p

def scale_swarm(target_count: int):
    """Dynamically adjust the number of running experts."""
    global EXPERT_PROCESSES
    try:
        safe_print(f"[DEBUG] scale_swarm({target_count}) starting...")
        with EXPERT_LOCK:
            current_ports = sorted(EXPERT_PROCESSES.keys())
            current_count = len(current_ports)
            safe_print(f"[DEBUG] Current ports: {current_ports} (Count: {current_count})")
            
            if target_count == current_count:
                safe_print("[DEBUG] Target count matches current count. No action.")
                return
                
            if target_count > current_count:
                # Launch more
                needed = target_count - current_count
                logger.info(f"[SWARM] Scaling UP: Adding {needed} experts...")
                
                # Determine starting port
                base_port = env_int("LLM_PORT", 8001)
                
                # Find next available port in our sequence
                potential_ports = []
                for i in range(1, 10): # Max 10 agents for now
                    p = 8001 + 3 + i
                    if p not in current_ports:
                        potential_ports.append(p)
                
                safe_print(f"[DEBUG] Potential ports: {potential_ports}")
                
                for i in range(min(needed, len(potential_ports))):
                    new_port = potential_ports[i]
                    p = launch_expert_process(new_port, 2)
                    EXPERT_PROCESSES[new_port] = p
                    safe_print(f"[DEBUG] Launched expert on port {new_port}")
                    
            elif target_count < current_count:
                # Terminate some
                to_remove = current_count - target_count
                logger.info(f"[SWARM] Scaling DOWN: Removing {to_remove} experts...")
                
                # Remove from highest ports down
                ports_to_kill = current_ports[-to_remove:]
                for port in ports_to_kill:
                    proc = EXPERT_PROCESSES.pop(port)
                    logger.info(f"[SWARM] Terminating expert on Port {port}...")
                    try:
                        kill_process_tree(proc.pid)
                    except:
                        pass
                    safe_print(f"[DEBUG] Terminated expert on port {port}")
    except Exception as e:
        import traceback
        safe_print(f"[ERROR] scale_swarm failed: {e}")
        traceback.print_exc()

def kill_process_tree(pid):
    """Kill a process and all its children."""
    try:
        import psutil
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except:
        # Fallback to taskkill if psutil fails/missing
        if os.name == 'nt':
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        else:
            os.kill(pid, 9)

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
        logger.info(f"[WS] Client connected: {websocket.remote_address}")
        self.clients.add(websocket)

        # Create a new processor for this session
        try:
            vs = get_cached_voice_service()
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
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.debug(f"[WS] Ignoring invalid control message: {e}")
        
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
        safe_print("[!] 'websockets' library missing. Streaming voice disabled.")
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
    """
    Read integer from environment variable with fallback to default.

    Supports negative numbers and validates the value is a valid integer.
    """
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
    ctx: int = 8192,
    gpu_layers: int = 0,
    batch: int = 512,
    ubatch: int = 512,
    model_path: Path = None,
    timeout: int = -1,
    threads_batch: int = None,
) -> list:
    """
    Build llama-server.exe command arguments (PURE FUNCTION - testable).

    This function is extracted to eliminate duplicate command-building logic
    and make it easy to test without spawning actual processes.

    Args:
        port: Port number for server
        threads: Number of threads for inference
        ctx: Context size (default 8192)
        gpu_layers: Number of GPU layers (0 = CPU only)
        batch: Batch size
        ubatch: Micro-batch size
        model_path: Path to .gguf model file
        timeout: Server timeout in seconds (-1 = no timeout)
        threads_batch: Threads for batch processing (defaults to threads)

    Returns:
        List of command arguments ready for subprocess.Popen()

    Example:
        >>> cmd = build_llama_cmd(port=8001, threads=4)
        >>> subprocess.Popen(cmd, ...)
    """
    if model_path is None:
        model_path = MODEL_PATH

    if threads_batch is None:
        threads_batch = threads

    return [
        str(SERVER_EXE),
        "--model", str(model_path),
        "--host", "0.0.0.0",
        "--port", str(port),
        "--ctx-size", str(ctx),
        "--n-gpu-layers", str(gpu_layers),
        "--threads", str(threads),
        "--threads-batch", str(threads_batch),
        "--batch-size", str(batch),
        "--ubatch-size", str(ubatch),
        "--flash-attn", "auto",
        "--repeat-penalty", "1.1",
        "--repeat-last-n", "1024",
        "--min-p", "0.1",
        "--alias", "local-model",
        "--no-warmup",
        "--timeout", str(timeout),
        "-np", "4",  # Number of parallel slots (was --parallel which didn't work)
        "--cont-batching"
    ]

def self_heal():
    logger.warning("[!] Missing components detected (binaries or models).")
    logger.warning("[!] Please run 'python Create_Local_LLM.py' to repair the environment.")
    safe_exit(1)

def start_hub():
    """Start the Management API (Hub) in a background thread"""
    try:
        hub = None
        mgmt_port = PORTS["MGMT_API"]
        for _ in range(3):
            try:
                hub = ThreadingHTTPServer(('127.0.0.1', mgmt_port), NebulaOrchestrator)
                break
            except Exception as port_err:
                logger.debug(f"Hub port bind attempt failed: {port_err}")
                time.sleep(1)

        if not hub:
            logger.error("Could not bind Hub API to Port 8002 after 3 attempts")
            safe_print("[!] Could not bind Hub API to Port 8002. Port in use.")
            safe_print("[*] Try: taskkill /F /IM python.exe (Windows) or kill existing process")
            # Non-fatal for LLM, but fatal for UI control.
            # We continue so at least the engine runs.
            return

        threading.Thread(target=hub.serve_forever, daemon=True).start()
        safe_print("[*] Nebula Hub API listening on Port 8002")
    except Exception as e:
        logger.error(f"Hub startup failed: {e}", exc_info=True)
        safe_print(f"[!] Hub Startup Failed: {e}")
        safe_print("[*] Continuing without Hub (model will run but no UI control)")

def start_server() -> NoReturn:
    global MODEL_PATH
    # Critical Check: Binaries
    if not SERVER_EXE.exists():
        logger.error(f"[!] Server binary not found at {SERVER_EXE}")
        logger.error("    Please run: python download_deps.py")
        safe_exit(1)

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
                 safe_print("\n[!] MISSING DEPENDENCY: Visual C++ Redistributable (MSVCP140.dll)")
                 safe_print("    Download: https://aka.ms/vs/17/release/vc_redist.x64.exe\n")
                 input("Press Enter to exit...") # Keep window open
                 safe_exit(1)

    # Partial Check: Models
    # Smart Detection: If default model missing, try to find ANY .gguf model
    if not MODEL_PATH.exists():
        candidates = list(MODEL_DIR.glob("*.gguf"))
        if candidates:
            # Sort by size (descending) as a heuristic for "main" model, or just pick first
            # Picking the largest file is usually safer than a tiny draft model
            candidates.sort(key=lambda x: x.stat().st_size, reverse=True)
            with MODEL_PATH_LOCK:
                MODEL_PATH = candidates[0]
            safe_print(f"\n[*] Auto-detected available model: {MODEL_PATH.name}")
        else:
            # TRULY missing -> Manager Mode
            safe_print(f"\n[!] Default model not found: {MODEL_PATH.name}")
            safe_print(f"[!] No models found in: {MODEL_DIR}")
            safe_print("[*] Starting in MANAGER MODE (Hub Only)")
            safe_print("    Please open the Web UI to download a model.")
            
            start_hub()
            safe_print("    Hub Active on http://127.0.0.1:8002")
            
            # specific loop to keep main thread alive while Hub runs
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                safe_print("Exiting...")
                return
    
    # If we get here, model exists -> Full Launch

    # HARDCODED SAFE DEFAULTS (Prevent Startup Hangs)
    profile = {'cpu': 'Generic', 'ram_gb': 16, 'type': 'CPU'}
    safe_print("[*] Universal Launcher: Starting...")
    safe_print(f"[*] Config used: MODEL_DIR={MODEL_DIR}") 
    safe_print(f"[*] Target Model: {MODEL_PATH}")

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
        except (ValueError, IndexError) as e:
            logger.debug(f"Invalid --ctx argument, using default: {e}")
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
        safe_print("[!] NITRO MODE FORCED.")

    # Build command using extracted pure function (testable, no duplication)
    cmd = build_llama_cmd(
        port=port,
        threads=threads,
        ctx=ctx,
        gpu_layers=gpu_layers,
        batch=batch,
        ubatch=ubatch,
        model_path=MODEL_PATH,
        timeout=-1,
        threads_batch=threads_batch
    )

    try:
        # Start background services ONLY in Master Mode
        if "--guard-bypass" not in sys.argv:
            start_hub()
            start_voice_stream_server()

        safe_print(f"\n[*] Launching optimized llama.cpp (v0.5.4-REV3)", flush=True)
        safe_print(f"    Layers: {gpu_layers} | Threads: {threads} | Ubatch: {ubatch} | Port: {port}", flush=True)
        
        # --- PATH Injection Fix ---
        current_path = os.environ.get("PATH", "")
        if str(BIN_DIR) not in current_path:
             os.environ["PATH"] = str(BIN_DIR) + os.pathsep + current_path

        safe_print(f"[DEBUG] About to spawn server process...", flush=True)
        global SERVER_PROCESS
        SERVER_PROCESS = subprocess.Popen(cmd, env=os.environ, cwd=BIN_DIR) # Run inside BIN_DIR for safety
        safe_print(f"[*] Engine Active (PID: {SERVER_PROCESS.pid})", flush=True)
        logger.info(f"Server process spawned: PID {SERVER_PROCESS.pid}")

        # Register the main server as CRITICAL process
        safe_print(f"[DEBUG] Registering process for monitoring...", flush=True)
        register_process("LLM-Server", SERVER_PROCESS, critical=True)
        safe_print(f"[DEBUG] Process registered successfully", flush=True)
        
        # --- UI Launch (Master Only) ---
        if "--guard-bypass" not in sys.argv:
            safe_print("[*] Launching Nebula UI...")
            safe_print("[*] Launching Zena AI (NiceGUI)...")
            subprocess.Popen(f'start cmd /k "cd /d "{BASE_DIR}" && {sys.executable} zena.py"', shell=True)
            
            # --- BENCHMARK (Master Only) ---
            safe_print("\n[*] Waiting for engine readiness & running benchmark...")
            try:
                import benchmark
                stats = benchmark.measure_tps(api_url=f"http://127.0.0.1:{port}")
                
                safe_print("\n" + "="*60)
                safe_print("       ✨ WELCOME TO NEBULA LOCAL AI ✨")
                safe_print("="*60)
                if stats["success"]:
                    safe_print(f"  Model:      {MODEL_PATH.name}")
                    safe_print(f"  Speed:      {stats['tps']:.2f} tokens/sec")
                    safe_print(f"  Rating:     {stats['rating']}")
                safe_print("="*60 + "\n")
            except Exception as e:
                safe_print(f"[!] Startup benchmark skipped or failed: {e}")

        # Wait for server process and monitor ALL processes
        safe_print(f"[*] All services running. Press Ctrl+C to stop.", flush=True)
        safe_print(f"[*] Monitoring {len(MONITORED_PROCESSES)} process(es)...", flush=True)
        safe_print(f"[DEBUG] Entering monitoring loop...", flush=True)
        logger.info("Entering main monitoring loop")

        # Auto-restart loop: monitors ALL processes
        restart_count = 0
        max_restarts = 3
        last_check = time.time()

        while True:
            try:
                # Check all monitored processes every 5 seconds
                if time.time() - last_check > 5:
                    crashed = check_processes()
                    for name, exit_code, is_critical in crashed:
                        safe_print(f"\n[!] WARNING: Process '{name}' crashed (exit code: {exit_code})")
                        if is_critical:
                            safe_print(f"[!] Critical process crashed! System may be unstable.")
                        logger.error(f"Process crash detected: {name} (exit code {exit_code})")
                    last_check = time.time()

                # Wait for main server to exit (with timeout for responsiveness)
                try:
                    exit_code = SERVER_PROCESS.wait(timeout=5)
                    logger.warning(f"[!] Main server process exited with code {exit_code}")

                    if exit_code == 0:
                        # Normal exit - don't restart
                        safe_print("[*] Server shut down normally")
                        break

                    # Abnormal exit - attempt restart
                    restart_count += 1
                    if restart_count > max_restarts:
                        safe_print(f"\n{'='*60}")
                        safe_print(f"CRITICAL: Server crashed {max_restarts} times")
                        safe_print(f"{'='*60}")
                        safe_print(f"Last exit code: {exit_code}")
                        safe_print(f"\nPossible causes:")
                        safe_print(f"  1. Insufficient RAM (need ~6GB free)")
                        safe_print(f"  2. Corrupted model file")
                        safe_print(f"  3. Incompatible CPU (AVX/AVX2 required)")
                        safe_print(f"  4. Port {port} conflict")
                        safe_print(f"  5. Missing system libraries")
                        safe_print(f"\nCheck logs for details: logs/")
                        safe_print(f"{'='*60}")
                        safe_exit(exit_code)

                    safe_print(f"\n[!] CRASH DETECTED: Server exited with code {exit_code}")
                    safe_print(f"[*] Auto-restarting... (attempt {restart_count}/{max_restarts})")
                    time.sleep(3)

                    # Restart the server
                    SERVER_PROCESS = subprocess.Popen(cmd, env=os.environ, cwd=BIN_DIR)
                    safe_print(f"[*] Server restarted (PID: {SERVER_PROCESS.pid})")
                    register_process("LLM-Server", SERVER_PROCESS, critical=True)

                except subprocess.TimeoutExpired:
                    # Server still running - continue monitoring
                    continue

            except KeyboardInterrupt:
                # Let outer handler catch this
                raise

    except KeyboardInterrupt:
        logger.info("[!] Interrupt received. Shutting down engine...")
        if SERVER_PROCESS:
            try:
                kill_process_tree(SERVER_PROCESS.pid)
            except Exception as e:
                logger.error(f"Error killing process tree: {e}")
        safe_exit(0)
    except Exception as e:
        import traceback
        logger.error(f"[!] Critical Launch Failure: {e}")
        traceback.print_exc()
        safe_print(f"\n[!] CRASH DETECTED: {e}")
        safe_print("[!] Possible causes:")
        safe_print("    - Missing VC++ Redistributable")
        safe_print("    - Incompatible CPU (AVX/AVX2 required)")
        safe_print("    - Port conflict (8001, 8002, 8003 already in use)")
        safe_print("    - Corrupted model file")
        safe_print("    - Insufficient RAM")

        if SERVER_PROCESS:
            try:
                exit_code = SERVER_PROCESS.poll()
                if exit_code is not None:
                    safe_print(f"    - Server process exited with code: {exit_code}")
            except:
                pass

        input("\nPress Enter to exit...")
        safe_exit(1)

def emergency_handler(signum, frame):
    """Emergency handler for fatal signals."""
    import traceback
    logger.critical(f"!!! FATAL SIGNAL {signum} RECEIVED !!!")
    safe_print(f"\n{'='*60}")
    safe_print(f"!!! FATAL SIGNAL {signum} - FORCED SHUTDOWN !!!")
    safe_print(f"{'='*60}")
    safe_print(f"This usually indicates:")
    safe_print(f"  - Out of memory (system killed process)")
    safe_print(f"  - Access violation / segmentation fault")
    safe_print(f"  - External process termination")
    safe_print(f"\nStack trace:")
    traceback.print_stack(frame)
    safe_print(f"{'='*60}")
    safe_exit(128 + signum)

if __name__ == "__main__":
    # Install signal handlers for fatal errors
    import signal
    signal.signal(signal.SIGTERM, emergency_handler)
    signal.signal(signal.SIGABRT, emergency_handler)
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, emergency_handler)

    # Log startup to catch silent crashes
    logger.info("="*60)
    logger.info("START_LLM.PY STARTING")
    logger.info(f"Process ID: {os.getpid()}")
    logger.info(f"Arguments: {' '.join(sys.argv)}")
    logger.info(f"Python: {sys.version}")
    logger.info("="*60)
    safe_print(f"\n{'='*60}")
    safe_print(f" NEBULA LLM SERVER - VERSION: 2.1-DEBUG-VERIFIED")
    safe_print(f" (Fixing: Slots -> Parallel, Added: Verbose Logging)")
    safe_print(f"{'='*60}\n")
    safe_print(f"[DEBUG] start_llm.py starting (PID: {os.getpid()})")
    safe_print(f"[DEBUG] Working directory: {os.getcwd()}")

    try:
        # Run pre-flight validation (unless bypassed)
        if "--skip-validation" not in sys.argv:
            try:
                validate_environment()
            except Exception as e:
                logger.error(f"Validation failed: {e}")
                safe_print(f"[!] Pre-flight validation failed: {e}")
                safe_print("[*] Continuing anyway (use --skip-validation to suppress)")

        if "--hub-only" in sys.argv:
            try:
                safe_print("[*] Starting in HUB ONLY mode (No Engine)...")
                # Ensure dependencies for Hub
                try:
                    get_model_manager()
                except ImportError:
                    safe_print("[!] Warning: model_manager not found")

                start_hub()
                safe_print("    Hub Active on http://127.0.0.1:8002")
                safe_print("    Press Ctrl+C to exit")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    safe_print("\n[*] Hub shutting down...")
                    safe_exit(0)
            except Exception as e:
                logger.error(f"Hub mode failed: {e}", exc_info=True)
                safe_print(f"[!] Hub mode crashed: {e}")
                input("Press Enter to exit...")
                safe_exit(1)

        # --- SWARM MODE (v2.0) ---
        if "--swarm" in sys.argv:
            try:
                idx = sys.argv.index("--swarm")
                try:
                    swarm_count = int(sys.argv[idx+1])
                except:
                    swarm_count = 3 # Default to 3 experts

                safe_print(f"\n[SWARM] Launching EXPERT SWARM ({swarm_count} instances)...")

                # Start Hub once
                start_hub()

                base_port = env_int("LLM_PORT", 8001)
                instances = []

                # Calculate threads per instance
                try:
                    import psutil
                    total_cores = psutil.cpu_count(logical=False) or 4
                except:
                    total_cores = os.cpu_count() or 4

                if swarm_count > 0:
                    threads_per = max(1, total_cores // swarm_count)
                    safe_print(f"[SWARM] Thread Allocation: {threads_per} threads per instance")
                else:
                    threads_per = 2 # Default for dynamic scale
                    safe_print("[SWARM] Starting with 0 experts (Manager Mode)")

                for i in range(swarm_count):
                    port = base_port + i
                    if i > 0: # 8001 is standard, others are expert ports
                        port = 8001 + 3 + i # Skip 8002 (Hub), 8003 (Voice) -> 8005, 8006...

                    safe_print(f"[SWARM] Spawning Expert {i+1} on Port {port}...")
                    p = launch_expert_process(port, threads_per)
                    with EXPERT_LOCK:
                        EXPERT_PROCESSES[port] = p
                    instances.append(p)
                    time.sleep(4) # Stagger boot to reduce IO spike

                # --- AUTO-TUNE (v2.5) ---
                if "--auto-swarm" in sys.argv:
                    safe_print("\n[SWARM] ENTERING AUTO-TUNE MODE...")
                    safe_print("[SWARM] Waiting for experts to initialize (45s) before benchmarking...")
                    time.sleep(45) # Give experts even more time to boot

                    try:
                        from zena_mode.arbitrage import SwarmArbitrator
                        from zena_mode.tuner import run_auto_tune

                        # Discover what we just launched
                        arb = SwarmArbitrator()
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        optimal_n = loop.run_until_complete(run_auto_tune(arb))
                        safe_print(f"\n[SWARM] AUTO-TUNE SUCCESS: Optimal Swarm Size is {optimal_n}")
                        safe_print("[SWARM] Please restart WITHOUT --auto-swarm to use optimized settings.")
                    except Exception as e:
                        safe_print(f"[SWARM] AUTO-TUNE FAILED: {e}")

                    safe_print("[SWARM] Shutting down benchmark instances...")
                    for p in instances:
                        p.terminate()
                    safe_exit(0)

                safe_print(f"\n[SWARM] Expert Swarm online. Listening on ports {base_port} and up.")
                safe_print("[SWARM] Chain of Thought (CoT) Arbitrage ready.")

                try:
                    while True:
                        # Monitor health?
                        time.sleep(5)
                        # Check if UI is running, if not maybe exit?
                except KeyboardInterrupt:
                    safe_print("[SWARM] Shutting down experts...")
                    for p in instances:
                        p.terminate()
                    safe_exit(0)
            except Exception as e:
                logger.error(f"Swarm mode failed: {e}", exc_info=True)
                safe_print(f"[!] Swarm mode crashed: {e}")
                for p in instances:
                    try:
                        p.terminate()
                    except:
                        pass
                input("Press Enter to exit...")
                safe_exit(1)

        if "--model" in sys.argv:
            idx = sys.argv.index("--model")
            passed_model = sys.argv[idx+1]
            # Allow absolute path or relative to MODEL_DIR
            potential_path = Path(passed_model)
            if potential_path.is_absolute() and potential_path.exists():
                with MODEL_PATH_LOCK:
                    MODEL_PATH = potential_path
                safe_print(f"[*] Dynamic Model Override (Absolute): {MODEL_PATH.name}")
            elif (MODEL_DIR / passed_model).exists():
                with MODEL_PATH_LOCK:
                    MODEL_PATH = MODEL_DIR / passed_model
                safe_print(f"[*] Dynamic Model Override (Relative): {MODEL_PATH.name}")
            else:
                safe_print(f"[!] Warning: override model {passed_model} not found.")

        if "--guard-bypass" not in sys.argv:
            instance_guard()
        start_server()

    except KeyboardInterrupt:
        logger.info("\n[*] Shutdown requested by user")
        safe_print("\n[*] Shutting down gracefully...")
        safe_exit(0)
    except Exception as e:
        import traceback
        logger.error(f"FATAL ERROR in main: {e}", exc_info=True)
        safe_print("\n" + "="*70)
        safe_print("FATAL ERROR - APPLICATION CRASHED")
        safe_print("="*70)
        safe_print(f"Error: {e}")
        safe_print("\nFull traceback:")
        traceback.print_exc()
        safe_print("\n" + "="*70)
        safe_print("Possible causes:")
        safe_print("  1. Missing dependencies (run: pip install -r requirements.txt)")
        safe_print("  2. Port conflict (8001, 8002, 8003 already in use)")
        safe_print("  3. Corrupted model file")
        safe_print("  4. Insufficient permissions")
        safe_print("  5. Missing VC++ Redistributable (Windows)")
        safe_print("="*70)
        input("\nPress Enter to exit...")
        safe_exit(1)
