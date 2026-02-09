import os
import sys
import json
import time
import threading
import subprocess
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import asyncio

try:
    import websockets
except ImportError:
    websockets = None

# --- Shared Imports ---
from utils import (
    logger, safe_print, is_port_active, ensure_package
)
from config_system import config

# --- Core Modules ---
from zena_mode.heart_and_brain import zen_heart
from zena_mode.handlers import (
    BaseZenHandler, ModelHandler, VoiceHandler, StaticHandler, ChatHandler,
    HealthHandler, OrchestrationHandler
)

# Global Variables (Derived from Config)
MODEL_PATH = config.MODEL_DIR / config.default_model

# --- Orchestrator API (The Mouth) ---
class ZenAIOrchestrator(BaseZenHandler):
    """
    Management API (Port 8002) - Now simplified to delegate to Handlers.
    """
    def do_GET(self):
        """Main GET routing entry point."""
        # Delegate to Modular Handlers (priority order)
        if HealthHandler.handle_get(self): return
        if ModelHandler.handle_get(self): return
        if VoiceHandler.handle_get(self): return
        if StaticHandler.handle_get(self): return

        # Default fallback
        self.send_json_response(200, {"status": "ZenAI Hub Active", "path": self.path})

    def do_POST(self):
        """Main POST routing entry point."""
        # Security check
        if not self.check_request_size(): return

        # Delegate to Modular Handlers
        if OrchestrationHandler.handle_post(self): return
        if ModelHandler.handle_post(self): return
        if VoiceHandler.handle_post(self): return
        if ChatHandler.handle_post(self): return

        # Default fallback
        self.send_json_response(404, {"error": "Endpoint not found"})

# --- Helper Functions ---
def start_hub():
    """Start the Management API (Hub)."""
    use_asgi = os.environ.get("ZENAI_USE_ASGI", "1") == "1"
    
    if use_asgi:
        try:
            import uvicorn
            from zena_mode.asgi_server import app
            safe_print(f"[*] Starting ASGI Hub API on 127.0.0.1:{config.mgmt_port}...")
            
            def run_uvicorn():
                import asyncio
                # Set loop for this thread to avoid MainThread conflicts
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                uvicorn_config = uvicorn.Config(
                    app, 
                    host="127.0.0.1", 
                    port=config.mgmt_port, 
                    log_level="warning",
                    loop="asyncio"
                )
                server = uvicorn.Server(uvicorn_config)
                loop.run_until_complete(server.serve())
            
            threading.Thread(target=run_uvicorn, daemon=True).start()
            safe_print(f"[*] ASGI Hub API listening on 127.0.0.1:{config.mgmt_port}")
        except Exception as e:
            safe_print(f"⚠️ ASGI startup failed, fallback to sync: {e}")
            _start_sync_hub()
    else:
        _start_sync_hub()

def _start_sync_hub():
    """Legacy sync HTTP server fallback."""
    try:
        safe_print(f"[*] Starting sync Hub API on port {config.mgmt_port}...")
        hub = ThreadingHTTPServer(('127.0.0.1', config.mgmt_port), ZenAIOrchestrator)
        threading.Thread(target=hub.serve_forever, daemon=True).start()
    except Exception as e:
        safe_print(f"❌ Hub Startup Failed: {e}")

# --- Voice Streaming ---
try:
    from zena_mode.voice_stream import VoiceStreamHandler
except ImportError:
    # Stub for bootstrap/dev where file might not exist yet
    class VoiceStreamHandler:
        def __init__(self): pass
        async def handle_client(self, ws): pass

# Global handler instance
voice_stream_handler = VoiceStreamHandler()

async def run_ws_server():
    if websockets:
        try:
            # Serve using the instance's handle_client method
            async with websockets.serve(voice_stream_handler.handle_client, "0.0.0.0", 8006):
                safe_print("[*] Voice Stream Server listening on Port 8006")
                await asyncio.Future()
        except OSError:
            safe_print(f"⚠️ Voice Port 8006 busy. Voice features limited.")
        except Exception as e:
            safe_print(f"Voice Server Error: {e}")

def start_voice_stream_server():
    if websockets:
        threading.Thread(target=lambda: asyncio.run(run_ws_server()), daemon=True).start()

# --- Main Entry Point (Called by start_llm.py) ---
def start_server():
    """
    Ignites the Heart and Brain.
    Replaces the old monolithic startup logic.
    """
    try:
        safe_print(f"✨ ZenAI Core (Heart & Brain) Activating...")
        
        # 1. Ignite the Engine (The Heart)
        # This handles hardware detection, command building, and launch
        if "--guard-bypass" not in sys.argv:
             # Standard launch
             zen_heart.ignite()
        
        # 2. Start the API Interface (The Mouth)
        if "--guard-bypass" not in sys.argv or config.llm_port == 8001:
            start_hub()
            start_voice_stream_server()

        # 3. Launch UI (The Face)
        if "--guard-bypass" not in sys.argv and "--no-ui" not in sys.argv:
            zena_script = str(config.BASE_DIR / "zena.py")
            ui_env = os.environ.copy()
            ui_env["ZENA_SKIP_PRUNE"] = "1"
            
            safe_print("[*] Launching UI...")
            # We don't track UI in Heart yet, maybe TODO?
            # For now, fire and forget (the UI script handles its own life)
            subprocess.Popen(
                [sys.executable, zena_script], 
                cwd=str(config.BASE_DIR), 
                env=ui_env,
                # Detach if possible to let UI survive engine restarts? 
                # No, standard subprocess is fine.
            )

        # 4. Enter Main Life Loop (Blocking)
        zen_heart.pump()

    except KeyboardInterrupt:
        safe_print("\n[*] Manual shutdown initiated by user.")
    except Exception as e:
        safe_print(f"❌ Critical Failure: {e}")
        import traceback
        traceback.print_exc()
    finally:
        safe_print("[*] System Shutdown.")
        sys.exit(0)

if __name__ == "__main__":
    start_server()
