import logging
import requests
from zena_mode.handlers.base import BaseZenHandler
from config_system import config

logger = logging.getLogger("ZenAI.Handler.Chat")


class ChatHandler:
    """Namespace for chat-related request handling."""

    @staticmethod
    def handle_post(handler: BaseZenHandler):
        """Routing for POST requests related to chat."""
        if handler.path == "/api/chat":
            params = handler.parse_json_body()
            user_msg = params.get("message", "")
            if not user_msg:
                handler.send_json_response(400, {"error": "Missing message"})
                return True

            try:
                # Forward to LLM Engine (8001)
                # We resolve the engine name from current active model
                from zena_mode.server import MODEL_PATH

                payload = {
                    "model": MODEL_PATH.name,
                    "messages": [
                        {"role": "system", "content": "You are ZenAI, a helpful assistant. Keep answers short."},
                        {"role": "user", "content": user_msg},
                    ],
                    "stream": False,
                    "max_tokens": 150,
                }
                resp = requests.post(config.get_api_url(), json=payload, timeout=30)
                if resp.status_code == 200:
                    llm_data = resp.json()
                    content = llm_data["choices"][0]["message"]["content"]
                    handler.send_json_response(200, {"response": content, "emotion": "neutral"})
                else:
                    handler.send_json_response(500, {"error": f"LLM Error: {resp.text}"})
            except Exception as e:
                logger.error(f"Chat proxy error: {e}")
                handler.send_json_response(500, {"error": str(e)})
            return True

        return False
