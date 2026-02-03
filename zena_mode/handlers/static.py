import os
import mimetypes
import logging
from zena_mode.handlers.base import BaseZenHandler
from config_system import config

logger = logging.getLogger("ZenAI.Handler.Static")

class StaticHandler:
    """Namespace for static file serving."""
    
    @staticmethod
    def handle_get(handler: BaseZenHandler):
        """Routing for GET requests related to static files."""
        path = handler.path
        
        # Security: Prevent directory traversal
        if '..' in path:
            handler.send_json_response(403, {"error": "Forbidden"})
            return True

        # Mapping for static assets
        if path.startswith('/static/') or path.startswith('/assets/'):
            try:
                # Resolve local file path
                rel_path = path.lstrip('/')
                file_path = config.BASE_DIR / rel_path
                
                if file_path.exists() and file_path.is_file():
                    content_type, _ = mimetypes.guess_type(str(file_path))
                    handler.send_response(200)
                    handler.send_header('Content-Type', content_type or 'application/octet-stream')
                    handler.end_headers()
                    with open(file_path, 'rb') as f:
                        handler.wfile.write(f.read())
                    return True
            except Exception as e:
                logger.error(f"Static file error: {e}")
                handler.send_json_response(500, {"error": str(e)})
                return True
        return False
