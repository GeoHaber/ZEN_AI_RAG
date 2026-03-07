"""
LlamaCppManager - Cross-platform llama.cpp detection and monitoring

Detects installed llama-server, checks version, monitors health, and provides
download information for updates.

Thread-safe with RLock for concurrent access.
"""

import logging
import os
import platform
import re
import subprocess
import shutil
import time
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Optional, Tuple

try:
    import psutil
except Exception:
    psutil = None

logger = logging.getLogger(__name__)


@dataclass
class LlamaCppStatus:
    """Status of llama.cpp installation and runtime"""
    installed: bool
    version: Optional[str] = None
    latest_version: Optional[str] = None
    needs_update: bool = False
    path: Optional[Path] = None
    running: bool = False
    port: int = 8001
    pid: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        return {
            'installed': self.installed,
            'version': self.version,
            'latest_version': self.latest_version,
            'needs_update': self.needs_update,
            'path': str(self.path) if self.path else None,
            'running': self.running,
            'port': self.port,
            'pid': self.pid,
            'error': self.error
        }


class LlamaCppManager:
    """Detect and monitor llama.cpp installation"""

    # Common installation paths by platform
    SEARCH_PATHS = {
        'Windows': [
            Path('C:\\AI\\_bin'),  # Custom AI folder (highest priority)
            Path(os.getenv('BIN_DIR', 'C:\\AI\\_bin')),  # Environment variable override
            Path('C:\\llama.cpp'),
            Path('C:\\Program Files\\llama.cpp'),
            Path('C:\\Program Files (x86)\\llama.cpp'),
            Path.home() / 'llama.cpp',
            Path.home() / 'AppData\\Local\\llama.cpp',
            Path.home() / 'Downloads\\llama.cpp',
        ],
        'Darwin': [  # macOS
            Path('/usr/local/bin'),
            Path('/opt/homebrew/bin'),
            Path.home() / 'llama.cpp',
            Path('/Applications/llama.cpp'),
        ],
        'Linux': [
            Path('/usr/local/bin'),
            Path('/usr/bin'),
            Path.home() / 'llama.cpp',
            Path.home() / '.local/bin',
        ]
    }

    EXECUTABLE_NAMES = {
        'Windows': ['llama-server.exe', 'llama.exe'],
        'Darwin': ['llama-server', 'llama-cpp-server'],
        'Linux': ['llama-server', 'llama-cpp-server']
    }

    def __init__(self):
        """Initialize manager with thread-safe lock"""
        self._lock = RLock()
        self._status_cache = None
        self._cache_timestamp = 0.0
        self._cache_ttl = 2.0  # seconds
        self._cache_valid = False
        self._last_error = None

    def _safe_run(self, args, timeout: float = 5.0, retries: int = 2, backoff: float = 0.2):
        """Run subprocess.run with retries, timeout handling, and consistent return.

        Returns a simple object with `returncode` and `stdout`, or None on fatal failure.
        """
        attempt = 0
        while attempt <= retries:
            try:
                res = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
                return res
            except FileNotFoundError:
                # executable not found - no point retrying
                self._last_error = f"Executable not found: {args[0]}"
                logging.debug(self._last_error)
                return None
            except subprocess.TimeoutExpired as e:
                logging.warning(f"Command timeout (attempt {attempt+1}/{retries+1}): {args}")
                self._last_error = str(e)
            except Exception as e:
                logging.warning(f"Subprocess failure (attempt {attempt+1}/{retries+1}): {e}")
                self._last_error = str(e)

            attempt += 1
            time.sleep(backoff * (2 ** attempt))

        return None

    def find_llama_server(self) -> Optional[Path]:
        """
        Find llama-server executable in common locations

        Returns:
            Path to executable or None if not found
        """
        system = platform.system()
        search_paths = self.SEARCH_PATHS.get(system, self.SEARCH_PATHS['Linux'])
        exe_names = self.EXECUTABLE_NAMES.get(system, self.EXECUTABLE_NAMES['Linux'])

        # Search common paths
        for search_path in search_paths:
            for exe_name in exe_names:
                exe_path = search_path / exe_name
                if exe_path.exists():
                    logger.info(f"Found llama-server at {exe_path}")
                    return exe_path

        # Use shutil.which for PATH lookup (more reliable)
        for exe_name in exe_names:
            which_path = shutil.which(exe_name)
            if which_path:
                logger.info(f"Found llama-server in PATH at {which_path}")
                return Path(which_path)

        logger.warning("llama-server not found in any known location")
        return None

    def check_installed(self) -> Tuple[bool, Optional[str], Optional[Path]]:
        """
        Check if llama.cpp is installed and get version

        Returns:
            (installed: bool, version: str or None, path: Path or None)
        """
        try:
            exe_path = self.find_llama_server()
            if not exe_path:
                return False, None, None

            # Try to get version using safe runner
            result = self._safe_run([str(exe_path), '--version'], timeout=5, retries=1)
            if result and hasattr(result, 'stdout'):
                version = result.stdout.strip()
                match = re.search(r'(\d+\.\d+\.\d+)', version)
                if match:
                    version = match.group(1)
                return True, version, exe_path

            logger.warning(f"Could not get version for {exe_path}; last_error={self._last_error}")
            return True, None, exe_path

        except Exception as e:
            logger.error(f"Error checking llama.cpp: {e}")
            return False, None, None

    def get_latest_version(self) -> Optional[str]:
        """
        Get latest llama.cpp version from GitHub API

        Returns:
            Version string or None if lookup fails
        """
        # Try urllib first (no external deps)
        url = 'https://api.github.com/repos/ggerganov/llama.cpp/releases/latest'
        try:
            req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'MARKET_AI'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                tag = data.get('tag_name', '')
                version = tag.lstrip('b')
                if version:
                    return version
        except Exception as e:
            logging.debug(f"urllib failed fetching latest version: {e}")

        # Fallback to curl via subprocess
        res = self._safe_run(['curl', '-s', url, '-H', 'Accept: application/vnd.github.v3+json'], timeout=5, retries=1)
        if res and hasattr(res, 'stdout'):
            try:
                data = json.loads(res.stdout)
                tag = data.get('tag_name', '')
                version = tag.lstrip('b')
                if version:
                    return version
            except Exception:
                pass

        return None

    @staticmethod
    def check_update_needed(current: str, latest: str) -> bool:
        """
        Check if update is needed by comparing versions

        Args:
            current: Current version string
            latest: Latest version string

        Returns:
            True if update recommended
        """
        try:
            current_parts = [int(x) for x in current.split('.')]
            latest_parts = [int(x) for x in latest.split('.')]

            # Pad with zeros if needed
            while len(current_parts) < len(latest_parts):
                current_parts.append(0)
            while len(latest_parts) < len(current_parts):
                latest_parts.append(0)

            return latest_parts > current_parts
        except Exception:
            return False

    def is_running(self) -> Tuple[bool, Optional[int]]:
        """
        Check if llama-server process is running

        Returns:
            (running: bool, pid: int or None)
        """
        system = platform.system()
        try:
            # Prefer psutil if available for cross-platform process discovery
            if psutil is not None:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        name = (proc.info.get('name') or '').lower()
                        cmd = ' '.join(proc.info.get('cmdline') or []).lower()
                        if 'llama-server' in name or 'llama-server' in cmd:
                            return True, int(proc.info.get('pid'))
                    except Exception:
                        continue

            if system == 'Windows':
                result = self._safe_run(['tasklist', '/FI', 'IMAGENAME eq llama-server.exe'], timeout=5)
                if result and 'llama-server.exe' in (result.stdout or ''):
                    lines = (result.stdout or '').strip().split('\n')
                    for line in lines:
                        if 'llama-server.exe' in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                try:
                                    pid = int(parts[1])
                                    return True, pid
                                except ValueError:
                                    pass
                    return True, None
            else:
                result = self._safe_run(['pgrep', '-f', 'llama-server'], timeout=5)
                if result and result.returncode == 0 and (result.stdout or '').strip():
                    try:
                        pid = int((result.stdout or '').strip().split()[0])
                        return True, pid
                    except (ValueError, IndexError):
                        return True, None

        except Exception as e:
            logger.debug(f"Could not check if running: {e}")

        return False, None

    def get_status(self) -> LlamaCppStatus:
        """
        Get comprehensive status of llama.cpp

        Returns:
            LlamaCppStatus dataclass with all info
        """
        with self._lock:
            try:
                # short-circuit with cache to avoid frequent subprocess calls
                now = time.time()
                if self._status_cache and (now - self._cache_timestamp) < self._cache_ttl:
                    return self._status_cache

                installed, version, path = self.check_installed()

                status = LlamaCppStatus(
                    installed=installed,
                    version=version,
                    path=path
                )

                if installed:
                    # Check for updates
                    try:
                        latest = self.get_latest_version()
                        if latest and version:
                            status.latest_version = latest
                            status.needs_update = self.check_update_needed(version, latest)
                    except Exception as e:
                        logger.debug(f"Latest version check failed: {e}")

                    # Check if running
                    try:
                        running, pid = self.is_running()
                        status.running = running
                        if pid:
                            status.pid = pid
                    except Exception as e:
                        logger.debug(f"is_running check failed: {e}")

                # cache result
                self._status_cache = status
                self._cache_timestamp = now
                return status

            except Exception as e:
                logger.error(f"Error getting status: {e}")
                return LlamaCppStatus(
                    installed=False,
                    error=str(e)
                )

    def get_download_url(self) -> str:
        """Get download URL for llama.cpp"""
        system = platform.system()
        if system == 'Windows':
            return "https://github.com/ggerganov/llama.cpp/releases"
        elif system == 'Darwin':
            return "https://github.com/ggerganov/llama.cpp/releases (or: brew install llama-cpp)"
        else:
            return "https://github.com/ggerganov/llama.cpp/releases"

    def is_ready(self) -> bool:
        """Quick check if ready to use"""
        status = self.get_status()
        return status.installed and not status.needs_update
