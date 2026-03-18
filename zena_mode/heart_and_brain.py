# -*- coding: utf-8 -*-
"""
heart_and_brain.py - The Core Logic of ZenAI
============================================
The "Heart" manages the Engine's pulse (Life, Restart, Recovery).
The "Brain" manages the Model's logic (Paths, Swarm, Experts).
"""

import sys
import time
import logging
import requests
import subprocess
from pathlib import Path
from typing import Optional, Dict

# Internal Imports
from config_system import config, EMOJI
from utils import safe_print, is_port_active, wait_for_port, ProcessManager
from zena_mode.resource_detect import HardwareProfiler

try:
    from local_llm import LocalLLMManager, LocalLLMStatus
except ImportError:
    LocalLLMManager = None  # type: ignore[assignment,misc]
    LocalLLMStatus = None  # type: ignore[assignment,misc]
    import logging as _ll_log
    _ll_log.getLogger(__name__).warning("local_llm package not found — LLM management disabled")

logger = logging.getLogger("ZenCore")

import threading


# --- Helper Classes ---
class LogRelay(threading.Thread):
    """
    Reads stdout from a subprocess in a non-blocking thread and logs it.
    Prevents pipe buffer deadlocks on Windows.
    Hardened: Uses chunk-based reading.
    """

    def __init__(self, process, prefix="[Engine]", chunk_size=1024):
        """Initialize instance."""
        super().__init__(daemon=True)
        self.process = process
        self.prefix = prefix
        self.chunk_size = chunk_size
        self._stop_event = threading.Event()
        self.last_lines = []  # "Last Words" buffer
        self.buffer_lock = threading.Lock()

    def run(self):
        """Run."""
        try:
            while not self._stop_event.is_set():
                if not self.process:
                    break
                try:
                    chunk = self.process.stdout.read(1024)
                except (ValueError, AttributeError, OSError):
                    break  # Process likely dead

                if not chunk:
                    break

                try:
                    text = chunk.decode("utf-8", errors="replace")
                    if text:
                        with self.buffer_lock:
                            self.last_lines.append(text.strip())
                            if len(self.last_lines) > 20:
                                self.last_lines.pop(0)
                        safe_print(f"{self.prefix} {text}", end="")
                except Exception:
                    pass
        except Exception:
            pass


class ZenHeart:
    """
    The Heart of the system.
    Responsibilities:
    - Pump Life: Start/Stop the LLM Engine
    - Pacemaker: Check Health & Auto-Restart
    - Blood Pressure: Manage Hardware/VRAM
    """

    def __init__(self):
        """Initialize instance."""
        self.server_process: Optional[subprocess.Popen] = None
        self.server_relay: Optional[LogRelay] = None
        self.monitored_pids: Dict[int, str] = {}
        self.restart_count = 0
        self.health_checks_failed = 0
        self.stop_event = threading.Event()

    def pump(self):
        """
        The Main Life-Support Loop.
        Monitors the engine, restarts it if it dies, and reports health.
        Should be run in the main thread (blocking).
        """
        logger.info("[Heart] Pump started. Monitoring vitals...")
        MAX_RESTARTS = 3

        while not self.stop_event.is_set():
            # 1. Check Engine Pulse
            if self.server_process:
                p_code = self.server_process.poll()

                if p_code is not None:
                    # HE'S DEAD, JIM!
                    logger.warning(f"[Heart] Engine flatlined (Exit Code: {p_code})")

                    if self.server_relay and self.server_relay.last_lines:
                        safe_print("\n" + "🏁" * 15 + "\n  ENGINE'S LAST WORDS:")
                        for l in self.server_relay.last_lines:
                            safe_print(f"  > {l}")
                        safe_print("🏁" * 15 + "\n")

                    if self.restart_count < MAX_RESTARTS:
                        self.restart_count += 1
                        safe_print(
                            f"{EMOJI['recovery']} Attempting resuscitation {self.restart_count}/{MAX_RESTARTS}..."
                        )
                        time.sleep(2)
                        try:
                            self.ignite()
                            safe_print(f"{EMOJI['success']} Resuscitation successful!")
                        except Exception as e:
                            safe_print(f"❌ Resuscitation failed: {e}")
                    else:
                        safe_print("💀 Brain death confirmed. Shutting down system.")
                        self.stop_event.set()
                        return

                # 2. Check Pacemaker (Zombie Hangs)
                elif not self.pacemaker():
                    # Process exists but is unresponsive
                    if self.health_checks_failed > 3:
                        safe_print(f"{EMOJI['warning']} Engine detected as ZOMBIE (Unresponsive). Force killing...")
                        self.flatline()  # Kill it
                        # Loop will catch "death" in next iteration and restart

            time.sleep(2)

    def pacemaker(self) -> bool:
        """Active Health Probe (HTTP Check)."""
        if not self.server_process:
            return False
        try:
            resp = requests.get(f"http://127.0.0.1:{config.llm_port}/health", timeout=2)
            if resp.status_code == 200:
                self.health_checks_failed = 0
                return True
        except Exception:
            pass

        self.health_checks_failed += 1
        return False

    def flatline(self):
        """Kill the engine (Process Death)."""
        if self.server_process:
            ProcessManager.kill_tree(self.server_process.pid)
            self.server_process = None

    @staticmethod
    def _build_engine_cmd():
        """Build the llama-server command with hardware-tuned parameters."""
        # 1. Sense Hardware
        profile = HardwareProfiler.get_profile()
        config.host = "127.0.0.1"

        # 2. Tune Hardware (VRAM Governor)
        gpu_layers = config.gpu_layers
        if profile["type"] == "NVIDIA" and config.gpu_layers == -1:
            safe_vram = max(0, profile["free_vram_mb"] - 500)
            if safe_vram < 500:
                gpu_layers = 0
            else:
                gpu_layers = min(99, int(safe_vram / 120))
            safe_print(
                f"{EMOJI['hardware']} Nvidia Governor: {profile['free_vram_mb']}MB Free -> {gpu_layers} layers safe."
            )
        elif profile["type"] == "AMD" and config.gpu_layers == -1:
            safe_vram = int(profile["vram_mb"] * 0.70)
            gpu_layers = max(0, int(safe_vram / 120))
            safe_print(f"{EMOJI['hardware']} AMD Governor: {profile['vram_mb']}MB Total -> {gpu_layers} layers (est).")

        # 3. CPU Threading
        threads = max(1, profile["threads"] - 1)

        # 4. Construct Command
        model_path = config.MODEL_DIR / config.default_model
        cmd = [
            str(config.BIN_DIR / "llama-server.exe"),
            "--model",
            str(model_path),
            "--host",
            config.host,
            "--port",
            str(config.llm_port),
            "--n-gpu-layers",
            str(gpu_layers),
            "--threads",
            str(threads),
            "--ctx-size",
            str(config.context_size),
            "--batch-size",
            str(config.batch_size),
            "--parallel",
            str(getattr(config, "parallel", 1)),
            "--log-disable",
        ]

        logger.info(f"Igniting Engine: {' '.join(cmd)}")
        return cmd

    def ignite(self):
        """Start the llama-server engine with optimal hardware settings."""
        cmd = self._build_engine_cmd()

        # Guard: Clean port
        if is_port_active(config.llm_port):
            ProcessManager.prune(ports=[config.llm_port], auto_confirm=True)

        # Launch
        try:
            creation_flags = (
                subprocess.CREATE_NEW_CONSOLE | subprocess.HIGH_PRIORITY_CLASS if sys.platform == "win32" else 0
            )

            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                creationflags=creation_flags,
                shell=False,
            )

            self.monitored_pids[self.server_process.pid] = "Llama Engine"

            # Attach Relay
            self.server_relay = LogRelay(self.server_process)
            self.server_relay.start()

            # Wait for startup
            safe_print(f"{EMOJI['rocket']} Waiting for Engine to Ignite (Port {config.llm_port})...")
            wait_for_port(config.llm_port, timeout=30)

            return self.server_process

        except Exception as e:
            logger.error(f"Failed to ignite engine: {e}")
            raise


# Global Singleton
zen_heart = ZenHeart()


class ZenBrain:
    """
    The Brain of the system.
    Responsibilities:
    - Model Discovery: Find and catalog available GGUF models
    - Model Selection: Recommend optimal model based on hardware
    - Model Validation: Verify model integrity and compatibility
    Uses LocalLLMManager (unified module from RAG_RAT)
    """

    def __init__(self, model_dir: Optional[Path] = None):
        """Initialize the brain with unified LLM management"""
        self.manager = LocalLLMManager(model_dir or Path(config.MODEL_DIR))
        self.status: Optional[LocalLLMStatus] = None
        self.selected_model: Optional[str] = None
        logger.info("[Brain] Initialized with unified LLM infrastructure")

    def wake_up(self) -> LocalLLMStatus:
        """
        Initialize and discover available models.
        Returns complete status of LLM infrastructure.
        """
        logger.info("[Brain] Waking up... searching for llama-server and GGUF models")
        try:
            self.status = self.manager.initialize(check_updates=False)

            if self.status.llama_cpp_ready:
                safe_print(
                    f"{EMOJI['success']} llama.cpp detected: {getattr(self.status.llama_cpp_status, 'path', 'unknown')}"
                )
            else:
                safe_print(f"{EMOJI['warning']} llama.cpp not found - check {config.BIN_DIR}")

            safe_print(f"{EMOJI['info']} Discovered {self.status.models_discovered} models")

            # Log available models
            if self.status.models:
                safe_print(f"  Top models: {', '.join([m.name for m in self.status.models[:3]])}")

            return self.status
        except Exception as e:
            logger.error(f"[Brain] Failed to initialize: {e}")
            raise

    def get_status(self) -> Dict:
        """Get current brain status"""
        if not self.status:
            self.wake_up()
        return self.status.to_dict() if self.status else {}

    def recommend_model(self, category: Optional[str] = None) -> Optional[str]:
        """
        Recommend a model based on hardware and category.

        Args:
            category: Model category (e.g., 'chat', 'code', 'vision')

        Returns:
            Recommended model filename or None
        """
        if not self.status or not self.status.models:
            logger.warning("[Brain] No models available for recommendation")
            return None

        # Simple recommendation: return first model matching category
        if category:
            matching = [m for m in self.status.models if m.category and m.category.lower() == category.lower()]
            if matching:
                return matching[0].filename

        # Default: return first available model
        if self.status.models:
            return self.status.models[0].filename

        return None

    def select_model(self, model_name: str):
        """Select a specific model"""
        self.selected_model = model_name
        logger.info(f"[Brain] Selected model: {model_name}")


# Global Singleton
zen_brain = ZenBrain()
