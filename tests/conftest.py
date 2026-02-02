# conftest.py - pytest configuration for ZenAI tests
import sys
import pytest
import respx
import httpx
import threading
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List
from pathlib import Path
import asyncio

# Add project root to Python path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

@pytest.fixture
def mock_llm_api():
    """Fixture to mock LLM API responses (8001)."""
    with respx.mock(base_url="http://127.0.0.1:8001", assert_all_called=False) as respx_mock:
        # Health check
        respx_mock.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        
        # Chat completion stream
        stream_content = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n',
            'data: {"choices": [{"delta": {"content": " world!"}}]}\n\n',
            'data: [DONE]\n\n'
        ]
        respx_mock.post("/v1/chat/completions").mock(return_value=httpx.Response(200, content="".join(stream_content)))
        
        yield respx_mock

@pytest.fixture
def mock_hub_api():
    """Fixture to mock Hub API responses (8002)."""
    with respx.mock(base_url="http://127.0.0.1:8002", assert_all_called=False) as respx_mock:
        respx_mock.get("/models/available").mock(return_value=httpx.Response(200, json=["mock-model-1.gguf", "mock-model-2.gguf"]))
        respx_mock.post("/models/load").mock(return_value=httpx.Response(200, json={"status": "loaded"}))
        respx_mock.post("/models/download").mock(return_value=httpx.Response(200, json={"status": "started"}))
        
        yield respx_mock

class _SimpleExpertHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


class _HubHandler(BaseHTTPRequestHandler):
    # Shared state will be injected by the fixture
    servers: Dict[int, HTTPServer] = {}

    def do_POST(self):
        if self.path == '/swarm/scale':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                count = int(data.get('count', 0))
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            # Start `count` expert servers on ports 8005.. upwards
            started: List[int] = []
            base = 8005
            for i in range(count):
                port = base + i
                if port in _HubHandler.servers:
                    started.append(port)
                    continue
                server = HTTPServer(('127.0.0.1', port), _SimpleExpertHandler)
                t = threading.Thread(target=server.serve_forever, daemon=True)
                t.start()
                _HubHandler.servers[port] = server
                started.append(port)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            resp = {'status': 'scaled', 'ports': started}
            self.wfile.write(json.dumps(resp).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/swarm/list':
            ports = list(_HubHandler.servers.keys())
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ports': ports}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


@pytest.fixture(scope='session', autouse=True)
def hub_server():
    """Start a lightweight Hub on 127.0.0.1:8002 that can scale experts for integration tests."""
    # Ensure config flags used by SwarmArbitrator are enabled during tests
    try:
        import config as _config_mod
        _config_mod.SWARM_ENABLED = True
        _config_mod.SWARM_SIZE = 7
    except Exception:
        pass

    hub = HTTPServer(('127.0.0.1', 8002), _HubHandler)
    th = threading.Thread(target=hub.serve_forever, daemon=True)
    th.start()

    yield

    # Teardown: shut down experts and hub
    try:
        hub.shutdown()
    except Exception:
        pass
    
    for srv in list(_HubHandler.servers.values()):
        try:
            srv.shutdown()
        except Exception:
            pass

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
