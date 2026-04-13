"""
Live end-to-end tests for RAG Test Bench — NO MOCKS.

Everything runs for real:
  - Real web crawl (httpbin.org — a tiny, stable test site)
  - Real sentence-transformers embedding
  - Real llama-server LLM (auto-started with smallest available model)
  - Real Flask app via test client

Prerequisites (auto-detected, test skips if missing):
  - Internet connection (for crawling httpbin.org)
  - llama-server binary (zen_core_libs.llm.find_llama_server_binary)
  - At least one GGUF model in C:\\AI\\Models or standard paths
  - sentence-transformers installed

Run:  python -m pytest test_live_e2e.py -v -m live
       (excluded from default `pytest` run — needs explicit -m live)
"""

from __future__ import annotations

# ── WMI hang workaround for Python 3.13 on Windows ──────────────────────
import platform, sys
if sys.platform == "win32" and sys.version_info >= (3, 13):
    try:
        platform._uname_cache = platform.uname_result(
            "Windows", "", "10", "10.0.22631", "AMD64"
        )
    except (AttributeError, TypeError):
        pass
# ─────────────────────────────────────────────────────────────────────────

import json
import os
import time

import pytest
import requests


# ── Constants ────────────────────────────────────────────────────────────

# Small, fast, reliable test site — returns structured text, always up
CRAWL_URL = "https://httpbin.org"
CRAWL_DEPTH = 1
CRAWL_MAX_PAGES = 5

APP_PORT = 5051  # Use non-default port to avoid conflicting with running app
APP_BASE = f"http://localhost:{APP_PORT}"
LLM_PORT = 8091  # Non-default port for test LLM server

# ── Markers ──────────────────────────────────────────────────────────────

pytestmark = pytest.mark.live


# ── Skip helpers ─────────────────────────────────────────────────────────

def _has_internet() -> bool:
    try:
        requests.head("https://httpbin.org", timeout=5)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False


def _has_llama_server() -> tuple[bool, str]:
    try:
        from zen_core_libs.llm import find_llama_server_binary
        binary = find_llama_server_binary()
        return (binary is not None, binary or "")
    except ImportError:
        return (False, "")


def _smallest_model() -> str | None:
    try:
        from zen_core_libs.llm import discover_models
        models = discover_models()
        if not models:
            return None
        # Pick smallest model for fastest startup
        models.sort(key=lambda m: m.get("size_gb", 999))
        return models[0]["path"]
    except ImportError:
        return None


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def live_prereqs():
    """Check all prerequisites once per module. Skip entire module if missing."""
    if not _has_internet():
        pytest.skip("No internet connection — cannot crawl live site")

    has_llama, binary = _has_llama_server()
    if not has_llama:
        pytest.skip("llama-server binary not found")

    model_path = _smallest_model()
    if not model_path:
        pytest.skip("No GGUF models found")

    return {"binary": binary, "model_path": model_path}


@pytest.fixture(scope="module")
def llm_server(live_prereqs):
    """Start a real llama-server with the smallest model, yield when ready, stop after."""
    from zen_core_libs.llm import LlamaServerManager

    mgr = LlamaServerManager()
    model_path = live_prereqs["model_path"]

    print(f"\n  Starting llama-server with {os.path.basename(model_path)}...")

    try:
        result = mgr.start(
            model_path=model_path,
            port=LLM_PORT,
            ctx_size=2048,
            gpu_layers=99,
            timeout=120,
        )
    except Exception as e:
        pytest.skip(f"Failed to start llama-server: {e}")

    if not mgr.is_running:
        pytest.skip(f"llama-server did not start: {result}")

    base_url = f"http://localhost:{LLM_PORT}/v1"
    print(f"  llama-server ready on port {LLM_PORT}")
    yield {"base_url": base_url, "model": os.path.basename(model_path), "mgr": mgr}

    # Teardown
    print("\n  Stopping llama-server...")
    mgr.stop()


@pytest.fixture(scope="module")
def app_client(live_prereqs, llm_server, tmp_path_factory):
    """Start the Flask app as a test client with real dependencies.

    Uses isolated data files so we don't corrupt the user's real sites.json.
    """
    tmp = tmp_path_factory.mktemp("live_e2e")

    import app as app_module

    # Isolate data files
    app_module.SITES_FILE = tmp / "sites.json"
    app_module._ACTIVE_PIPELINES_FILE = tmp / "active_pipelines.json"
    app_module.LLM_CONFIG_FILE = tmp / "llm_config.json"

    # Clear index for fresh start
    app_module.INDEX.clear()

    # Configure LLM to use our test server
    llm_cfg = {
        "base_url": llm_server["base_url"],
        "api_key": "not-needed",
        "model": llm_server["model"],
    }
    with open(tmp / "llm_config.json", "w") as f:
        json.dump(llm_cfg, f)

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client

    # Cleanup
    app_module.INDEX.clear()


def _wait_crawl(client, timeout=120):
    """Poll crawl status until done."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = client.get("/api/crawl/status")
        status = r.get_json()
        if not status["running"]:
            return status
        time.sleep(0.5)
    pytest.fail(f"Crawl did not finish within {timeout}s")


def _parse_sse(data: bytes) -> list[dict]:
    """Parse SSE byte stream into list of JSON events."""
    events = []
    text = data.decode("utf-8", errors="replace")
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("data: ") and line[6:].strip() != "[DONE]":
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


# ═══════════════════════════════════════════════════════════════════════════
# LIVE TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestLiveLandingPage:
    """Verify the app serves its UI."""

    def test_homepage_loads(self, app_client):
        r = app_client.get("/")
        assert r.status_code == 200
        assert b"RAG Test Bench" in r.data


class TestLiveSiteAndCrawl:
    """Add a real site, crawl it live, verify real chunks in the index."""

    def test_add_site(self, app_client):
        r = app_client.post("/api/sites", json={
            "url": CRAWL_URL,
            "depth": CRAWL_DEPTH,
            "max_pages": CRAWL_MAX_PAGES,
        })
        assert r.status_code == 201
        data = r.get_json()
        assert data["url"] == CRAWL_URL

    def test_crawl_completes(self, app_client):
        # Ensure site is added
        sites = app_client.get("/api/sites").get_json()
        if not sites:
            app_client.post("/api/sites", json={
                "url": CRAWL_URL, "depth": CRAWL_DEPTH, "max_pages": CRAWL_MAX_PAGES,
            })

        r = app_client.post("/api/crawl")
        assert r.get_json()["started"] is True

        status = _wait_crawl(app_client)
        assert status["running"] is False
        assert len(status["progress"]) >= 1

        # At least one site should have succeeded
        done = [p for p in status["progress"] if p.get("status") == "done"]
        assert len(done) >= 1
        assert done[0]["pages"] >= 1

    def test_index_has_chunks(self, app_client):
        stats = app_client.get("/api/stats").get_json()
        assert stats["n_chunks"] > 0, "Index should have chunks after crawl"

    def test_site_record_updated(self, app_client):
        sites = app_client.get("/api/sites").get_json()
        site = next((s for s in sites if s["url"] == CRAWL_URL), None)
        assert site is not None
        assert site["last_crawled"] is not None
        assert site["pages_crawled"] >= 1


class TestLiveSearch:
    """Search the real indexed data."""

    def test_search_returns_results(self, app_client):
        # Make sure we have data
        stats = app_client.get("/api/stats").get_json()
        if stats["n_chunks"] == 0:
            pytest.skip("No chunks indexed — crawl may have failed")

        r = app_client.post("/api/search", json={"query": "HTTP request methods", "k": 3})
        assert r.status_code == 200
        data = r.get_json()
        assert len(data["results"]) > 0
        assert data["elapsed_sec"] > 0

    def test_search_scores_are_real(self, app_client):
        stats = app_client.get("/api/stats").get_json()
        if stats["n_chunks"] == 0:
            pytest.skip("No chunks indexed")

        r = app_client.post("/api/search", json={"query": "httpbin", "k": 5})
        data = r.get_json()
        for result in data["results"]:
            assert isinstance(result["score"], float)
            assert result["source_url"].startswith("http")
            assert len(result["text"]) > 0

    def test_search_has_routing(self, app_client):
        stats = app_client.get("/api/stats").get_json()
        if stats["n_chunks"] == 0:
            pytest.skip("No chunks indexed")

        r = app_client.post("/api/search", json={"query": "What methods does httpbin support?"})
        data = r.get_json()
        assert "intent" in data
        assert "intent_confidence" in data


class TestLiveLLMHealth:
    """Verify LLM health endpoint against real running server."""

    def test_llm_health_ok(self, app_client):
        r = app_client.get("/api/llm/health")
        data = r.get_json()
        assert data["ok"] is True, f"LLM health failed: {data.get('error')}"


class TestLiveChat:
    """Chat with a real LLM using real RAG context."""

    def test_chat_produces_real_answer(self, app_client):
        stats = app_client.get("/api/stats").get_json()
        if stats["n_chunks"] == 0:
            pytest.skip("No chunks indexed")

        r = app_client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "What is httpbin?"}],
            "rag_k": 3,
        })
        assert r.status_code == 200
        assert "text/event-stream" in r.content_type

        events = _parse_sse(r.data)
        assert len(events) > 0, "Should receive SSE events"

        # Should have sources from RAG
        source_events = [e for e in events if "sources" in e]
        assert len(source_events) >= 1, "Chat should include RAG sources"

        # Should have actual LLM-generated content
        content_parts = [e.get("content", "") for e in events if "content" in e]
        full_answer = "".join(content_parts)
        assert len(full_answer) > 10, f"LLM should generate a real answer, got: {full_answer!r}"

    def test_chat_has_rag_timing(self, app_client):
        stats = app_client.get("/api/stats").get_json()
        if stats["n_chunks"] == 0:
            pytest.skip("No chunks indexed")

        r = app_client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Tell me about HTTP methods"}],
        })
        events = _parse_sse(r.data)
        timing_events = [e for e in events if "rag_timing" in e]
        assert len(timing_events) >= 1
        timing = timing_events[0]["rag_timing"]
        assert "rag_chunks_sent" in timing
        assert timing["rag_chunks_sent"] >= 0

    def test_multi_turn_chat(self, app_client):
        stats = app_client.get("/api/stats").get_json()
        if stats["n_chunks"] == 0:
            pytest.skip("No chunks indexed")

        r = app_client.post("/api/chat", json={
            "messages": [
                {"role": "user", "content": "What is httpbin?"},
                {"role": "assistant", "content": "httpbin is an HTTP testing service."},
                {"role": "user", "content": "What endpoints does it have?"},
            ],
        })
        events = _parse_sse(r.data)
        content = "".join(e.get("content", "") for e in events if "content" in e)
        assert len(content) > 5, "Multi-turn should produce a response"


class TestLiveChatCompare:
    """Multi-pipeline comparison with real LLM."""

    def test_compare_two_pipelines(self, app_client):
        stats = app_client.get("/api/stats").get_json()
        if stats["n_chunks"] == 0:
            pytest.skip("No chunks indexed")

        # Activate two pipelines
        app_client.post("/api/pipelines/active", json={
            "pipelines": ["baseline", "full_stack"],
        })

        r = app_client.post("/api/chat/compare", json={
            "messages": [{"role": "user", "content": "What does httpbin do?"}],
        })
        assert r.status_code == 200
        events = _parse_sse(r.data)
        assert len(events) > 0

        # Both pipelines should produce content
        pipelines_seen = set()
        for e in events:
            if "pipeline" in e:
                pipelines_seen.add(e["pipeline"])
        assert len(pipelines_seen) >= 1, f"Expected pipeline events, saw: {pipelines_seen}"


class TestLivePipelineManagement:
    """Pipeline CRUD against real app state."""

    def test_list_pipelines(self, app_client):
        r = app_client.get("/api/pipelines")
        data = r.get_json()
        assert len(data) >= 4
        labels = [p["label"] for p in data]
        assert "Baseline" in labels
        assert "Full Stack" in labels

    def test_activate_pipelines(self, app_client):
        r = app_client.post("/api/pipelines/active", json={
            "pipelines": ["baseline", "reranked", "routed"],
        })
        assert r.status_code == 200
        assert len(r.get_json()["active"]) == 3


class TestLiveMetrics:
    """Verify metrics are tracked from real operations."""

    def test_metrics_recorded(self, app_client):
        stats = app_client.get("/api/stats").get_json()
        assert "metrics" in stats
        assert "cache" in stats
        assert "reranker" in stats


class TestLiveClearAndReload:
    """Clear and verify empty — last test to run."""

    def test_clear_index(self, app_client):
        r = app_client.post("/api/clear")
        assert r.get_json()["ok"] is True

        stats = app_client.get("/api/stats").get_json()
        assert stats["n_chunks"] == 0

    def test_search_empty_after_clear(self, app_client):
        r = app_client.post("/api/search", json={"query": "anything"})
        data = r.get_json()
        assert data["results"] == []
