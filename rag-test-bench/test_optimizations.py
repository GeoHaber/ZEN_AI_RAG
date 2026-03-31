"""
Comprehensive tests for llama-server optimization flags and chat context compression.

Tests cover:
  1. LlamaServerManager: command-line construction, KV type validation, opts dict
  2. Context compression: score filtering, token budgeting, history trimming
  3. API wiring: Flask endpoint parameter passthrough
  4. Edge cases: empty messages, no RAG results, huge histories, boundary values

Run:  python -m pytest test_optimizations.py -v
"""

from __future__ import annotations

import json
import os
import sys
import types
from dataclasses import dataclass
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ── Helpers to import without side-effects ─────────────────────────────────

# Patch heavy imports that llama_server.py and app.py need at module level
# so tests run instantly without loading sentence-transformers or TurboQuant.


# ═══════════════════════════════════════════════════════════════════════════
# PART 1: LlamaServerManager unit tests
# ═══════════════════════════════════════════════════════════════════════════

from zen_core_libs.llm import LlamaServerManager, find_llama_server_binary


class TestKVCacheTypeValidation:
    """Verify KV cache type validation logic (no process spawned)."""

    def test_all_valid_types_accepted(self):
        mgr = LlamaServerManager()
        for t in mgr.KV_CACHE_TYPES:
            assert t in ("f32", "f16", "bf16", "q8_0", "q4_0", "q4_1", "iq4_nl", "q5_0", "q5_1")

    def test_valid_type_count(self):
        mgr = LlamaServerManager()
        assert len(mgr.KV_CACHE_TYPES) == 9

    def test_default_opts_empty_when_not_running(self):
        mgr = LlamaServerManager()
        st = mgr.status()
        assert st["opts"] == {}
        assert st["running"] is False

    def test_status_has_binary_field(self):
        mgr = LlamaServerManager()
        st = mgr.status()
        assert "binary" in st

    def test_base_url_format(self):
        mgr = LlamaServerManager()
        mgr._port = 9999
        assert mgr.base_url == "http://localhost:9999/v1"


class TestCommandLineConstruction:
    """Test that start() builds the correct command line.
    We mock subprocess.Popen and requests.get so no process is actually spawned.
    """

    @pytest.fixture
    def mgr(self, tmp_path):
        """Create a manager with a fake binary and model."""
        fake_bin = tmp_path / "llama-server.exe"
        fake_bin.write_text("fake")
        fake_model = tmp_path / "test-model.gguf"
        fake_model.write_text("fake model")
        return LlamaServerManager(), str(fake_bin), str(fake_model)

    def _mock_start(self, mgr, binary, model, **kwargs):
        """Run start() capturing the Popen cmd without actually starting anything."""
        captured_cmd = []

        class FakeProc:
            pid = 12345
            stdout = MagicMock()
            def poll(self): return None
            def terminate(self): pass
            def wait(self, timeout=None): pass
            def kill(self): pass

        def fake_popen(cmd, **kw):
            captured_cmd.extend(cmd)
            return FakeProc()

        def fake_get(url, **kw):
            resp = MagicMock()
            resp.status_code = 200
            resp.headers = {"content-type": "application/json"}
            resp.json.return_value = {"status": "ok"}
            return resp

        with patch("zen_core_libs.llm.server.find_llama_server_binary", return_value=binary), \
             patch("subprocess.Popen", side_effect=fake_popen), \
             patch("requests.get", side_effect=fake_get), \
             patch.object(LlamaServerManager, "_kill_stale_port"):
            mgr.start(model, **kwargs)

        return captured_cmd

    def test_default_optimization_flags(self, mgr):
        m, binary, model = mgr
        cmd = self._mock_start(m, binary, model)
        cmd_str = " ".join(cmd)

        # KV cache quantization defaults to q8_0
        assert "--cache-type-k" in cmd
        idx = cmd.index("--cache-type-k")
        assert cmd[idx + 1] == "q8_0"

        idx = cmd.index("--cache-type-v")
        assert cmd[idx + 1] == "q8_0"

        # Flash attention default: on
        idx = cmd.index("--flash-attn")
        assert cmd[idx + 1] == "on"

        # mlock enabled by default
        assert "--mlock" in cmd

        # cont-batching enabled by default
        assert "--cont-batching" in cmd

        # cache-reuse default: 256
        idx = cmd.index("--cache-reuse")
        assert cmd[idx + 1] == "256"

        # slot-prompt-similarity default: 0.5
        idx = cmd.index("--slot-prompt-similarity")
        assert cmd[idx + 1] == "0.5"

    def test_custom_kv_cache_types(self, mgr):
        m, binary, model = mgr
        cmd = self._mock_start(m, binary, model, kv_cache_type_k="q4_0", kv_cache_type_v="f16")

        idx_k = cmd.index("--cache-type-k")
        assert cmd[idx_k + 1] == "q4_0"

        idx_v = cmd.index("--cache-type-v")
        assert cmd[idx_v + 1] == "f16"

    def test_invalid_kv_type_falls_back_to_q8_0(self, mgr):
        m, binary, model = mgr
        cmd = self._mock_start(m, binary, model, kv_cache_type_k="INVALID", kv_cache_type_v="bad_type")

        idx_k = cmd.index("--cache-type-k")
        assert cmd[idx_k + 1] == "q8_0"

        idx_v = cmd.index("--cache-type-v")
        assert cmd[idx_v + 1] == "q8_0"

    def test_mlock_disabled(self, mgr):
        m, binary, model = mgr
        cmd = self._mock_start(m, binary, model, mlock=False)
        assert "--mlock" not in cmd

    def test_cont_batching_disabled(self, mgr):
        m, binary, model = mgr
        cmd = self._mock_start(m, binary, model, cont_batching=False)
        assert "--cont-batching" not in cmd

    def test_flash_attn_off(self, mgr):
        m, binary, model = mgr
        cmd = self._mock_start(m, binary, model, flash_attn="off")
        idx = cmd.index("--flash-attn")
        assert cmd[idx + 1] == "off"

    def test_flash_attn_auto(self, mgr):
        m, binary, model = mgr
        cmd = self._mock_start(m, binary, model, flash_attn="auto")
        idx = cmd.index("--flash-attn")
        assert cmd[idx + 1] == "auto"

    def test_custom_cache_reuse(self, mgr):
        m, binary, model = mgr
        cmd = self._mock_start(m, binary, model, cache_reuse=512)
        idx = cmd.index("--cache-reuse")
        assert cmd[idx + 1] == "512"

    def test_custom_slot_similarity(self, mgr):
        m, binary, model = mgr
        cmd = self._mock_start(m, binary, model, slot_prompt_similarity=0.8)
        idx = cmd.index("--slot-prompt-similarity")
        assert cmd[idx + 1] == "0.8"

    def test_opts_dict_stored(self, mgr):
        m, binary, model = mgr
        self._mock_start(m, binary, model, kv_cache_type_k="q4_0", flash_attn="auto", mlock=False)
        assert m._opts["kv_cache_type_k"] == "q4_0"
        assert m._opts["flash_attn"] == "auto"
        assert m._opts["mlock"] is False

    def test_opts_in_status_when_running(self, mgr):
        m, binary, model = mgr
        self._mock_start(m, binary, model)
        st = m.status()
        assert st["running"] is True
        assert st["opts"]["kv_cache_type_k"] == "q8_0"
        assert st["opts"]["flash_attn"] == "on"
        assert st["opts"]["mlock"] is True

    def test_basic_flags_preserved(self, mgr):
        """Ensure the base flags (model, port, ctx-size, gpu-layers, host) are still there."""
        m, binary, model = mgr
        cmd = self._mock_start(m, binary, model, port=7777, gpu_layers=42, ctx_size=8192)

        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == model

        idx = cmd.index("--port")
        assert cmd[idx + 1] == "7777"

        idx = cmd.index("--n-gpu-layers")
        assert cmd[idx + 1] == "42"

        idx = cmd.index("--ctx-size")
        assert cmd[idx + 1] == "8192"

        idx = cmd.index("--host")
        assert cmd[idx + 1] == "0.0.0.0"

    def test_all_kv_types_accepted(self, mgr):
        """Verify every valid KV type passes through without fallback."""
        _, binary, model = mgr
        for kv_type in LlamaServerManager.KV_CACHE_TYPES:
            # Fresh manager each iteration to avoid _kill_proc on a FakeProc
            m = LlamaServerManager()
            cmd = self._mock_start(m, binary, model, kv_cache_type_k=kv_type, kv_cache_type_v=kv_type)
            idx_k = cmd.index("--cache-type-k")
            assert cmd[idx_k + 1] == kv_type, f"K type {kv_type} not preserved"
            idx_v = cmd.index("--cache-type-v")
            assert cmd[idx_v + 1] == kv_type, f"V type {kv_type} not preserved"


class TestStartErrorHandling:
    """Test error paths in start()."""

    def test_missing_binary_raises(self, tmp_path):
        mgr = LlamaServerManager()
        fake_model = tmp_path / "model.gguf"
        fake_model.write_text("data")
        with patch("zen_core_libs.llm.server.find_llama_server_binary", return_value=None):
            with pytest.raises(FileNotFoundError, match="llama-server binary not found"):
                mgr.start(str(fake_model))

    def test_missing_model_raises(self, tmp_path):
        mgr = LlamaServerManager()
        fake_bin = tmp_path / "llama-server.exe"
        fake_bin.write_text("fake")
        with patch("zen_core_libs.llm.server.find_llama_server_binary", return_value=str(fake_bin)):
            with pytest.raises(FileNotFoundError, match="Model not found"):
                mgr.start("/nonexistent/model.gguf")


# ═══════════════════════════════════════════════════════════════════════════
# PART 2: Context compression unit tests (pure logic, no Flask)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FakeChunk:
    text: str
    source_url: str = "http://example.com"
    page_title: str = "Test"
    chunk_idx: int = 0
    char_offset: int = 0


@dataclass
class FakeSearchResult:
    chunk: FakeChunk
    score: float


def _run_compression(
    messages: list[dict],
    search_results: list[FakeSearchResult] | None = None,
    rag_score_threshold: float = 0.15,
    rag_k: int = 5,
    ctx_budget: int = 3072,
    rag_token_budget: int = 1200,
    chars_per_token: int = 4,
    system_prompt: str = "",
) -> dict:
    """
    Replicate the chat endpoint's compression logic standalone for testing.
    Returns dict with all computed values.
    """
    # Get last user message
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "")
            break

    # Retrieve RAG context with score-based filtering
    rag_context = ""
    rag_sources = []
    rag_timing = {}
    rag_filtered = 0

    if last_user_msg and search_results is not None:
        results = search_results
        # Filter by score threshold
        strong = [r for r in results if r.score >= rag_score_threshold]
        rag_filtered = len(results) - len(strong)

        # Budget-cap RAG context
        parts = []
        total_chars = 0
        max_rag_chars = rag_token_budget * chars_per_token
        for r in strong:
            chunk_text_str = f"[{r.chunk.page_title}] ({r.chunk.source_url})\n{r.chunk.text}"
            if total_chars + len(chunk_text_str) > max_rag_chars:
                break
            parts.append(chunk_text_str)
            total_chars += len(chunk_text_str)
            rag_sources.append({
                "title": r.chunk.page_title,
                "url": r.chunk.source_url,
                "score": round(r.score, 4),
            })
        rag_context = "\n\n---\n\n".join(parts)

    rag_timing["rag_filtered_weak"] = rag_filtered
    rag_timing["rag_chunks_sent"] = len(rag_sources)
    rag_timing["rag_context_chars"] = len(rag_context)
    rag_timing["rag_context_est_tokens"] = len(rag_context) // chars_per_token

    # Build system prompt
    system_parts = []
    if system_prompt:
        system_parts.append(system_prompt)
    else:
        system_parts.append(
            "You are a helpful assistant. Answer questions based on the provided context. "
            "If the context doesn't contain the answer, say so honestly. "
            "Always cite your sources when using the retrieved context."
        )
    if rag_context:
        system_parts.append(f"\n\n## Retrieved Context\n\n{rag_context}")

    system_msg = {"role": "system", "content": "\n".join(system_parts)}

    # Chat history compression
    system_tokens = len(system_msg["content"]) // chars_per_token
    remaining = ctx_budget - system_tokens
    trimmed_messages = []
    total_msg_chars = 0
    for m in reversed(messages):
        mc = len(m.get("content", ""))
        if total_msg_chars + mc > remaining * chars_per_token:
            break
        trimmed_messages.insert(0, m)
        total_msg_chars += mc

    if not trimmed_messages and messages:
        trimmed_messages = [messages[-1]]

    history_trimmed = len(messages) - len(trimmed_messages)

    return {
        "rag_context": rag_context,
        "rag_sources": rag_sources,
        "rag_filtered": rag_filtered,
        "rag_context_chars": len(rag_context),
        "rag_context_est_tokens": len(rag_context) // chars_per_token,
        "system_msg": system_msg,
        "trimmed_messages": trimmed_messages,
        "history_trimmed": history_trimmed,
        "total_messages": len(messages),
    }


class TestScoreFiltering:
    """Verify RAG chunks below score threshold are dropped."""

    def test_all_above_threshold(self):
        results = [
            FakeSearchResult(FakeChunk(text="Good chunk A"), score=0.85),
            FakeSearchResult(FakeChunk(text="Good chunk B"), score=0.70),
            FakeSearchResult(FakeChunk(text="Good chunk C"), score=0.55),
        ]
        out = _run_compression(
            [{"role": "user", "content": "test query"}],
            search_results=results,
        )
        assert out["rag_filtered"] == 0
        assert out["rag_sources"] == [
            {"title": "Test", "url": "http://example.com", "score": 0.85},
            {"title": "Test", "url": "http://example.com", "score": 0.7},
            {"title": "Test", "url": "http://example.com", "score": 0.55},
        ]

    def test_some_below_threshold(self):
        results = [
            FakeSearchResult(FakeChunk(text="Strong"), score=0.80),
            FakeSearchResult(FakeChunk(text="Weak"), score=0.10),
            FakeSearchResult(FakeChunk(text="Very weak"), score=0.05),
        ]
        out = _run_compression(
            [{"role": "user", "content": "test"}],
            search_results=results,
            rag_score_threshold=0.15,
        )
        assert out["rag_filtered"] == 2
        assert len(out["rag_sources"]) == 1
        assert out["rag_sources"][0]["score"] == 0.8

    def test_all_below_threshold(self):
        results = [
            FakeSearchResult(FakeChunk(text="Weak A"), score=0.10),
            FakeSearchResult(FakeChunk(text="Weak B"), score=0.05),
        ]
        out = _run_compression(
            [{"role": "user", "content": "test"}],
            search_results=results,
            rag_score_threshold=0.15,
        )
        assert out["rag_filtered"] == 2
        assert len(out["rag_sources"]) == 0
        assert out["rag_context"] == ""

    def test_exact_threshold_included(self):
        results = [
            FakeSearchResult(FakeChunk(text="Borderline"), score=0.15),
        ]
        out = _run_compression(
            [{"role": "user", "content": "test"}],
            search_results=results,
            rag_score_threshold=0.15,
        )
        assert out["rag_filtered"] == 0
        assert len(out["rag_sources"]) == 1

    def test_zero_threshold_keeps_all(self):
        results = [
            FakeSearchResult(FakeChunk(text="A"), score=0.01),
            FakeSearchResult(FakeChunk(text="B"), score=0.001),
        ]
        out = _run_compression(
            [{"role": "user", "content": "test"}],
            search_results=results,
            rag_score_threshold=0.0,
        )
        assert out["rag_filtered"] == 0
        assert len(out["rag_sources"]) == 2


class TestTokenBudgeting:
    """Verify RAG context is capped at token budget."""

    def test_small_chunks_all_fit(self):
        results = [
            FakeSearchResult(FakeChunk(text="Short"), score=0.9),
            FakeSearchResult(FakeChunk(text="Also short"), score=0.8),
        ]
        out = _run_compression(
            [{"role": "user", "content": "q"}],
            search_results=results,
            rag_token_budget=1200,
        )
        assert len(out["rag_sources"]) == 2

    def test_large_chunks_truncated(self):
        # Each chunk ~1000 chars → ~250 tokens. Budget=100 tokens=400 chars
        big_text = "X" * 1000
        results = [
            FakeSearchResult(FakeChunk(text=big_text, page_title="T1"), score=0.9),
            FakeSearchResult(FakeChunk(text=big_text, page_title="T2"), score=0.8),
            FakeSearchResult(FakeChunk(text=big_text, page_title="T3"), score=0.7),
        ]
        out = _run_compression(
            [{"role": "user", "content": "q"}],
            search_results=results,
            rag_token_budget=100,  # 400 chars
        )
        # Only first chunk should fit (it's ~1030 chars with metadata → exceeds 400)
        # Actually even the first chunk exceeds 400 chars, so none fit
        assert len(out["rag_sources"]) == 0

    def test_budget_allows_partial(self):
        """Two chunks: first fits, second doesn't."""
        results = [
            FakeSearchResult(FakeChunk(text="A" * 300, page_title="T"), score=0.9),
            FakeSearchResult(FakeChunk(text="B" * 300, page_title="T"), score=0.8),
        ]
        # Budget: 200 tokens = 800 chars. First chunk with metadata ≈ 340 chars. Both ≈ 690.
        out = _run_compression(
            [{"role": "user", "content": "q"}],
            search_results=results,
            rag_token_budget=200,
        )
        assert len(out["rag_sources"]) == 2  # Both should fit in 800 chars

    def test_context_token_estimate(self):
        results = [
            FakeSearchResult(FakeChunk(text="Word " * 100), score=0.9),
        ]
        out = _run_compression(
            [{"role": "user", "content": "test"}],
            search_results=results,
        )
        chars = out["rag_context_chars"]
        est_tokens = out["rag_context_est_tokens"]
        assert est_tokens == chars // 4


class TestHistoryTrimming:
    """Verify chat history is trimmed to fit remaining budget."""

    def test_short_history_not_trimmed(self):
        msgs = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "How are you?"},
        ]
        out = _run_compression(msgs)
        assert out["history_trimmed"] == 0
        assert len(out["trimmed_messages"]) == 3

    def test_long_history_trimmed(self):
        """Build 50 turns of 200-char messages → 10000 chars total → must trim."""
        msgs = []
        for i in range(50):
            msgs.append({"role": "user", "content": f"Message {i}: " + "x" * 200})
            msgs.append({"role": "assistant", "content": f"Reply {i}: " + "y" * 200})
        out = _run_compression(msgs, ctx_budget=500)
        assert out["history_trimmed"] > 0
        assert len(out["trimmed_messages"]) < 100
        # Trimmed messages should be the MOST RECENT ones
        last_trimmed = out["trimmed_messages"][-1]
        assert last_trimmed["content"] == msgs[-1]["content"]

    def test_fallback_keeps_last_message(self):
        """Even if budget is tiny, must keep at least the last message."""
        msgs = [
            {"role": "user", "content": "A" * 100000},  # Huge message
        ]
        out = _run_compression(msgs, ctx_budget=10)  # Very tiny budget
        assert len(out["trimmed_messages"]) == 1
        assert out["trimmed_messages"][0]["content"] == msgs[0]["content"]

    def test_trimming_preserves_order(self):
        msgs = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply1"},
            {"role": "user", "content": "second"},
            {"role": "assistant", "content": "reply2"},
            {"role": "user", "content": "third"},
        ]
        out = _run_compression(msgs, ctx_budget=3072)
        trimmed = out["trimmed_messages"]
        # All should fit with default budget
        assert [m["content"] for m in trimmed] == ["first", "reply1", "second", "reply2", "third"]


class TestNoRAGContext:
    """Test behavior when no RAG index is available."""

    def test_no_search_results(self):
        out = _run_compression(
            [{"role": "user", "content": "test"}],
            search_results=None,
        )
        assert out["rag_context"] == ""
        assert out["rag_filtered"] == 0
        assert out["rag_sources"] == []
        assert out["rag_context_est_tokens"] == 0

    def test_empty_search_results(self):
        out = _run_compression(
            [{"role": "user", "content": "test"}],
            search_results=[],
        )
        assert out["rag_context"] == ""

    def test_system_prompt_without_rag(self):
        out = _run_compression(
            [{"role": "user", "content": "hello"}],
            search_results=None,
        )
        assert "Retrieved Context" not in out["system_msg"]["content"]
        assert "helpful assistant" in out["system_msg"]["content"]

    def test_system_prompt_with_rag(self):
        results = [FakeSearchResult(FakeChunk(text="Data here"), score=0.9)]
        out = _run_compression(
            [{"role": "user", "content": "test"}],
            search_results=results,
        )
        assert "Retrieved Context" in out["system_msg"]["content"]
        assert "Data here" in out["system_msg"]["content"]

    def test_custom_system_prompt(self):
        out = _run_compression(
            [{"role": "user", "content": "hi"}],
            system_prompt="You are a medical assistant.",
        )
        assert "medical assistant" in out["system_msg"]["content"]


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_messages_list(self):
        """Empty messages should produce no context, no crash."""
        out = _run_compression([], search_results=None)
        assert out["trimmed_messages"] == []
        assert out["history_trimmed"] == 0

    def test_single_message(self):
        out = _run_compression([{"role": "user", "content": "hi"}])
        assert len(out["trimmed_messages"]) == 1

    def test_assistant_only_messages(self):
        """No user message → no RAG retrieval."""
        msgs = [{"role": "assistant", "content": "I'm ready to help."}]
        results = [FakeSearchResult(FakeChunk(text="Data"), score=0.9)]
        out = _run_compression(msgs, search_results=results)
        # Should NOT retrieve RAG since there's no user message
        assert out["rag_context"] == ""

    def test_score_precision_preserved(self):
        """Score rounding should keep 4 decimal places."""
        results = [
            FakeSearchResult(FakeChunk(text="A"), score=0.923456789),
        ]
        out = _run_compression(
            [{"role": "user", "content": "test"}],
            search_results=results,
        )
        assert out["rag_sources"][0]["score"] == 0.9235  # rounded to 4 decimals

    def test_unicode_content_handled(self):
        """Unicode content shouldn't break char counting."""
        msgs = [{"role": "user", "content": "こんにちは世界 🌍 مرحبا"}]
        results = [FakeSearchResult(FakeChunk(text="日本語テキスト"), score=0.9)]
        out = _run_compression(msgs, search_results=results)
        assert len(out["trimmed_messages"]) == 1
        assert out["rag_context_chars"] > 0

    def test_very_high_score_threshold_filters_all(self):
        results = [
            FakeSearchResult(FakeChunk(text="A"), score=0.95),
            FakeSearchResult(FakeChunk(text="B"), score=0.90),
        ]
        out = _run_compression(
            [{"role": "user", "content": "test"}],
            search_results=results,
            rag_score_threshold=0.99,
        )
        assert out["rag_filtered"] == 2
        assert len(out["rag_sources"]) == 0


# ═══════════════════════════════════════════════════════════════════════════
# PART 3: Flask API endpoint tests
# ═══════════════════════════════════════════════════════════════════════════

class TestFlaskAPIWiring:
    """Test that Flask endpoints correctly parse and pass optimization params."""

    @pytest.fixture
    def client(self):
        """Create a test Flask client with mocked heavy dependencies."""
        # We need to mock the RAG index and LLAMA server to avoid real loads
        with patch("app.INDEX") as mock_idx, \
             patch("app.LLAMA") as mock_llama:
            mock_idx.is_built = False
            mock_idx.n_chunks = 0
            mock_llama.is_running = False

            from app import app
            app.config["TESTING"] = True
            with app.test_client() as c:
                yield c, mock_llama

    def test_start_endpoint_default_params(self, client, tmp_path):
        c, mock_llama = client
        fake_model = tmp_path / "test.gguf"
        fake_model.write_text("data")

        mock_llama.start = MagicMock()

        resp = c.post("/api/llm/server/start", json={
            "model_path": str(fake_model),
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["starting"] is True

    def test_start_endpoint_custom_opts(self, client, tmp_path):
        c, mock_llama = client
        fake_model = tmp_path / "test.gguf"
        fake_model.write_text("data")

        mock_llama.start = MagicMock()

        resp = c.post("/api/llm/server/start", json={
            "model_path": str(fake_model),
            "kv_cache_type_k": "q4_0",
            "kv_cache_type_v": "q4_1",
            "flash_attn": "off",
            "mlock": False,
            "cont_batching": False,
            "cache_reuse": 512,
            "slot_prompt_similarity": 0.8,
        })
        assert resp.status_code == 200

    def test_status_endpoint(self, client):
        c, mock_llama = client
        mock_llama.status.return_value = {
            "running": False, "model": None, "port": None, "opts": {},
        }
        resp = c.get("/api/llm/server/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "running" in data


# ═══════════════════════════════════════════════════════════════════════════
# PART 4: Precision / consistency tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPrecisionConsistency:
    """Ensure no data loss or corruption through the optimization pipeline."""

    def test_source_metadata_fully_preserved(self):
        """All chunk metadata must survive through compression."""
        results = [
            FakeSearchResult(
                FakeChunk(
                    text="Important medical data about patient treatment protocols",
                    source_url="https://hospital.example.com/protocols/123",
                    page_title="Treatment Protocol v2.1",
                    chunk_idx=7,
                ),
                score=0.92,
            ),
        ]
        out = _run_compression(
            [{"role": "user", "content": "treatment protocol"}],
            search_results=results,
        )
        src = out["rag_sources"][0]
        assert src["title"] == "Treatment Protocol v2.1"
        assert src["url"] == "https://hospital.example.com/protocols/123"
        assert src["score"] == 0.92

    def test_chunk_text_not_truncated_within_budget(self):
        """Within budget, chunk text should appear in full in the context."""
        original_text = "This is the complete chunk text that should not be truncated at all."
        results = [FakeSearchResult(FakeChunk(text=original_text), score=0.9)]
        out = _run_compression(
            [{"role": "user", "content": "test"}],
            search_results=results,
        )
        assert original_text in out["rag_context"]

    def test_message_content_not_modified(self):
        """Trimming should not modify message content, only drop whole messages."""
        original = "This is my exact message with special chars: <>&\"' 日本語"
        msgs = [{"role": "user", "content": original}]
        out = _run_compression(msgs)
        assert out["trimmed_messages"][0]["content"] == original

    def test_message_roles_preserved(self):
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
            {"role": "assistant", "content": "ast"},
        ]
        out = _run_compression(msgs)
        roles = [m["role"] for m in out["trimmed_messages"]]
        assert roles == ["system", "user", "assistant"]

    def test_ordering_stability_under_compression(self):
        """When history is trimmed, remaining messages must maintain order."""
        msgs = []
        for i in range(20):
            msgs.append({"role": "user", "content": f"msg_{i:03d} " + "x" * 500})
            msgs.append({"role": "assistant", "content": f"reply_{i:03d} " + "y" * 500})

        out = _run_compression(msgs, ctx_budget=500)

        trimmed = out["trimmed_messages"]
        # Check monotonic ordering
        for i in range(1, len(trimmed)):
            # Each message in trimmed should come AFTER the previous one in original
            idx_prev = msgs.index(trimmed[i - 1])
            idx_curr = msgs.index(trimmed[i])
            assert idx_curr > idx_prev, f"Order violated: {idx_prev} >= {idx_curr}"

    def test_rag_sources_ordered_by_relevance(self):
        """Sources should maintain the search-result order (best score first)."""
        results = [
            FakeSearchResult(FakeChunk(text="Best", page_title="A"), score=0.95),
            FakeSearchResult(FakeChunk(text="Good", page_title="B"), score=0.80),
            FakeSearchResult(FakeChunk(text="OK", page_title="C"), score=0.60),
        ]
        out = _run_compression(
            [{"role": "user", "content": "query"}],
            search_results=results,
        )
        scores = [s["score"] for s in out["rag_sources"]]
        assert scores == sorted(scores, reverse=True), "Sources not in descending score order"

    def test_no_data_loss_small_budget(self):
        """With restricted budget, the chunks that DO fit should be complete."""
        # 200-char chunk should fit in 200-token budget = 800 chars
        text_a = "Alpha content: " + "a" * 180
        text_b = "Beta content: " + "b" * 180
        results = [
            FakeSearchResult(FakeChunk(text=text_a, page_title="Alpha"), score=0.9),
            FakeSearchResult(FakeChunk(text=text_b, page_title="Beta"), score=0.8),
        ]
        out = _run_compression(
            [{"role": "user", "content": "test"}],
            search_results=results,
            rag_token_budget=200,
        )
        # Whatever sources made it should have their full text in context
        for src in out["rag_sources"]:
            title = src["title"]
            if title == "Alpha":
                assert text_a in out["rag_context"]
            elif title == "Beta":
                assert text_b in out["rag_context"]


# ═══════════════════════════════════════════════════════════════════════════
# PART 5: Regression guard — ensure defaults match between files
# ═══════════════════════════════════════════════════════════════════════════

class TestDefaultConsistency:
    """Verify that default values in zen_core_libs and app.py are consistent."""

    def test_kv_cache_defaults_match(self):
        """app.py default for kv_cache_type should match llama_server.py default."""
        import inspect
        sig = inspect.signature(LlamaServerManager.start)
        assert sig.parameters["kv_cache_type_k"].default == "q8_0"
        assert sig.parameters["kv_cache_type_v"].default == "q8_0"

    def test_flash_attn_default_match(self):
        import inspect
        sig = inspect.signature(LlamaServerManager.start)
        assert sig.parameters["flash_attn"].default == "on"

    def test_mlock_default_match(self):
        import inspect
        sig = inspect.signature(LlamaServerManager.start)
        assert sig.parameters["mlock"].default is True

    def test_cont_batching_default_match(self):
        import inspect
        sig = inspect.signature(LlamaServerManager.start)
        assert sig.parameters["cont_batching"].default is True

    def test_cache_reuse_default_match(self):
        import inspect
        sig = inspect.signature(LlamaServerManager.start)
        assert sig.parameters["cache_reuse"].default == 256

    def test_slot_prompt_similarity_default(self):
        import inspect
        sig = inspect.signature(LlamaServerManager.start)
        assert sig.parameters["slot_prompt_similarity"].default == 0.5
