import os
import sys
import time
import socket
import logging
import ctypes
import subprocess
import signal
import hashlib
import zipfile
import platform
try:
    import psutil
except ImportError:
    psutil = None
from typing import Optional, NoReturn
from pathlib import Path
from config import LOG_FILE, HOST, BASE_DIR

# --- Logging Setup ---
# Determine log file based on process
proc_name = str(getattr(sys.modules.get("__main__"), "__file__", "unknown"))

if "start_llm.py" in proc_name:
    CURRENT_LOG_FILE = BASE_DIR / "nebula_engine.log"
    LOG_NAME = "ZenAIEngine"
elif "Test_Chat.py" in proc_name:
    CURRENT_LOG_FILE = BASE_DIR / "nebula_ui.log"
    LOG_NAME = "ZenAIUI"
elif "nebula_desktop.py" in proc_name:
    CURRENT_LOG_FILE = BASE_DIR / "nebula_desktop.log"
    LOG_NAME = "ZenAIDesktop"
else:
    CURRENT_LOG_FILE = LOG_FILE
    LOG_NAME = "ZenAIShared"

# Configure valid logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CURRENT_LOG_FILE, encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(LOG_NAME)

def safe_print(*args, level: str = "info", to_logger_when_debug: bool = True, **kwargs):
    """
    Thread-safe print with automatic flush=True.
    Ensures output is immediately visible in loggers and consoles.
    Handles Windows console encoding issues by falling back to ASCII-safe text.
    
    Enhanced: Forwards to logger if global/env DEBUG mode is enabled.
    """
    kwargs['flush'] = kwargs.get('flush', True)
    sep = kwargs.get('sep', ' ')
    
    # 1. Prepare text (safe string conversion)
    text = sep.join(str(a) for a in args)
    
    # 2. Print to Console (with encoding fallback)
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        # Fallback for Windows consoles that don't support UTF-8/Emojis
        safe_args = []
        for a in args:
            try:
                # Try to filter out non-encodable characters
                s = str(a).encode(sys.stdout.encoding or 'ascii', errors='replace').decode(sys.stdout.encoding or 'ascii')
                safe_args.append(s)
            except:
                safe_args.append(str(a).encode('ascii', 'ignore').decode('ascii'))
        print(sep.join(safe_args), **kwargs)

    # 3. Always Forward to Logger (Persistence)
    # This ensures that even if the console closes, we have a record in the log file.
    if to_logger_when_debug:
        level = (level or "info").lower()
        if level == "debug":
            logger.debug(text)
        elif level == "warning":
            logger.warning(text)
        elif level == "error":
            logger.error(text)
        else:
            logger.info(text)

def sha256sum(path: Path) -> str:
    """Computes SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def safe_extract(zip_path: Path, dest: Path):
    """Securely extracts a zip file, preventing path traversal (Zip Slip)."""
    with zipfile.ZipFile(zip_path, 'r') as z:
        for member in z.namelist():
            target = dest / member
            # Security check: ensure target resolves inside dest
            if not str(target.resolve()).startswith(str(dest.resolve())):
                raise RuntimeError(f"Security Alert: Zip Slip attempt detected! {member}")
        z.extractall(dest)

def trace_log(component: str, msg: str):
    """Legacy helper to maintain trace log format if needed, or just pipe to logger."""
    logger.info(f"[{component}] PID:{os.getpid()} | {msg}")

# --- Networking ---

def is_port_active(port: int, host: str = HOST) -> bool:
    """Checks if a TCP port is open/active."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0

def wait_for_port(port: int, timeout: int = 60, host: str = HOST) -> bool:
    """Waits for a port to become active."""
    start = time.time()
    while time.time() - start < timeout:
        if is_port_active(port, host):
            return True
        time.sleep(1)
    return False

# --- Process Management ---

def is_pid_alive(pid: int) -> bool:
    """Checks if a process ID is actually running (cross-platform)."""
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        # Fallback for Windows without psutil
        if sys.platform == "win32":
            try:
                process = ctypes.windll.kernel32.OpenProcess(1, False, pid)
                if process:
                    ctypes.windll.kernel32.CloseHandle(process)
                    return True
                return False
            except Exception:
                return False
        else:
            # Unix fallback
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False


# --- Hardware Profiling ---
class HardwareProfiler:
    @staticmethod
    def get_profile() -> dict:
        """
        Cross-platform hardware detection.
        Prefers psutil, falls back to platform-specific commands.
        """
        cpu_name = platform.processor()
        ram_gb = 8.0
        vram_mb = 0
        best_gpu = "CPU"
        threads = os.cpu_count() or 4
        
        # Try psutil for RAM
        try:
            import psutil
            ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
        except ImportError:
            # Fallback for Windows
            if sys.platform == "win32":
                try:
                    cmd = "powershell -NoProfile -Command \"(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory\""
                    # Stability: Add timeout to prevent hang if WMI/PowerShell is broken
                    raw = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL, timeout=2).strip()
                    if raw.isdigit(): ram_gb = round(int(raw) / (1024**3), 1)
                except: pass

        # GPU Detection (Best-effort)
        try:
            if sys.platform == "win32":
                cmd = "powershell -NoProfile -Command \"Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json\""
                # Stability: Add timeout
                out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL, timeout=2).strip()
                if out:
                    import json
                    gpus = json.loads(out)
                    if not isinstance(gpus, list): gpus = [gpus]
                    for g in gpus:
                        name = g.get("Name", "").upper()
                        v_raw = g.get("AdapterRAM", 0)
                        v_mb = round(int(v_raw) / (1024**2), 0) if v_raw else 0
                        
                        # Heuristic ranking
                        if "NVIDIA" in name: 
                            best_gpu = "NVIDIA"; vram_mb = max(vram_mb, v_mb)
                        elif "AMD" in name and best_gpu != "NVIDIA": 
                            best_gpu = "AMD"; vram_mb = max(vram_mb, v_mb)
                        elif "INTEL" in name and best_gpu not in ["NVIDIA", "AMD"]: 
                            best_gpu = "INTEL"; vram_mb = max(vram_mb, v_mb)
        except: pass
        
        logger.info(f"[Profiler] CPU: {cpu_name} | RAM: {ram_gb}GB | GPU: {best_gpu} ({vram_mb}MB)")
        return {"type": best_gpu, "cpu": cpu_name, "ram_gb": ram_gb, "vram_mb": vram_mb, "threads": threads}

def ensure_package(import_name: str, install_name: str = None):
    """Ensures a package is installed, installing it via pip if missing."""
    if not install_name:
        install_name = import_name
    try:
        __import__(import_name)
    except ImportError:
        logger.info(f"[!] Installing missing dependency: {install_name}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", install_name], 
                                stdout=subprocess.DEVNULL)
            logger.info(f"[+] Installed {install_name}")
        except Exception as e:
            logger.error(f"[!] Failed to install {install_name}: {e}")
            sys.exit(1)

def kill_process_tree(pid: int):
    """Safely kills a process and its children using psutil."""
    try:
        if not psutil.pid_exists(pid): return
        
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        for child in children:
            try: child.terminate()
            except: pass
        
        _, alive = psutil.wait_procs(children, timeout=3)
        for p in alive:
            try: p.kill() 
            except (psutil.NoSuchProcess, psutil.AccessDenied): pass
            
        parent.terminate()
        parent.wait(3)
    except Exception as e:
        logger.error(f"Failed to kill tree {pid}: {e}")
        # Fallback for extreme cases
        try: os.kill(pid, signal.SIGTERM)
        except OSError: pass

def kill_process_by_name(image_name: str):
    """Safely kills processes by image name using psutil."""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and proc.info['name'].lower() == image_name.lower():
                try:
                    proc.terminate()
                    # We don't wait here to avoid blocking large iterations, 
                    # but real implementations might want to collect and wait.
                except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    except ImportError:
        # Fallback only if psutil is somehow missing (bootstrap edge case)
        subprocess.run(["taskkill", "/F", "/IM", image_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logger.error(f"Failed to kill {image_name}: {e}")

def restart_program():
    """Restarts the current python program."""
    try:
        python = sys.executable
        os.execl(python, python, *sys.argv)
    except Exception as e:
        logger.error(f"Failed to restart program: {e}")
        # Fallback: simple exit, assuming an external watcher (like Docker or systemd) might restart it
        # But for local dev scripts, we really want to try to re-launch.
        sys.exit(1)

def kill_process_by_port(port: int):
    """Kills any process listening on the specified port."""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == port:
                        logger.info(f"[Cleanup] Killing PID {proc.pid} ({proc.info['name']}) on Port {port}")
                        proc.terminate()
                        try: proc.wait(timeout=3)
                        except: proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"Failed to kill process on port {port}: {e}")

def kill_zombie_process(port: int, allowed_names: list[str] = None):
    """
    Smart Kill: Terminates a process on 'port' ONLY if its name is in 'allowed_names'.
    If allowed_names is None or empty, it behaves like a standard kill (use with caution).
    Returns True if a process was killed, False otherwise.
    """
    killed = False
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == port:
                        proc_name = proc.info['name'].lower()
                        should_kill = False
                        
                        if not allowed_names:
                            should_kill = True # Legacy behavior (Unsafe)
                        else:
                            # Check against allowed list (case-insensitive)
                            if any(name.lower() in proc_name for name in allowed_names):
                                should_kill = True
                        
                        if should_kill:
                            logger.info(f"[SmartKill] Terminating {proc_name} (PID {proc.pid}) on Port {port}")
                            proc.terminate()
                            try: proc.wait(timeout=3)
                            except: proc.kill()
                            killed = True
                        else:
                            logger.warning(f"[SmartKill] Skipped unrelated process on port {port}: {proc_name} (PID {proc.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"Failed to execute Smart Kill on port {port}: {e}")
    return killed

def format_message_with_attachment(user_query: str, filename: str, content: str) -> str:
    """
    Formats a user message to include attached file content.
    Detects code files and applies markdown formatting.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    # Check for binary indicator
    if "[Binary file:" in content or "[Binary Content]" in content:
        return f"[Attached: {filename}] {user_query}"
        
    context_block = ""
    # Smart Detection: Code Analysis vs Context
    code_extensions = ['.py', '.js', '.html', '.css', '.json', '.cpp', '.c', '.java', '.go', '.rs', '.ts', '.sh', '.bat']
    
    if ext in code_extensions:
        lang = ext[1:]
        if lang == 'py': lang = 'python'
        if lang == 'rs': lang = 'rust'
        if lang == 'sh': lang = 'bash'
        
        # Directive Prompt for Code
        context_block = (
            f"I have attached a code file '{filename}'. Please analyze and review its logic:\\n\\n"
            f"```{lang}\\n{content}\\n```"
        )
    else:
        # Standard Context
        context_block = (
            f"I have attached a file '{filename}' for context:\\n\\n"
            f"[Start of File]\\n{content}\\n[End of File]"
        )
        
    return f"{context_block}\\n\\n{user_query}"

def sanitize_prompt(text: str) -> str:
    """
    Sanitizes user input to prevent prompt injection or format manipulation.
    Removes common LLM control tokens.
    """
    if not text:
        return ""
    
    # Remove control tokens
    forbidden = ["<|im_start|>", "<|im_end|>", "<|system|>", "<|user|>", "<|assistant|>", "[INST]", "[/INST]"]
    for token in forbidden:
        text = text.replace(token, "")
    
    return text.strip()

def normalize_input(value: str, input_type: str = 'url') -> str:
    """
    Smart input normalization/correction helper.
    types: 'url', 'path', 'repo', 'filename'
    """
    if not value:
        return ""
    
    # Common cleanup
    value = value.strip().strip('"').strip("'")
    
    if input_type == 'url':
        # Auto-add https if missing (unless file:// or localhost)
        if value and not value.startswith(('http://', 'https://', 'file://')):
            if 'localhost' in value or '127.0.0.1' in value:
                return f"http://{value}"
            # Heuristic: looks like a domainor incomplete url
            return f"https://{value}"
            
    elif input_type == 'path':
        # Fix slashes for OS
        value = value.replace('/', os.sep).replace('\\', os.sep)
        
    elif input_type == 'filename':
        # Ensure extension if obvious missing (heuristic)
        if not value.endswith('.gguf') and 'gguf' not in value.lower():
            # Don't force it, but maybe warn? 
            pass

    return value
