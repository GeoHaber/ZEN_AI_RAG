# -*- coding: utf-8 -*-
"""
resource_manager.py - Dynamic Resource Management for ZenAI V2
Monitors system RAM and determines model loading strategies to prevent crashes.
"""

import logging
from typing import Dict, Literal, Optional
import threading

# from typing import List, Optional
from config_system import config
import asyncio

# Configure logging
logger = logging.getLogger("ResourceManager")

# Try to import psutil, handled gracefully if missing
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("[ResourceManager] psutil not found. Dynamic RAM detection disabled (defaulting to Safe Mode).")


class ResourceManager:
    """
    Monitors system resources and delegates loading strategies.

    Strategies:
    - SERIAL: Unload current -> Load new (Safe, Slow). Used when RAM < 8GB.
    - SWAP: Keep Orchestrator, swap Experts. Used for 8-16GB RAM.
    - PARALLEL: Keep Orchestrator + Expert loaded. Used for > 16GB RAM.
    """

    def __init__(self):
        """Initialize instance."""
        self.strategy: Literal["SERIAL", "SWAP", "PARALLEL"] = "SERIAL"
        self.total_ram_gb = 0
        self.available_ram_gb = 0
        self._refresh_stats()
        self._determine_strategy()
        # Optional worker thread tracking (for background tasks spawned by orchestrator)
        self._worker_threads: List[threading.Thread] = []
        self._threads_lock = threading.Lock()

    def add_worker_thread(self, target, args=(), daemon=True, max_workers: Optional[int] = None):
        """Start and register a background thread, optionally enforcing a max worker count.

        Returns the Thread object.
        """
        # Determine effective max_workers
        max_workers if max_workers is not None else getattr(config, "GENERIC_MAX_WORKERS", 4)

        t = threading.Thread(target=target, args=args, daemon=daemon)
        with self._threads_lock:
            self._worker_threads.append(t)
            # If max_workers is set, prune finished threads and optionally refuse new threads
            if max_workers is not None:
                # cleanup first
                self.cleanup_finished_threads()
                if len(self._worker_threads) >= max_workers:
                    # Do not start new worker to avoid resource exhaustion
                    raise RuntimeError("Max worker threads reached")
        t.start()
        return t

    def cleanup_finished_threads(self):
        """Remove finished worker threads from internal registry."""
        with self._threads_lock:
            self._worker_threads = [t for t in self._worker_threads if t.is_alive()]

    def get_worker_count(self) -> int:
        with self._threads_lock:
            self.cleanup_finished_threads()
            return len(self._worker_threads)

    def run_in_thread_future(self, func, *args, daemon=True, max_workers: Optional[int] = None):
        """Run `func(*args)` in a background thread, return an asyncio.Future tied to the current loop.

        The thread is tracked in the internal registry so cleanup can prune finished threads.
        Raises RuntimeError if max_workers would be exceeded.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Not called from an event loop
            raise RuntimeError("run_in_thread_future must be called from an async context")

        fut = loop.create_future()

        def _target():
            try:
                res = func(*args)
            except Exception as e:
                loop.call_soon_threadsafe(fut.set_exception, e)
                return
            loop.call_soon_threadsafe(fut.set_result, res)

        # Determine effective max_workers
        effective_max = max_workers if max_workers is not None else getattr(config, "GENERIC_MAX_WORKERS", 4)

        t = threading.Thread(target=_target, daemon=daemon)
        with self._threads_lock:
            self._worker_threads.append(t)
            if effective_max is not None:
                self.cleanup_finished_threads()
                if len(self._worker_threads) > effective_max:
                    # remove the appended thread to keep state consistent
                    self._worker_threads.pop()
                    raise RuntimeError("Max worker threads reached")

        t.start()
        return fut

    def _refresh_stats(self):
        """Update current memory stats."""
        if PSUTIL_AVAILABLE:
            mem = psutil.virtual_memory()
            self.total_ram_gb = mem.total / (1024**3)
            self.available_ram_gb = mem.available / (1024**3)
        else:
            # Fallback for no psutil
            self.total_ram_gb = 8.0  # Assume baseline
            self.available_ram_gb = 4.0

    def _determine_strategy(self):
        """Calculate best strategy based on Total RAM."""
        # Note: We use Total RAM for strategy definition, but check Available RAM for immediate actions.

        if self.total_ram_gb < 8.5:  # < 8GB (giving some margin)
            self.strategy = "SERIAL"
        elif self.total_ram_gb < 16.5:  # 8GB - 16GB
            self.strategy = "SWAP"
        else:  # > 16GB
            self.strategy = "PARALLEL"

        logger.info(
            f"[ResourceManager] Strategy: {self.strategy} (Total: {self.total_ram_gb:.1f}GB, Avail: {self.available_ram_gb:.1f}GB)"
        )

    def can_load_model(self, model_size_gb: float) -> bool:
        """Check if we have enough RAM to load a model of size_gb."""
        self._refresh_stats()
        # Leave 2GB buffer for OS/System
        safe_margin = 2.0
        return self.available_ram_gb > (model_size_gb + safe_margin)

    def get_status(self) -> Dict:
        """Return current status for UI."""
        self._refresh_stats()
        return {
            "strategy": self.strategy,
            "total_ram": f"{self.total_ram_gb:.1f} GB",
            "available_ram": f"{self.available_ram_gb:.1f} GB",
            "psutil": PSUTIL_AVAILABLE,
        }


# Global singleton
resource_manager = ResourceManager()

if __name__ == "__main__":
    # Test run
    # [X-Ray auto-fix] print(f"Strategy: {resource_manager.strategy}")
    pass
    # [X-Ray auto-fix] print(f"Can load 4GB model? {resource_manager.can_load_model(4.0)}")    pass
