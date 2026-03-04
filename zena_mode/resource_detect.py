# -*- coding: utf-8 -*-
"""
resource_detect.py - Dedicated Hardware Discovery Module
======================================================
The "Senses" of ZenAI. Detects CPU, GPU, and VRAM capabilities
to optimize the "Brain" (LLM Engine).
"""
import os
import sys
import logging
import subprocess

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger("ResourceDetect")

class HardwareProfiler:
    """Detects available hardware resources for AI Inference."""
    
    @staticmethod
    def _get_nvidia_vram() -> int:
        """Get FREE VRAM in MiB using nvidia-smi."""
        try:
            # nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"], 
                encoding="utf-8", 
                creationflags=creation_flags
            )
            return int(out.strip().split('\n')[0])
        except Exception:
            return 0

    @staticmethod
    def get_profile() -> dict:
        """
        Scan system for CPU threads and GPU VRAM.
        Returns dict: {
            "type": "CPU" | "NVIDIA" | "AMD",
            "ram_gb": float,
            "vram_mb": int (Total/Estimated),
            "free_vram_mb": int (Actual Free),
            "threads": int (Physical Cores)
        }
        """
        # Default to logical count, but prefer physical for LLM work
        cpu_threads = os.cpu_count() or 4
        if psutil:
            try:
                # efficient inference usually prefers physical cores
                phy_cores = psutil.cpu_count(logical=False)
                if phy_cores:
                    cpu_threads = phy_cores
            except Exception: pass
        
        profile = {
            "type": "CPU", 
            "ram_gb": 8.0, 
            "vram_mb": 0, 
            "free_vram_mb": 0, 
            "threads": cpu_threads
        }
        
        try:
            if psutil: 
                profile['ram_gb'] = round(psutil.virtual_memory().total / (1024**3), 1)
            
            if sys.platform == "win32":
                # 1. Check NVIDIA via SMI (Most reliable for Free VRAM)
                free_vram = HardwareProfiler._get_nvidia_vram()
                if free_vram > 0:
                    profile['type'] = "NVIDIA"
                    profile['free_vram_mb'] = free_vram
                    # Use free VRAM for 'vram_mb' if we can't get total, for safety
                    profile['vram_mb'] = free_vram 
                else:
                    # 2. WMI Fallback (Total VRAM via PowerShell) for AMD/Intel or driverless NVIDIA
                    cmd = "powershell -NoProfile -Command \"Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json\""
                    out = subprocess.check_output(
                        cmd, 
                        shell=False, 
                        text=True, 
                        stderr=subprocess.DEVNULL, 
                        timeout=3
                    ).strip()
                    
                    if out:
                        import json
                        gpus = json.loads(out)
                        if not isinstance(gpus, list): gpus = [gpus]
                        
                        for g in gpus:
                            name = g.get("Name", "").upper()
                            ram = g.get("AdapterRAM", 0) or 0
                            ram_mb = ram // (1024**2)
                            
                            # Prioritize Discrete GPU
                            if "NVIDIA" in name: 
                                profile['type'] = "NVIDIA"
                                profile['vram_mb'] = ram_mb
                                # If we missed free vram earlier, assume a safe chunk is free?
                                # No, better to leave free_vram_mb as 0 if we can't measure it.
                                break # Found NVIDIA, stop
                            elif "AMD" in name or "RADEON" in name: 
                                profile['type'] = "AMD"
                                profile['vram_mb'] = ram_mb
                                break
                                
        except (subprocess.SubprocessError, ValueError, KeyError, OSError, ImportError): 
            pass  # Hardware detection optional
        
        logger.info(f"[Profiler] Detected: {profile['type']} | {profile['ram_gb']}GB RAM | {profile['free_vram_mb']}MB Free VRAM | {profile['threads']} Threads")
        return profile
