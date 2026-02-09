from http.server import BaseHTTPRequestHandler
import json
import logging
from config_system import config

logger = logging.getLogger("ZenAI.Handler")

class BaseZenHandler(BaseHTTPRequestHandler):
    """Base class for Zena AI server handlers, providing common logic and security."""
    
    def send_json_response(self, status: int, data: dict):
        """Standard JSON response helper."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        # Security: Restrict CORS to localhost only (Phase 1 hardening)
        self.send_header('Access-Control-Allow-Origin', 'http://127.0.0.1:8080')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def check_request_size(self) -> bool:
        """Enforces a global request size limit (Phase 1 security hardening)."""
        content_length_str = self.headers.get('Content-Length')
        if content_length_str is None:
            # For security, we reject POSTs without a content length in this orchestrator.
            if self.command == "POST":
                self.send_json_response(411, {"error": "Content-Length required"})
                return False
            return True # GET etc.
            
        try:
            content_length = int(content_length_str)
        except ValueError:
            self.send_json_response(400, {"error": "Invalid Content-Length"})
            return False

        if content_length > config.get('MAX_FILE_SIZE', 10485760):
            self.send_json_response(413, {"error": "Request entity too large"})
            return False
        return True

    def parse_json_body(self) -> dict:
        """Helper to parse JSON from the request body."""
        if not self.check_request_size(): return {}
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0: return {}
            return json.loads(self.rfile.read(content_length))
        except Exception as e:
            logger.error(f"Failed to parse JSON body: {e}")
            return {}
