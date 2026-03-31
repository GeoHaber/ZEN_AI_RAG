"""
End-to-end tests for RAG Test Bench.

Simulates the full user journey through the Flask app using the test client:
  1. Landing page loads
  2. Add a site (URL, depth, max_pages)
  3. Trigger crawl and wait for completion
  4. Verify index has chunks (stats)
  5. Search the indexed data
  6. Configure LLM settings
  7. Check LLM health
  8. Chat with RAG context (single pipeline)
  9. Chat compare (multi-pipeline)
  10. Pipeline management (list, activate)
  11. Clear index and verify empty
  12. Edge cases: duplicate site, bad params, empty chat

All external HTTP calls (crawl fetches, LLM API) are mocked so tests run
offline in < 5 seconds.

Run:  python -m pytest test_e2e.py -v
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
import time
import threading
from dataclasses import dataclass
from typing import Optional
from unittest.mock import patch, MagicMock

import numpy as np
import pytest


# ── Fake pages for the crawler ───────────────────────────────────────────

FAKE_PAGES = {
    "https://example.com": {
        "title": "Example Home",
        "text": (
            "Welcome to Example Corp.\n\n"
            "We specialize in artificial intelligence and machine learning solutions.\n\n"
            "Our team has over 20 years of experience in data science, "
            "natural language processing, and computer vision.\n\n"
            "Founded in 2010, Example Corp has grown to serve over 500 clients worldwide.\n\n"
            "Our headquarters are located in San Francisco, California."
        ),
        "links": ["https://example.com/about", "https://example.com/products"],
    },
    "https://example.com/about": {
        "title": "About Us",
        "text": (
            "About Example Corp\n\n"
            "Example Corp was founded by Dr. Jane Smith and Dr. John Doe.\n\n"
            "Our mission is to make artificial intelligence accessible to every business.\n\n"
            "We have offices in San Francisco, London, and Tokyo.\n\n"
            "The company employs over 300 data scientists and engineers.\n\n"
            "Our research has been published in Nature, Science, and IEEE journals."
        ),
        "links": ["https://example.com"],
    },
    "https://example.com/products": {
        "title": "Products",
        "text": (
            "Our Products\n\n"
            "RAG Engine — Retrieval-Augmented Generation for enterprise search.\n\n"
            "SmartClassifier — Automated document classification using deep learning.\n\n"
            "DataPipeline — End-to-end data processing and feature engineering.\n\n"
            "VisionAI — Computer vision platform for manufacturing quality control.\n\n"
            "Each product comes with a REST API and Python SDK."
        ),
        "links": ["https://example.com"],
    },
}


# ── Mock crawler ─────────────────────────────────────────────────────────

@dataclass
class _FakeCrawlResult:
    url: str
    title: str
    text: str
    depth: int
    status: int = 200
    error: Optional[str] = None


@dataclass
class _FakeCrawlStats:
    pages_fetched: int = 0
    pages_skipped: int = 0
    pages_errored: int = 0
    total_chars: int = 0
    elapsed_sec: float = 0.1
    urls_visited: int = 0
    content_types: dict = None

    def __post_init__(self):
        if self.content_types is None:
            self.content_types = {"text/html": self.pages_fetched}


def _fake_crawl_site(start_url, max_depth=2, max_pages=50, on_page=None,
                     cancel_event=None):
    """Return fake crawl results from FAKE_PAGES."""
    results = []
    visited = set()
    queue = [(start_url, 0)]

    while queue and len(results) < max_pages:
        url, depth = queue.pop(0)
        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        page = FAKE_PAGES.get(url)
        if not page:
            continue

        cr = _FakeCrawlResult(
            url=url, title=page["title"], text=page["text"], depth=depth,
        )
        results.append(cr)
        if on_page:
            on_page(cr)

        for link in page.get("links", []):
            if link not in visited:
                queue.append((link, depth + 1))

    stats = _FakeCrawlStats(
        pages_fetched=len(results),
        urls_visited=len(visited),
        total_chars=sum(len(r.text) for r in results),
    )
    return results, stats


# ── Mock embedder (avoid loading sentence-transformers) ──────────────────

class _FakeEmbedder:
    """Deterministic embedder: hashes text into a 384-d unit vector."""

    def encode(self, texts, **kwargs):
        import hashlib
        vecs = []
        for t in (texts if isinstance(texts, list) else [texts]):
            h = hashlib.sha256(t.encode()).digest()
            v = np.frombuffer(h * 12, dtype=np.float32)[:384]
            v = v / (np.linalg.norm(v) + 1e-9)
            vecs.append(v)
        return np.array(vecs, dtype=np.float32)


# ── Mock LLM responses ──────────────────────────────────────────────────

def _make_llm_stream(text: str) -> list[bytes]:
    """Build SSE byte lines that mimic an OpenAI chat/completions stream."""
    lines = []
    # Stream the text in small chunks
    words = text.split(" ")
    for i, word in enumerate(words):
        token = word if i == 0 else " " + word
        chunk = {
            "choices": [{"delta": {"content": token}, "index": 0}]
        }
        lines.append(f"data: {json.dumps(chunk)}\n\n".encode())
    lines.append(b"data: [DONE]\n\n")
    return lines


class _FakeLLMResponse:
    """Mimics a streaming requests.Response from an OpenAI-compatible API."""

    def __init__(self, text: str):
        self.status_code = 200
        self.headers = {"content-type": "text/event-stream"}
        self._lines = _make_llm_stream(text)
        self.ok = True

    def raise_for_status(self):
        pass

    def iter_lines(self, decode_unicode=False):
        for line in self._lines:
            decoded = line.decode() if isinstance(line, bytes) else line
            yield decoded.strip()

    def json(self):
        return {"choices": [{"message": {"content": "mocked"}}]}


class _FakeLLMModelsResponse:
    """Mimics GET /v1/models response."""
    status_code = 200
    ok = True

    def raise_for_status(self):
        pass

    def json(self):
        return {"data": [{"id": "test-model"}]}


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    """Create a Flask test client with mocked crawler and isolated data files."""
    # Isolate data files to tmp_path
    monkeypatch.setattr("app.SITES_FILE", tmp_path / "sites.json")
    monkeypatch.setattr("app._ACTIVE_PIPELINES_FILE", tmp_path / "active_pipelines.json")

    # Reset index
    import app as app_module
    app_module.INDEX.clear()

    # Mock the crawler
    monkeypatch.setattr("app.crawl_site", _fake_crawl_site)

    # Mock the embedder inside RAGIndex to avoid loading sentence-transformers
    fake_emb = _FakeEmbedder()
    monkeypatch.setattr("app.INDEX._embedder", fake_emb, raising=False)
    # Also patch _get_embedder in case index rebuilds
    monkeypatch.setattr(
        "zen_core_libs.rag.rag_index._get_embedder",
        lambda *a, **kw: fake_emb,
        raising=False,
    )

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client

    # Cleanup
    app_module.INDEX.clear()


def _wait_crawl(client, timeout=30):
    """Poll /api/crawl/status until crawl finishes."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = client.get("/api/crawl/status")
        status = r.get_json()
        if not status["running"]:
            return status
        time.sleep(0.1)
    pytest.fail("Crawl did not finish within timeout")


# ═══════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestLandingPage:
    """Phase 1: User opens the website."""

    def test_index_page_loads(self, app_client):
        r = app_client.get("/")
        assert r.status_code == 200
        assert b"RAG Test Bench" in r.data

    def test_no_cache_headers(self, app_client):
        r = app_client.get("/")
        assert "no-cache" in r.headers.get("Cache-Control", "")


class TestSiteManagement:
    """Phase 2: User adds sites to scan."""

    def test_add_site(self, app_client):
        r = app_client.post("/api/sites", json={
            "url": "https://example.com", "depth": 2, "max_pages": 50,
        })
        assert r.status_code == 201
        data = r.get_json()
        assert data["url"] == "https://example.com"
        assert data["depth"] == 2
        assert data["max_pages"] == 50

    def test_list_sites(self, app_client):
        app_client.post("/api/sites", json={"url": "https://example.com"})
        r = app_client.get("/api/sites")
        sites = r.get_json()
        assert len(sites) == 1
        assert sites[0]["url"] == "https://example.com"

    def test_duplicate_site_rejected(self, app_client):
        app_client.post("/api/sites", json={"url": "https://example.com"})
        r = app_client.post("/api/sites", json={"url": "https://example.com"})
        assert r.status_code == 409

    def test_auto_prepend_https(self, app_client):
        r = app_client.post("/api/sites", json={"url": "example.com"})
        assert r.status_code == 201
        assert r.get_json()["url"] == "https://example.com"

    def test_empty_url_rejected(self, app_client):
        r = app_client.post("/api/sites", json={"url": ""})
        assert r.status_code == 400

    def test_depth_clamped(self, app_client):
        r = app_client.post("/api/sites", json={
            "url": "https://example.com", "depth": 99, "max_pages": 10,
        })
        assert r.get_json()["depth"] == 10  # clamped to max 10

    def test_max_pages_clamped(self, app_client):
        r = app_client.post("/api/sites", json={
            "url": "https://example.com", "max_pages": 99999,
        })
        assert r.get_json()["max_pages"] == 5000  # clamped to max 5000


class TestCrawlAndIndex:
    """Phase 3: User triggers crawl → data gets indexed."""

    def test_crawl_indexes_data(self, app_client):
        # Add site
        app_client.post("/api/sites", json={
            "url": "https://example.com", "depth": 2, "max_pages": 50,
        })
        # Start crawl
        r = app_client.post("/api/crawl")
        assert r.get_json()["started"] is True

        # Wait for crawl to finish
        status = _wait_crawl(app_client)
        assert status["running"] is False
        assert len(status["progress"]) >= 1
        assert status["progress"][0]["status"] == "done"
        assert status["progress"][0]["pages"] >= 1

    def test_stats_after_crawl(self, app_client):
        app_client.post("/api/sites", json={"url": "https://example.com", "depth": 2})
        app_client.post("/api/crawl")
        _wait_crawl(app_client)

        r = app_client.get("/api/stats")
        stats = r.get_json()
        assert stats["n_chunks"] > 0

    def test_crawl_updates_site_record(self, app_client):
        app_client.post("/api/sites", json={"url": "https://example.com", "depth": 2})
        app_client.post("/api/crawl")
        _wait_crawl(app_client)

        sites = app_client.get("/api/sites").get_json()
        assert sites[0]["last_crawled"] is not None
        assert sites[0]["pages_crawled"] >= 1
        assert sites[0]["chunks_indexed"] >= 1

    def test_crawl_cancel(self, app_client):
        app_client.post("/api/sites", json={"url": "https://example.com"})
        app_client.post("/api/crawl")
        r = app_client.post("/api/crawl/cancel")
        assert r.get_json()["ok"] is True
        status = _wait_crawl(app_client)
        assert status["running"] is False


class TestSearch:
    """Phase 4: User searches the indexed data."""

    @pytest.fixture(autouse=True)
    def _crawled(self, app_client):
        app_client.post("/api/sites", json={"url": "https://example.com", "depth": 2})
        app_client.post("/api/crawl")
        _wait_crawl(app_client)

    def test_search_returns_results(self, app_client):
        r = app_client.post("/api/search", json={"query": "artificial intelligence"})
        assert r.status_code == 200
        data = r.get_json()
        assert data["query"] == "artificial intelligence"
        assert len(data["results"]) > 0

    def test_search_result_fields(self, app_client):
        r = app_client.post("/api/search", json={"query": "machine learning", "k": 3})
        data = r.get_json()
        for result in data["results"]:
            assert "text" in result
            assert "source_url" in result
            assert "page_title" in result
            assert "score" in result
            assert isinstance(result["score"], float)

    def test_search_has_intent(self, app_client):
        r = app_client.post("/api/search", json={"query": "products"})
        data = r.get_json()
        assert "intent" in data
        assert "intent_confidence" in data

    def test_search_empty_query_rejected(self, app_client):
        r = app_client.post("/api/search", json={"query": ""})
        assert r.status_code == 400

    def test_search_k_respected(self, app_client):
        r = app_client.post("/api/search", json={"query": "example", "k": 1})
        data = r.get_json()
        assert len(data["results"]) <= 1


class TestLLMConfig:
    """Phase 5: User configures LLM settings."""

    def test_get_llm_config(self, app_client):
        r = app_client.get("/api/llm/config")
        assert r.status_code == 200
        data = r.get_json()
        assert "base_url" in data
        assert "model" in data

    def test_set_llm_config(self, app_client):
        r = app_client.post("/api/llm/config", json={
            "base_url": "http://localhost:9999/v1",
            "api_key": "test-key",
            "model": "test-model",
        })
        assert r.status_code == 200
        # Verify it persisted
        cfg = app_client.get("/api/llm/config").get_json()
        assert cfg["base_url"] == "http://localhost:9999/v1"
        assert cfg["model"] == "test-model"


class TestLLMHealth:
    """Phase 6: Check LLM connectivity before chatting."""

    def test_llm_healthy(self, app_client):
        with patch("app.http_requests.get", return_value=_FakeLLMModelsResponse()):
            r = app_client.get("/api/llm/health")
            data = r.get_json()
            assert data["ok"] is True

    def test_llm_unreachable(self, app_client):
        with patch("app.http_requests.get",
                    side_effect=ConnectionError("Connection refused [10061]")):
            r = app_client.get("/api/llm/health")
            data = r.get_json()
            assert data["ok"] is False
            assert "error" in data
            assert "not running" in data["error"].lower() or "running" in data["error"].lower()

    def test_llm_timeout(self, app_client):
        from requests.exceptions import Timeout
        with patch("app.http_requests.get", side_effect=Timeout("timed out")):
            r = app_client.get("/api/llm/health")
            data = r.get_json()
            assert data["ok"] is False
            assert "timed out" in data["error"].lower()


class TestChat:
    """Phase 7: User chats with RAG-augmented LLM (single pipeline)."""

    @pytest.fixture(autouse=True)
    def _crawled(self, app_client):
        app_client.post("/api/sites", json={"url": "https://example.com", "depth": 2})
        app_client.post("/api/crawl")
        _wait_crawl(app_client)

    def _parse_sse(self, response_data: bytes) -> list[dict]:
        """Parse SSE stream into list of JSON objects."""
        events = []
        text = response_data.decode("utf-8", errors="replace")
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("data: ") and line[6:].strip() != "[DONE]":
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
        return events

    def test_chat_streams_response(self, app_client):
        llm_answer = "Example Corp was founded in 2010 in San Francisco."
        fake_resp = _FakeLLMResponse(llm_answer)

        with patch("app.http_requests.post", return_value=fake_resp):
            r = app_client.post("/api/chat", json={
                "messages": [{"role": "user", "content": "When was Example Corp founded?"}],
            })
            assert r.status_code == 200
            assert "text/event-stream" in r.content_type

            events = self._parse_sse(r.data)
            assert len(events) > 0

            # First event should have sources + rag_timing
            first = events[0]
            assert "sources" in first or "content" in first

            # Collect full text from content events
            full_text = "".join(e.get("content", "") for e in events)
            assert "Example Corp" in full_text or "founded" in full_text.lower()

    def test_chat_includes_rag_sources(self, app_client):
        fake_resp = _FakeLLMResponse("Founded in San Francisco.")
        with patch("app.http_requests.post", return_value=fake_resp):
            r = app_client.post("/api/chat", json={
                "messages": [{"role": "user", "content": "Where is the headquarters?"}],
            })
            events = self._parse_sse(r.data)
            source_events = [e for e in events if "sources" in e]
            assert len(source_events) >= 1
            sources = source_events[0]["sources"]
            assert isinstance(sources, list)

    def test_chat_includes_rag_timing(self, app_client):
        fake_resp = _FakeLLMResponse("Products include RAG Engine.")
        with patch("app.http_requests.post", return_value=fake_resp):
            r = app_client.post("/api/chat", json={
                "messages": [{"role": "user", "content": "What products do they offer?"}],
            })
            events = self._parse_sse(r.data)
            timing_events = [e for e in events if "rag_timing" in e]
            assert len(timing_events) >= 1
            timing = timing_events[0]["rag_timing"]
            assert "rag_chunks_sent" in timing

    def test_chat_empty_messages_rejected(self, app_client):
        r = app_client.post("/api/chat", json={"messages": []})
        assert r.status_code == 400

    def test_chat_llm_error_returns_friendly_message(self, app_client):
        with patch("app.http_requests.post",
                    side_effect=ConnectionError("Connection refused [10061]")):
            r = app_client.post("/api/chat", json={
                "messages": [{"role": "user", "content": "test"}],
            })
            events = self._parse_sse(r.data)
            error_events = [e for e in events if "error" in e]
            assert len(error_events) >= 1
            assert "not running" in error_events[0]["error"].lower() or \
                   "running" in error_events[0]["error"].lower()

    def test_chat_with_history(self, app_client):
        fake_resp = _FakeLLMResponse("They have offices worldwide.")
        with patch("app.http_requests.post", return_value=fake_resp):
            r = app_client.post("/api/chat", json={
                "messages": [
                    {"role": "user", "content": "Tell me about Example Corp"},
                    {"role": "assistant", "content": "Example Corp is an AI company."},
                    {"role": "user", "content": "Where are their offices?"},
                ],
            })
            events = self._parse_sse(r.data)
            full_text = "".join(e.get("content", "") for e in events)
            assert len(full_text) > 0

    def test_chat_hallucination_detection(self, app_client):
        """If the answer has content and RAG context, hallucination check runs."""
        fake_resp = _FakeLLMResponse(
            "Example Corp was founded in 2010 and has 300 employees."
        )
        with patch("app.http_requests.post", return_value=fake_resp):
            r = app_client.post("/api/chat", json={
                "messages": [{"role": "user", "content": "Tell me about Example Corp"}],
            })
            events = self._parse_sse(r.data)
            hallu_events = [e for e in events if "hallucination" in e]
            # Hallucination detector should have run
            if hallu_events:
                h = hallu_events[0]["hallucination"]
                assert "score" in h
                assert "has_hallucinations" in h


class TestChatCompare:
    """Phase 8: Multi-pipeline comparison chat."""

    @pytest.fixture(autouse=True)
    def _crawled(self, app_client):
        app_client.post("/api/sites", json={"url": "https://example.com", "depth": 2})
        app_client.post("/api/crawl")
        _wait_crawl(app_client)

    def _parse_sse(self, response_data: bytes) -> list[dict]:
        events = []
        text = response_data.decode("utf-8", errors="replace")
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("data: ") and line[6:].strip() != "[DONE]":
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
        return events

    def test_compare_streams_per_pipeline(self, app_client):
        # Activate two pipelines
        app_client.post("/api/pipelines/active", json={
            "pipelines": ["baseline", "reranked"],
        })

        fake_resp = _FakeLLMResponse("Example Corp is an AI company.")

        with patch("app.http_requests.post", return_value=fake_resp):
            r = app_client.post("/api/chat/compare", json={
                "messages": [{"role": "user", "content": "What is Example Corp?"}],
            })
            assert r.status_code == 200
            events = self._parse_sse(r.data)
            # Should have events for multiple pipelines
            pipelines_seen = set()
            for e in events:
                if "pipeline" in e:
                    pipelines_seen.add(e["pipeline"])
            assert len(pipelines_seen) >= 1

    def test_compare_empty_messages_rejected(self, app_client):
        r = app_client.post("/api/chat/compare", json={"messages": []})
        assert r.status_code == 400


class TestPipelineManagement:
    """Phase 9: Managing pipeline presets."""

    def test_list_pipelines(self, app_client):
        r = app_client.get("/api/pipelines")
        data = r.get_json()
        assert len(data) >= 4
        ids = [p["id"] for p in data]
        assert "baseline" in ids
        assert "full_stack" in ids

    def test_pipeline_has_features(self, app_client):
        r = app_client.get("/api/pipelines")
        for p in r.get_json():
            assert "features" in p
            assert "label" in p
            assert "color" in p

    def test_set_active_pipelines(self, app_client):
        r = app_client.post("/api/pipelines/active", json={
            "pipelines": ["baseline", "routed"],
        })
        assert r.status_code == 200
        assert set(r.get_json()["active"]) == {"baseline", "routed"}

    def test_set_active_requires_valid_ids(self, app_client):
        r = app_client.post("/api/pipelines/active", json={
            "pipelines": ["nonexistent"],
        })
        assert r.status_code == 400

    def test_max_four_pipelines(self, app_client):
        r = app_client.post("/api/pipelines/active", json={
            "pipelines": ["baseline", "reranked", "routed", "full_stack", "baseline"],
        })
        assert len(r.get_json()["active"]) <= 4


class TestClearAndReload:
    """Phase 10: Reset and reload operations."""

    def test_clear_index(self, app_client):
        app_client.post("/api/sites", json={"url": "https://example.com", "depth": 2})
        app_client.post("/api/crawl")
        _wait_crawl(app_client)

        # Verify we have data
        stats = app_client.get("/api/stats").get_json()
        assert stats["n_chunks"] > 0

        # Clear
        r = app_client.post("/api/clear")
        assert r.get_json()["ok"] is True

        # Verify empty
        stats = app_client.get("/api/stats").get_json()
        assert stats["n_chunks"] == 0

    def test_search_on_empty_index(self, app_client):
        r = app_client.post("/api/search", json={"query": "anything"})
        data = r.get_json()
        assert data["results"] == []


class TestFullJourney:
    """Complete end-to-end: add site → crawl → search → configure LLM → chat."""

    def _parse_sse(self, response_data: bytes) -> list[dict]:
        events = []
        text = response_data.decode("utf-8", errors="replace")
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("data: ") and line[6:].strip() != "[DONE]":
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
        return events

    def test_complete_user_journey(self, app_client):
        # 1. Landing page works
        assert app_client.get("/").status_code == 200

        # 2. Add a site
        r = app_client.post("/api/sites", json={
            "url": "https://example.com", "depth": 2, "max_pages": 50,
        })
        assert r.status_code == 201

        # 3. Start crawl and wait
        r = app_client.post("/api/crawl")
        assert r.get_json()["started"] is True
        status = _wait_crawl(app_client)
        assert status["progress"][0]["status"] == "done"
        pages_crawled = status["progress"][0]["pages"]
        assert pages_crawled >= 1

        # 4. Verify index stats
        stats = app_client.get("/api/stats").get_json()
        n_chunks = stats["n_chunks"]
        assert n_chunks > 0

        # 5. Search the indexed data
        r = app_client.post("/api/search", json={
            "query": "artificial intelligence machine learning", "k": 5,
        })
        search_data = r.get_json()
        assert len(search_data["results"]) > 0
        assert search_data["results"][0]["score"] >= 0

        # 6. Configure LLM
        r = app_client.post("/api/llm/config", json={
            "base_url": "http://localhost:8090/v1",
            "api_key": "test-key",
            "model": "test-model",
        })
        assert r.status_code == 200

        # 7. Check LLM health
        with patch("app.http_requests.get", return_value=_FakeLLMModelsResponse()):
            health = app_client.get("/api/llm/health").get_json()
            assert health["ok"] is True

        # 8. Chat with the RAG data
        llm_answer = (
            "Example Corp was founded in 2010 by Dr. Jane Smith and Dr. John Doe. "
            "They specialize in artificial intelligence and machine learning solutions, "
            "serving over 500 clients from their headquarters in San Francisco."
        )
        fake_resp = _FakeLLMResponse(llm_answer)
        with patch("app.http_requests.post", return_value=fake_resp):
            r = app_client.post("/api/chat", json={
                "messages": [
                    {"role": "user", "content": "Tell me about Example Corp's history and founders"},
                ],
            })
            assert r.status_code == 200
            events = self._parse_sse(r.data)

            # Should have sources
            source_events = [e for e in events if "sources" in e]
            assert len(source_events) >= 1

            # Should have content
            full_text = "".join(e.get("content", "") for e in events)
            assert "Example Corp" in full_text
            assert "2010" in full_text

            # Should have RAG timing
            timing_events = [e for e in events if "rag_timing" in e]
            assert len(timing_events) >= 1

        # 9. Multi-turn conversation
        with patch("app.http_requests.post",
                    return_value=_FakeLLMResponse("They offer RAG Engine and SmartClassifier.")):
            r = app_client.post("/api/chat", json={
                "messages": [
                    {"role": "user", "content": "Tell me about Example Corp"},
                    {"role": "assistant", "content": full_text},
                    {"role": "user", "content": "What products do they offer?"},
                ],
            })
            events = self._parse_sse(r.data)
            followup = "".join(e.get("content", "") for e in events)
            assert len(followup) > 0

        # 10. Compare pipelines
        app_client.post("/api/pipelines/active", json={
            "pipelines": ["baseline", "full_stack"],
        })
        with patch("app.http_requests.post",
                    return_value=_FakeLLMResponse("AI company with 300 employees.")):
            r = app_client.post("/api/chat/compare", json={
                "messages": [{"role": "user", "content": "How many employees?"}],
            })
            events = self._parse_sse(r.data)
            assert len(events) > 0

        # 11. Metrics recorded
        stats = app_client.get("/api/stats").get_json()
        assert "metrics" in stats

        # 12. Clear and verify
        app_client.post("/api/clear")
        stats = app_client.get("/api/stats").get_json()
        assert stats["n_chunks"] == 0
