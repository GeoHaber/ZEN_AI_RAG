"""
Orchestration Handler - Manages model swapping, swarm scaling, and admin operations.
"""

import logging
import threading
from zena_mode.handlers.base import BaseZenHandler

logger = logging.getLogger("ZenAI.Handler.Orchestration")


class OrchestrationHandler:
    """Namespace for orchestration-related request handling (swap, scale, etc.)."""

    @staticmethod
    def handle_post(handler: BaseZenHandler):
        """Routing for POST requests related to orchestration."""

        if handler.path == "/swap":
            from zena_mode.server import restart_with_model

            params = handler.parse_json_body()
            model_name = params.get("model")
            if not model_name:
                handler.send_json_response(400, {"error": "Missing 'model' parameter"})
                return True
            threading.Thread(target=restart_with_model, args=(model_name,), daemon=True).start()
            handler.send_json_response(200, {"status": "accepted", "model": model_name})
            return True

        if handler.path == "/swarm/scale":
            from zena_mode.server import scale_swarm

            params = handler.parse_json_body()
            count = params.get("count", 3)
            if not isinstance(count, int) or count < 1 or count > 10:
                handler.send_json_response(400, {"error": "count must be integer 1-10"})
                return True
            threading.Thread(target=scale_swarm, args=(count,), daemon=True).start()
            handler.send_json_response(200, {"status": "scaling", "target": count})
            return True

        if handler.path == "/swarm/launch":
            from zena_mode.server import launch_expert_process
            from config_system import config
            from pathlib import Path

            params = handler.parse_json_body()
            model_name = params.get("model")
            port = params.get("port")

            if not model_name or not port:
                handler.send_json_response(400, {"error": "Missing 'model' or 'port'"})
                return True

            # Resolve Model Path
            # 1. Check if absolute
            m_path = Path(model_name)
            if not m_path.is_absolute():
                # 2. Check in standard model dir
                m_path = config.MODEL_DIR / model_name

            if not m_path.exists():
                # 3. Check in central store via config (portable)
                try:
                    from config import MODEL_DIR as _cfg_model_dir
                    central = _cfg_model_dir / model_name
                except Exception:
                    central = m_path  # no-op fallback
                if central.exists():
                    m_path = central
                else:
                    handler.send_json_response(404, {"error": f"Model not found: {model_name}"})
                    return True

            # Launch in background thread to not block response?
            # launch_expert_process is fast (Popen), so it's fine.
            try:
                launch_expert_process(port=int(port), threads=2, model_path=m_path)
                handler.send_json_response(200, {"status": "launched", "port": port, "model": str(m_path)})
            except Exception as e:
                handler.send_json_response(500, {"error": str(e)})

            return True

        return False
