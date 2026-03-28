# conftest.py - pytest configuration for ZenAI tests
import sys
import types
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

# ── Stub out rag_core if not installed so zena_mode can be imported ──────────
if "rag_core" not in sys.modules:
    _rc = types.ModuleType("rag_core")
    _rc.__path__ = []
    _rc.__package__ = "rag_core"
    sys.modules["rag_core"] = _rc
    for _sub in (
        "bm25_index", "cache", "chunker", "dedup", "embeddings",
        "fusion", "models", "pipeline", "reranker", "retriever",
        "text_chunker",
    ):
        _m = types.ModuleType(f"rag_core.{_sub}")
        _m.__dict__.update({
            "BM25Index": type("BM25Index", (), {}),
            "SemanticCache": type("SemanticCache", (), {"__init__": lambda self, **kw: None}),
            "TextChunker": type("TextChunker", (), {}),
            "ChunkerConfig": type("ChunkerConfig", (), {}),
            "DeduplicationManager": type("DeduplicationManager", (), {}),
            "SmartDeduplicator": type("SmartDeduplicator", (), {}),
            "EmbeddingManager": type("EmbeddingManager", (), {}),
            "RerankerManager": type("RerankerManager", (), {}),
            "reciprocal_rank_fusion": lambda *a, **kw: [],
        })
        sys.modules[f"rag_core.{_sub}"] = _m
        setattr(_rc, _sub, _m)

# ── Pre-load zena_mode submodules bypassing __init__.py (avoids Qdrant hang) ─
import importlib.util as _ilu

# Register fake zena_mode package so `from zena_mode.X import Y` works without
# triggering the real __init__.py (which connects to Qdrant / heavy services).
if "zena_mode" not in sys.modules:
    _zm = types.ModuleType("zena_mode")
    _zm.__path__ = [str(ROOT / "zena_mode")]
    _zm.__package__ = "zena_mode"
    _zm.__file__ = str(ROOT / "zena_mode" / "__init__.py")
    sys.modules["zena_mode"] = _zm

# Load standalone submodules (no internal zena_mode deps)
for _mod_name in ("chunker", "rag_pipeline"):
    _fqn = f"zena_mode.{_mod_name}"
    if _fqn not in sys.modules:
        _spec = _ilu.spec_from_file_location(
            _fqn, str(ROOT / "zena_mode" / f"{_mod_name}.py")
        )
        if _spec and _spec.loader:
            _mod = _ilu.module_from_spec(_spec)
            _mod.__package__ = "zena_mode"
            sys.modules[_fqn] = _mod
            setattr(sys.modules["zena_mode"], _mod_name, _mod)
            try:
                _spec.loader.exec_module(_mod)
            except Exception:
                pass  # allow tests to detect broken imports themselves

# Stub zena_mode.handlers (a package) with dummy handler classes so server.py
# can be imported without loading the real handler stack.
if "zena_mode.handlers" not in sys.modules:
    _zh = types.ModuleType("zena_mode.handlers")
    _zh.__path__ = [str(ROOT / "zena_mode" / "handlers")]
    _zh.__package__ = "zena_mode.handlers"
    for _cls_name in (
        "BaseZenHandler", "ModelHandler", "VoiceHandler",
        "StaticHandler", "ChatHandler", "HealthHandler",
        "OrchestrationHandler",
    ):
        setattr(_zh, _cls_name, type(_cls_name, (), {}))
    sys.modules["zena_mode.handlers"] = _zh
    setattr(sys.modules["zena_mode"], "handlers", _zh)

# Stub config_system.config and utils if not importable
if "config_system" not in sys.modules:
    _cs = types.ModuleType("config_system")
    _cs.config = type("Config", (), {
        "get": lambda self, *a, **kw: kw.get("default"),
        "__getattr__": lambda self, name: None,
    })()
    sys.modules["config_system"] = _cs

if "utils" not in sys.modules:
    _ut = types.ModuleType("utils")
    import logging as _logging
    _ut.logger = _logging.getLogger("zenai_test")
    _ut.ensure_package = lambda *a, **kw: None
    _ut.safe_print = print
    _ut.ProcessManager = type("ProcessManager", (), {})
    _ut.is_port_active = lambda port: False
    _ut.kill_process_by_name = lambda *a: None
    _ut.kill_process_by_port = lambda *a: None
    sys.modules["utils"] = _ut

# Now try to load server.py (it depends on handlers + config_system + utils)
_fqn_srv = "zena_mode.server"
if _fqn_srv not in sys.modules:
    _spec_srv = _ilu.spec_from_file_location(
        _fqn_srv, str(ROOT / "zena_mode" / "server.py")
    )
    if _spec_srv and _spec_srv.loader:
        _mod_srv = _ilu.module_from_spec(_spec_srv)
        _mod_srv.__package__ = "zena_mode"
        sys.modules[_fqn_srv] = _mod_srv
        setattr(sys.modules["zena_mode"], "server", _mod_srv)
        try:
            _spec_srv.loader.exec_module(_mod_srv)
        except Exception:
            pass  # partial load is fine, tests can detect missing attrs


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
            "data: [DONE]\n\n",
        ]
        respx_mock.post("/v1/chat/completions").mock(return_value=httpx.Response(200, content="".join(stream_content)))

        yield respx_mock


@pytest.fixture
def mock_hub_api():
    """Fixture to mock Hub API responses (8002)."""
    with respx.mock(base_url="http://127.0.0.1:8002", assert_all_called=False) as respx_mock:
        respx_mock.get("/models/available").mock(
            return_value=httpx.Response(200, json=["mock-model-1.gguf", "mock-model-2.gguf"])
        )
        respx_mock.post("/models/load").mock(return_value=httpx.Response(200, json={"status": "loaded"}))
        respx_mock.post("/models/download").mock(return_value=httpx.Response(200, json={"status": "started"}))

        yield respx_mock


class _SimpleExpertHandler(BaseHTTPRequestHandler):
    """_SimpleExpertHandler class."""

    def do_GET(self):
        """Do get."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


class _HubHandler(BaseHTTPRequestHandler):
    """_HubHandler class."""

    # Shared state will be injected by the fixture
    servers: Dict[int, HTTPServer] = {}

    def do_POST(self):
        """Do post."""
        if self.path == "/swarm/scale":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                count = int(data.get("count", 0))
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
                server = HTTPServer(("127.0.0.1", port), _SimpleExpertHandler)
                t = threading.Thread(target=server.serve_forever, daemon=True)
                t.start()
                _HubHandler.servers[port] = server
                started.append(port)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {"status": "scaled", "ports": started}
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        """Do get."""
        if self.path == "/swarm/list":
            ports = list(_HubHandler.servers.keys())
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ports": ports}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


@pytest.fixture(scope="session", autouse=True)
def hub_server():
    """Start a lightweight Hub on 127.0.0.1:8002 that can scale experts for integration tests."""
    # Ensure config flags used by SwarmArbitrator are enabled during tests
    try:
        from config_system import config

        config.swarm_enabled = True
        config.swarm_size = 7
        # Also set uppercase aliases for backward compatibility
        config.SWARM_ENABLED = True
        config.SWARM_SIZE = 7
    except Exception:
        pass

    hub = HTTPServer(("127.0.0.1", 8002), _HubHandler)
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
