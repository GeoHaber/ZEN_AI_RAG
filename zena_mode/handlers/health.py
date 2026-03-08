"""
Health Handler - Diagnostics, metrics, and status endpoints.
"""

import logging
from zena_mode.handlers.base import BaseZenHandler
from config_system import config

logger = logging.getLogger("ZenAI.Handler.Health")


class HealthHandler:
    """Namespace for health and diagnostics request handling."""

    @staticmethod
    def handle_get(handler: BaseZenHandler):
        """Routing for GET requests related to health/diagnostics."""

        if handler.path == "/health":
            from utils import is_port_active

            llm_status = is_port_active(config.llm_port)
            handler.send_json_response(
                200,
                {
                    "status": "healthy" if llm_status else "degraded",
                    "llm_online": llm_status,
                    "llm_port": config.llm_port,
                },
            )
            return True

        if handler.path == "/api/test-llm":
            from utils import is_port_active

            status = is_port_active(config.llm_port)
            handler.send_json_response(200, {"success": status, "port": config.llm_port})
            return True

        if handler.path == "/startup/progress":
            try:
                from startup_progress import get_startup_progress

                handler.send_json_response(200, get_startup_progress())
            except Exception:
                handler.send_json_response(200, {"stage": "loading", "percent": 0, "message": "Initializing..."})
            return True

        if handler.path == "/metrics":
            from zena_mode.profiler import monitor

            handler.send_json_response(200, monitor.get_summary())
            return True

        return False
