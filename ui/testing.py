import logging
import json
import time
import asyncio
from fastapi import Response
from nicegui import app

logger = logging.getLogger("ZenAI.Test")


def register_test_endpoints():
    """Register hidden testing endpoints for Monkey Test and chaos testing."""

    @app.post("/test/click/{element_id}")
    async def test_click_element(element_id: str):
        """Simulate a click on a UI element for chaos testing."""
        logger.info(f"[Test] Simulating click on: {element_id}")
        try:
            # Broadcast click to all connected clients
            clients = app.clients
            if callable(clients):
                try:
                    clients = clients()
                except TypeError:
                    pass

            # Support both dict and list-like clients
            client_list = []
            if isinstance(clients, dict):
                client_list = list(clients.values())
            elif clients:
                try:
                    client_list = list(clients)
                except (TypeError, ValueError):
                    client_list = []

            for client in client_list:
                try:
                    client.run_javascript(f"document.getElementById('{element_id}')?.click()")
                except Exception as e:
                    logger.debug(f"[Test] Failed for client: {e}")
                    continue
            return Response(status_code=200)
        except Exception as e:
            logger.error(f"[Test] Click simulation failed: {e}")
            return Response(content=str(e), status_code=500)

    @app.get("/test/state")
    async def test_get_ui_state():
        """Retrieve a summary of the current UI state (text and visible components)."""
        return {"active": True, "timestamp": time.time()}

    @app.post("/test/send")
    async def test_send_message(data: dict):
        """Simulate typing and sending a message for automated testing."""
        text = data.get("text", "")
        logger.info(f"[Test] Simulating send: {text}")
        try:
            # Broadcast to all clients (Super Robust)
            clients_obj = getattr(app, "clients", None)

            client_list = []
            if clients_obj:
                if callable(clients_obj):
                    try:
                        clients_obj = clients_obj()
                    except TypeError:
                        pass

                if isinstance(clients_obj, dict):
                    client_list = list(clients_obj.values())
                elif isinstance(clients_obj, (list, set, tuple)):
                    client_list = list(clients_obj)

            # Fallback to NiceGUI globals if app.clients failed
            if not client_list:
                try:
                    from nicegui import globals as ng_globals

                    client_list = list(ng_globals.clients.values())
                except (ImportError, AttributeError, TypeError):
                    pass

            logger.info(f"[Test] Broadasting to {len(client_list)} clients")

            for client in client_list:
                try:
                    js = f"""
                    (function() {{
                        const input = document.getElementById('ui-input-chat');
                        const btn = document.getElementById('ui-btn-send');
                        if (input) {{
                            input.value = {json.dumps(text)};
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            console.log('[Test] Input set to:', input.value);
                            if (btn) {{
                                setTimeout(() => {{
                                    console.log('[Test] Clicking send button');
                                    btn.click();
                                }}, 100);
                            }}
                        }}
                    }})();
                    """
                    client.run_javascript(js)
                except Exception as e:
                    logger.debug(f"[Test] Send failed for client: {e}")
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"[Test] Send simulation failed: {e}")
            return Response(content=str(e), status_code=500)
