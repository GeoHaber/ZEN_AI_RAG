# -*- coding: utf-8 -*-
"""
utils.py - ZenAI Unified Utility System
=======================================
Consolidated utilities for process management, hardware profiling, and diagnostics.
Strictly follows zena_master_spec.md v3.1.
"""

import os
import sys
import time
import socket
import logging
import subprocess
import signal
import hashlib
from pathlib import Path
from typing import List, Dict

try:
    import psutil
except ImportError:
    psutil = None

from config_system import EMOJI, config

# --- Global Logic ---
BASE_DIR = config.BASE_DIR

# --- Logging Setup ---
proc_name = str(getattr(sys.modules.get("__main__"), "__file__", "unknown"))
if "start_llm.py" in proc_name:
    LOG_NAME = "ZenAIEngine"
elif "zena.py" in proc_name:
    LOG_NAME = "ZenAIUI"
else:
    LOG_NAME = "ZenAIShared"

logger = logging.getLogger(LOG_NAME)


def safe_print(*args, level: str = "info", **kwargs):
    """Thread-safe and encoding-safe print with automatic flush.

    Handles:
    - UnicodeEncodeError: strips non-ASCII chars on encoding failures
    - OSError: silently skips print when no console is attached (Windows Explorer launch)
    """
    kwargs["flush"] = kwargs.get("flush", True)
    sep = kwargs.get("sep", " ")
    text = sep.join(str(a) for a in args)

    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        # Fallback: strip non-ASCII characters
        safe_args = [str(a).encode("ascii", "ignore").decode("ascii") for a in args]
        try:
            print(sep.join(safe_args), **kwargs)
        except OSError:
            pass  # No console attached, skip output
    except OSError:
        # No console attached (Windows "Open with Python" scenario)
        pass

    try:
        sys.stdout.flush()
    except (OSError, AttributeError):
        pass  # stdout may be None or invalid

    # Forward to logger (always works, writes to file)
    lvl = level.lower()
    if lvl == "debug":
        logger.debug(text)
    elif lvl == "warning":
        logger.warning(text)
    elif lvl == "error":
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


# --- Networking ---
def is_port_active(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a TCP port is open/active."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0


def wait_for_port(port: int, timeout: int = 60, host: str = "127.0.0.1") -> bool:
    """Waits for a port to become active."""
    start = time.time()
    while time.time() - start < timeout:
        if is_port_active(port, host):
            return True
        time.sleep(1)
    return False


# --- Process Management ---
class ProcessManager:
    """Unified handler for process lifecycle and 'Zombie' pruning."""

    @staticmethod
    def get_zombies(ports: List[int] = None, scripts: List[str] = None) -> Dict[int, Dict]:
        """Identifies hanging processes by port or script name."""
        zombies = {}
        if not psutil:
            return zombies

        target_ports = ports or [
            config.llm_port,
            config.mgmt_port,
            config.ui_port,
            config.voice_port,
        ]
        target_scripts = scripts or ["zena.py", "start_llm.py", "llama-server.exe"]

        # Get current process and parent (to avoid killing launcher like py.exe)
        current_pid = os.getpid()
        try:
            parent_pid = psutil.Process(current_pid).ppid()
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            parent_pid = None

        # 1. Port-based detection
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.laddr.port in target_ports and conn.status == "LISTEN":
                    try:
                        p = psutil.Process(conn.pid)
                        # Skip self and parent (py.exe launcher)
                        if conn.pid in (current_pid, parent_pid):
                            continue
                        zombies[conn.pid] = {
                            "type": "Port Conflict",
                            "port": conn.laddr.port,
                            "name": p.name(),
                            "cmd": " ".join(p.cmdline()[:3]),
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        except (psutil.AccessDenied, OSError):
            pass  # Connection iteration failed

        # 2. Script-based detection
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                pid = p.info["pid"]
                # Skip self, parent, and already-detected
                if pid in (current_pid, parent_pid) or pid in zombies:
                    continue
                cmd = p.info["cmdline"] or []
                cmd_str = " ".join(cmd).lower()
                for target in target_scripts:
                    if target.lower() in cmd_str:
                        zombies[pid] = {
                            "type": "Hanging Instance",
                            "port": "N/A",
                            "name": p.info["name"],
                            "cmd": cmd_str[:100],
                        }
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return zombies

    @staticmethod
    def kill_tree(pid: int):
        """Safely terminates a process and all its children."""
        try:
            if not psutil or not psutil.pid_exists(pid):
                return
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            parent.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            pass

    @staticmethod
    def prune(
        auto_confirm: bool = False,
        ports: List[int] = None,
        scripts: List[str] = None,
        **kwargs,
    ) -> bool:
        """Detect and kill zombies for a clean startup."""
        # Map allowed_names to scripts for backward compatibility
        if "allowed_names" in kwargs:
            scripts = kwargs["allowed_names"]

        zombies = ProcessManager.get_zombies(ports=ports, scripts=scripts)
        if not zombies:
            return True

        safe_print(f"\n{EMOJI['warning']} ZOMBIE PROCESSES DETECTED")
        for pid, info in zombies.items():
            safe_print(f"  - [{info['type']}] {info['name']} (PID: {pid}, Port: {info['port']})")

        if not auto_confirm:
            ans = input("\nKill these processes to allow a clean startup? (y/n): ").lower()
            if ans != "y":
                return False

        for pid in zombies:
            try:
                if psutil:
                    p = psutil.Process(pid)
                    p.kill()
                else:
                    os.kill(pid, signal.SIGTERM)
                safe_print(f"  {EMOJI['success']} Terminated PID {pid}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                pass
        time.sleep(1)
        return True


# --- Hardware Profiling ---
class HardwareProfiler:
    @staticmethod
    def get_profile() -> dict:
        """Cross-platform hardware detection."""
        profile = {
            "type": "CPU",
            "ram_gb": 8.0,
            "vram_mb": 0,
            "threads": os.cpu_count() or 4,
        }
        try:
            if psutil:
                profile["ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 1)

            if sys.platform == "win32":
                cmd = ["powershell", "-NoProfile", "-Command",
                       "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json"]
                out = subprocess.check_output(cmd, shell=False, text=True, stderr=subprocess.DEVNULL, timeout=3).strip()
                if out:
                    import json

                    gpus = json.loads(out)
                    if not isinstance(gpus, list):
                        gpus = [gpus]
                    for g in gpus:
                        name = g.get("Name", "").upper()
                        if "NVIDIA" in name:
                            profile["type"] = "NVIDIA"
                        elif "AMD" in name:
                            profile["type"] = "AMD"
        except (subprocess.SubprocessError, ValueError, KeyError, OSError):
            pass  # Hardware detection optional
        logger.info(f"[Profiler] Detected: {profile['type']} | {profile['ram_gb']}GB RAM | {profile['threads']} Cores")
        return profile


def ensure_package(import_name: str, install_name: str = None):
    """Guarantees a Python package is available."""
    if not install_name:
        install_name = import_name
    try:
        __import__(import_name)
    except ImportError:
        logger.info(f"[Packages] Installing {install_name}...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", install_name],
            stdout=subprocess.DEVNULL,
        )


def restart_program():
    """Restarts the current python program."""
    os.execl(sys.executable, sys.executable, *sys.argv)


class DiagnosticRunner:
    """v3.1 Smoke Test Engine."""

    @staticmethod
    async def run_smoke_test():
        results = []
        safe_print(f"\n{EMOJI['search']} Running Global System Health Check...")

        # 1. Config Check
        results.append(("Config Integrity", "OK" if hasattr(config, "BIN_DIR") else "FAIL"))

        # 2. Binary Check
        results.append(
            (
                "Engine Binary",
                "OK" if (config.BIN_DIR / "llama-server.exe").exists() else "MISSING",
            )
        )

        # 3. Port Check
        results.append(
            (
                "API Port Availability",
                "OK" if not is_port_active(config.llm_port) else "BUSY",
            )
        )

        for name, status in results:
            icon = EMOJI["success"] if status == "OK" else EMOJI["error"]
            safe_print(f"{icon} {name:<20}: {status}")

        return all(s == "OK" for _, s in results)


# Legacy shims for backwards compatibility during migration
def prune_zombies(auto_confirm=False):
    return ProcessManager.prune(auto_confirm)


def kill_process_tree(pid):
    return ProcessManager.kill_tree(pid)


def kill_process_by_name(name: str):
    """Legacy shim."""
    if not psutil:
        return
    for p in psutil.process_iter(["name"]):
        if p.info["name"] == name:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass


def kill_process_by_port(port: int):
    """Legacy shim."""
    if not psutil:
        return
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            try:
                psutil.Process(conn.pid).kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass


def trace_log(msg: str, level: str = "info"):
    """Legacy shim."""
    safe_print(f"[Trace] {msg}", level=level)


def format_message_with_attachment(user_query: str, filename: str, content: str) -> str:
    """Formats a user message to include attached file content."""
    import os

    ext = os.path.splitext(filename)[1].lower()
    if "[Binary file:" in content or "[Binary Content]" in content:
        return f"[Attached: {filename}] {user_query}"

    code_extensions = [
        ".py",
        ".js",
        ".html",
        ".css",
        ".json",
        ".cpp",
        ".c",
        ".java",
        ".go",
        ".rs",
        ".ts",
        ".sh",
        ".bat",
    ]
    if ext in code_extensions:
        lang = ext[1:]
        if lang == "py":
            lang = "python"
        context_block = f"I have attached a code file '{filename}'. Please analyze and review its logic:\\n\\n```{lang}\\n{content}\\n```"
    else:
        context_block = (
            f"I have attached a file '{filename}' for context:\\n\\n[Start of File]\\n{content}\\n[End of File]"
        )
    return f"{context_block}\\n\\n{user_query}"


def sanitize_prompt(text: str) -> str:
    """Sanitizes user input to prevent prompt injection."""
    if not text:
        return ""
    forbidden = [
        "<|im_start|>",
        "<|im_end|>",
        "<|system|>",
        "<|user|>",
        "<|assistant|>",
        "[INST]",
        "[/INST]",
    ]
    for token in forbidden:
        text = text.replace(token, "")
    return text.strip()


def normalize_input(value: str, input_type: str = "url") -> str:
    """Normalizes input (url, path, etc.)."""
    if not value:
        return ""
    value = value.strip().strip('"').strip("'")
    if input_type == "url":
        if value and not value.startswith(("http://", "https://", "file://")):
            if "localhost" in value or "127.0.0.1" in value:
                return f"http://{value}"
            return f"https://{value}"
    elif input_type == "path":
        value = value.replace("/", os.sep).replace("\\", os.sep)
    return value


def safe_extract(zip_path: Path, dest: Path):
    """Secure extraction helper."""
    import zipfile

    with zipfile.ZipFile(zip_path, "r") as z:
        for member in z.namelist():
            target = dest / member
            if not str(target.resolve()).startswith(str(dest.resolve())):
                raise RuntimeError("Security Alert: Zip Slip attempt detected!")
        z.extractall(dest)
