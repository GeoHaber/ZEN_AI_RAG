# -*- coding: utf-8 -*-
"""
resource_manager.py - Dynamic Resource Management for ZenAI V2
Monitors system RAM and determines model loading strategies to prevent crashes.
"""
import logging
import platform
import os
from typing import Dict, Literal, Optional

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
        self.strategy: Literal["SERIAL", "SWAP", "PARALLEL"] = "SERIAL"
        self.total_ram_gb = 0
        self.available_ram_gb = 0
        self._refresh_stats()
        self._determine_strategy()

    def _refresh_stats(self):
        """Update current memory stats."""
        if PSUTIL_AVAILABLE:
            mem = psutil.virtual_memory()
            self.total_ram_gb = mem.total / (1024 ** 3)
            self.available_ram_gb = mem.available / (1024 ** 3)
        else:
            # Fallback for no psutil
            self.total_ram_gb = 8.0 # Assume baseline
            self.available_ram_gb = 4.0

    def _determine_strategy(self):
        """Calculate best strategy based on Total RAM."""
        # Note: We use Total RAM for strategy definition, but check Available RAM for immediate actions.
        
        if self.total_ram_gb < 8.5: # < 8GB (giving some margin)
            self.strategy = "SERIAL"
        elif self.total_ram_gb < 16.5: # 8GB - 16GB
            self.strategy = "SWAP"
        else: # > 16GB
            self.strategy = "PARALLEL"
        
        logger.info(f"[ResourceManager] Strategy: {self.strategy} (Total: {self.total_ram_gb:.1f}GB, Avail: {self.available_ram_gb:.1f}GB)")

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
            "psutil": PSUTIL_AVAILABLE
        }

# Global singleton
resource_manager = ResourceManager()

if __name__ == "__main__":
    # Test run
    print(f"Strategy: {resource_manager.strategy}")
    print(f"Can load 4GB model? {resource_manager.can_load_model(4.0)}")
