# ZenAI Architecture Specification v3.2 (Heart & Brain)

**Version**: 3.2 (Modular "Heart & Brain" Architecture)
**Date**: 2026-02-04
**Status**: Production-Ready

---

## 1. Project Identity
**ZenAI** is a hyper-secure, privacy-obsessed local AI assistant.
- **Core Mandate**: 100% ZERO DATA EGRESS.
- **UX Imperative**: Transparency in RAG and Local Processing.

## 2. Technology Stack
- **Engine**: `llama.cpp` (via `llama-server.exe`).
- **Orchestration**: Python `subprocess` + `threading`.
- **Frontend**: NiceGUI (Vue/Quasar).
- **Communication**: HTTP/REST (Port 8001, 8004), WebSocket (8003).

## 3. "Heart & Brain" Architecture
The monolithic orchestration has been refactored into biological modules for resilience.

### A. The Senses (`zena_mode/resource_detect.py`)
**Responsibility**: Dedicated Hardware Discovery.
1.  **CPU**: Detects *Physical* vs Logical cores to optimize `llama.cpp` threads (avoiding hyperthreading overhead).
2.  **GPU**:
    -   **NVIDIA**: Uses `nvidia-smi` to query *Free VRAM*.
    -   **AMD**: Uses WMI to query *Total VRAM* (assumes 70% usable).
3.  **VRAM Governor**: Calculates safe layer offload count: `(Free VRAM - 500MB Buffer) / 120MB`.

### B. The Heart (`zena_mode/heart_and_brain.py` - `ZenHeart`)
**Responsibility**: Engine Lifecycle & Pulse.
1.  **Ignition**: Starts `llama-server` with optimal parameters derived from *The Senses*.
2.  **Pulse Monitor**: Checks process status (`poll()`) every 2 seconds.
3.  **Pacemaker**:
    -   Detects **Crashes** (Exit Code != None).
    -   Detects **Zombie Hangs** (Process running but Port 8001 unresponsive).
    -   **Auto-Recovery**: Automatically restarts the engine up to 3 times per session before safety shutdown.
4.  **Log Relay**: Captures stdout/stderr in a non-blocking thread using binary read chunks (prevents Windows pipe deadlocks).

### C. The Mouth (`zena_mode/server.py`)
**Responsibility**: External Interface.
1.  **Logic-Free**: pure API layer.
2.  **Endpoints**:
    -   `GET /health`: Reports Heart status.
    -   `POST /model/swap`: Signals Heart to restart with new model.
    -   `POST /swarm/launch`: Signals Brain to launch Expert process.

### D. The Brain (`zena_mode/heart_and_brain.py` - `ZenBrain`)
**Responsibility**: Intelligence Management (Planned).
1.  **Model Registry**: Paths to GGUF files.
2.  **Swarm Council**: Manages secondary "Expert" processes on ports 8005+.

## 4. Boot Sequence (`start_llm.py`)
1.  **Prune Zombies**: Kills any lingering `llama-server` or `python` processes on critical ports.
2.  **Atomic Update**: Checks for binary updates (`.new` -> `.exe`).
3.  **Ignite Heart**: Calls `ZenHeart.ignite()`.
4.  **Launch Mouth**: Starts API server.
5.  **Launch Face**: Starts UI (`zena.py`).
6.  **Pump Loop**: Enters blocking `zen_heart.pump()` monitor loop.

## 5. Security & Stability Commandments
1.  **VRAM Safety**: NEVER hardcode gpu-layers. Always calculate based on *current* free memory.
2.  **Zero Trust inputs**: All web/file inputs must be sanitized before RAG.
3.  **Resilience**: The system must survive a user killing `llama-server.exe` manually (verified via `test_llm_chaos.py`).

---
**Verification**: Run `tests/test_llm_chaos.py` to validate architecture integrity.
