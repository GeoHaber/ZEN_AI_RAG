import logging
from zena_mode.handlers.base import BaseZenHandler
from config_system import config

try:
    import model_manager
except ImportError:
    model_manager = None  # type: ignore[assignment]

logger = logging.getLogger("ZenAI.Handler.Models")


class ModelHandler:
    """Namespace for model-related request handling."""

    @staticmethod
    def handle_get(handler: BaseZenHandler):
        """Routing for GET requests related to models."""
        path = handler.path

        if path == "/list":
            try:
                models = [f.name for f in config.MODEL_DIR.glob("*.gguf")]
                handler.send_json_response(200, {"models": models})
            except Exception as e:
                handler.send_json_response(500, {"error": str(e)})

        elif path == "/models/popular":
            try:
                models = model_manager.get_popular_models()
                handler.send_json_response(200, models)
            except Exception as e:
                handler.send_json_response(500, {"error": str(e)})

        elif path.startswith("/models/search"):
            import urllib.parse

            query = urllib.parse.parse_qs(urllib.parse.urlparse(path).query).get("q", [""])[0]
            try:
                models = model_manager.search_hf_models(query)
                handler.send_json_response(200, models)
            except Exception as e:
                handler.send_json_response(500, {"error": str(e)})
        else:
            return False  # Not handled
        return True

    @staticmethod
    def handle_post(handler: BaseZenHandler):
        """Routing for POST requests related to models."""
        if handler.path == "/models/download":
            params = handler.parse_json_body()
            repo_id = params.get("repo_id")
            filename = params.get("filename")

            if not repo_id or not filename:
                handler.send_json_response(400, {"error": "Missing repo_id or filename"})
                return True

            try:
                model_manager.download_model_async(repo_id, filename)
                handler.send_json_response(200, {"status": "started", "message": f"Downloading {filename}..."})
            except Exception as e:
                handler.send_json_response(500, {"error": str(e)})
            return True
        return False
