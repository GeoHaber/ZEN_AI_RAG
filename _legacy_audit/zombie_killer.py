# -*- coding: utf-8 -*-
"""
zombie_killer.py - ZenAI Anti-Zombie Utility
Detects and kills processes blocking ZenAI ports.
"""
import os
import sys
import subprocess
import time
import logging

try:
    import psutil
except ImportError:
    print("[!] psutil not found. Installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "psutil"], capture_output=True)
    import psutil

logger = logging.getLogger("ZombieKiller")

def find_zombie_pids(ports=[8080, 8001, 8002], scripts=["zena.py", "start_llm.py", "llama-server.exe"]):
    """Find PIDs of processes listening on specific ports or running target scripts."""
    zombies = {}
    
    # 1. Port-based detection
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port in ports and conn.status == 'LISTEN':
            try:
                p = psutil.Process(conn.pid)
                if conn.pid == os.getpid(): continue
                zombies[conn.pid] = {
                    'type': 'Port conflict',
                    'port': conn.laddr.port,
                    'name': p.name(),
                    'cmdline': " ".join(p.cmdline()[:3])
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    # 2. Script-name based detection (Harder: find hanging pythons)
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = p.info['pid']
            if pid == os.getpid(): continue
            if pid in zombies: continue # Already caught by port
            
            cmd = p.info['cmdline'] or []
            cmd_str = " ".join(cmd).lower()
            
            for target in scripts:
                if target.lower() in cmd_str:
                    zombies[pid] = {
                        'type': 'Hanging process',
                        'port': 'N/A',
                        'name': p.info['name'],
                        'cmdline': cmd_str[:100]
                    }
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    return zombies

def prune_zombies(auto_confirm=False):
    """Detect and kill zombie processes with user confirmation."""
    zombies = find_zombie_pids()
    if not zombies:
        return True

    print("\n" + "🧟" * 15)
    print("  ZOMBIE DETECTED: STARTUP BLOCKED")
    print("🧟" * 15 + "\n")
    
    for pid, info in zombies.items():
        print(f"⚠️ {info['type']} (Port {info['port']})")
        print(f"   - PID  : {pid}")
        print(f"   - Name : {info['name']}")
        print(f"   - Cmd  : {info['cmdline']}...")
    
    if auto_confirm:
        reply = 'y'
    else:
        print("\nKill these processes to allow a clean startup? (y/n): ", end="", flush=True)
        try:
            # Simple input for console usage
            reply = input().lower()
        except:
            reply = 'n'

    if reply == 'y':
        for pid, info in zombies.items():
            try:
                p = psutil.Process(pid)
                p.terminate()
                print(f"✅ Terminated {info['type']} process {pid}")
            except Exception as e:
                print(f"❌ Failed to kill {pid}: {e}")
        time.sleep(1) # Wait for OS to release resources
        return True
    
    print("🚫 Startup aborted by user.")
    return False

if __name__ == "__main__":
    prune_zombies()
