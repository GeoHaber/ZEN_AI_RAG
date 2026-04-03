"""Minimal hub server for tests.

This module provides a small, stable HTTP hub implementation exposing
`start_hub` and `stop_hub` so the test-suite and the root shim can import
and control the management API without pulling in the full orchestrator.
"""

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import threading
import time
from typing import Tuple

# Use project config defaults so shim/tests don't need to pass ports
try:
    from config_system import config

    HOST = config.host
    PORTS = {"MGMT_API": config.mgmt_port}
except Exception:
    HOST = "127.0.0.1"
    PORTS = {"MGMT_API": 8002}


class _SimpleHandler(BaseHTTPRequestHandler):
    """_SimpleHandler class."""

    def do_OPTIONS(self):
        """Do options."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8080")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Do get."""
        # Minimal routes used by the test-suite
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ZenAI Hub Active")
            return

        if self.path == "/models/available":
            import json

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps([]).encode())
            return

        if self.path.startswith("/updates/check"):
            import json

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({}).encode())
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        return


def _serve_in_thread(server: ThreadingHTTPServer):
    try:
        server.serve_forever()
    except Exception:
        pass


def start_hub(host: str | None = None, port: int | None = None) -> Tuple[ThreadingHTTPServer, threading.Thread]:
    """Start a minimal HTTP hub in a background thread.

    Returns the (server, thread) so callers/tests can shut it down.
    """
    bind_host = host if host is not None else HOST
    bind_port = port if port is not None else PORTS.get("MGMT_API", 8002)
    server = ThreadingHTTPServer((bind_host, bind_port), _SimpleHandler)
    thread = threading.Thread(target=_serve_in_thread, args=(server,), daemon=True)
    thread.start()
    # Give server a moment to bind and verify it's reachable
    timeout = 2.0
    interval = 0.05
    elapsed = 0.0
    import socket

    bound = False
    while elapsed < timeout:
        try:
            with socket.create_connection((bind_host, bind_port), timeout=0.5):
                bound = True
                break
        except Exception:
            time.sleep(interval)
            elapsed += interval

    if not bound:
        # If binding failed, clean up server and raise so caller can see the error.
        try:
            server.shutdown()
            server.server_close()
        except Exception:
            pass
        raise RuntimeError(f"Hub failed to bind to {bind_host}:{bind_port} within {timeout}s")

    print(f"HUB_BOUND {bind_host}:{bind_port}")
    return server, thread


def stop_hub(server: ThreadingHTTPServer):
    """Stop the hub started by `start_hub`.
    This is safe to call from tests or cleanup hooks.
    """
    try:
        server.shutdown()
        server.server_close()
    except Exception:
        pass


def start_server(*args, **kwargs):
    """Backwards-compatible entry that starts the hub.

    The original project exposes a `start_server` entrypoint; keep a thin
    wrapper so imports remain stable during migration.
    """
    return start_hub(*args, **kwargs)


__all__ = ["start_hub", "stop_hub", "start_server"]
