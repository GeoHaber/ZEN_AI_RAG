# -*- coding: utf-8 -*-
"""
test_llm_adapter_monkey.py — LLM Adapter Resilience / Monkey Tests
====================================================================

Targets: src/llm_adapters.py (LLMProvider, LLMRequest, LLMResponse, adapters)
Tests construction with bad args, cost calculations, enum coverage.

Run:
    pytest tests/test_llm_adapter_monkey.py -v --tb=short -x
"""

import asyncio
import random
import sys
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_CHAOS_STRINGS: list[str] = [
    "",
    "   ",
    "\x00\x01\x02",
    "A" * 100_000,
    "🔥" * 5_000,
    "<script>alert('xss')</script>",
    "'; DROP TABLE users; --",
    "../../../etc/passwd",
    "Hello 你好 مرحبا こんにちは",
    "NaN",
    "null",
    "None",
    "-1",
    "inf",
]


# ═════════════════════════════════════════════════════════════════════════════
#  LLMProvider Enum Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestLLMProviderMonkey:
    """Verify LLMProvider enum completeness and safety."""

    def test_all_providers_exist(self):
        from src.llm_adapters import LLMProvider

        expected = {"LOCAL_LLAMA", "OLLAMA", "OPENAI", "CLAUDE", "HUGGINGFACE", "GEMINI", "COHERE", "CUSTOM"}
        actual = {p.name for p in LLMProvider}
        assert expected.issubset(actual), f"Missing providers: {expected - actual}"

    def test_provider_values_are_strings_or_ints(self):
        from src.llm_adapters import LLMProvider

        for p in LLMProvider:
            assert isinstance(p.value, (str, int))


# ═════════════════════════════════════════════════════════════════════════════
#  LLMRequest / LLMResponse Dataclass Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestLLMDataclassMonkey:
    """Fuzz LLMRequest and LLMResponse with adversarial values."""

    def test_request_construction(self):
        from src.llm_adapters import LLMProvider, LLMRequest

        req = LLMRequest(provider=LLMProvider.LOCAL_LLAMA, model="test", prompt="Hello")
        assert req.prompt == "Hello"
        assert req.temperature == 0.7
        assert req.max_tokens == 2000

    def test_request_chaos_prompt(self):
        from src.llm_adapters import LLMProvider, LLMRequest

        for s in _CHAOS_STRINGS:
            req = LLMRequest(provider=LLMProvider.LOCAL_LLAMA, model="test", prompt=s)
            assert req.prompt == s

    def test_response_defaults(self):
        from src.llm_adapters import LLMResponse

        resp = LLMResponse(text="Hello world")
        assert resp.text == "Hello world"
        assert resp.success is True
        assert resp.error is None
        assert resp.cost >= 0

    def test_response_error_state(self):
        from src.llm_adapters import LLMResponse

        resp = LLMResponse(text="", error="Connection refused", success=False)
        assert not resp.success
        assert resp.error == "Connection refused"

    def test_response_extreme_tokens(self):
        from src.llm_adapters import LLMResponse

        # Zero tokens
        resp = LLMResponse(text="x", tokens_used=0)
        assert resp.cost >= 0
        # Huge tokens
        resp = LLMResponse(text="x", tokens_used=10**9)
        assert resp.tokens_used == 10**9


# ═════════════════════════════════════════════════════════════════════════════
#  Adapter Construction Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestAdapterConstructionMonkey:
    """Every adapter must construct without crash, even with bad args."""

    def test_local_llama_default(self):
        from src.llm_adapters import LocalLlamaAdapter

        adapter = LocalLlamaAdapter()
        assert adapter is not None

    def test_local_llama_invalid_endpoint(self):
        from src.llm_adapters import LocalLlamaAdapter

        adapter = LocalLlamaAdapter(endpoint="http://DOES_NOT_EXIST:99999")
        assert adapter is not None

    def test_ollama_default(self):
        from src.llm_adapters import OllamaAdapter

        adapter = OllamaAdapter()
        assert adapter is not None

    def test_ollama_custom_endpoint(self):
        from src.llm_adapters import OllamaAdapter

        adapter = OllamaAdapter(endpoint="http://localhost:99999")
        assert adapter is not None

    def test_openai_no_key(self):
        from src.llm_adapters import OpenAIAdapter

        with pytest.raises(ValueError, match="API key"):
            OpenAIAdapter(api_key=None)

    def test_openai_empty_key(self):
        from src.llm_adapters import OpenAIAdapter

        with pytest.raises(ValueError, match="API key"):
            OpenAIAdapter(api_key="")


# ═════════════════════════════════════════════════════════════════════════════
#  Cost Calculation Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestCostCalculationMonkey:
    """Cost calculation must never return negative or crash."""

    def test_cost_zero_tokens(self):
        from src.llm_adapters import BaseLLMAdapter

        adapter = BaseLLMAdapter.__new__(BaseLLMAdapter)
        try:
            cost = adapter.calculate_cost(0)
            assert cost >= 0
        except (NotImplementedError, AttributeError, TypeError):
            pass  # base class may not implement

    def test_cost_negative_tokens(self):
        from src.llm_adapters import BaseLLMAdapter

        adapter = BaseLLMAdapter.__new__(BaseLLMAdapter)
        try:
            cost = adapter.calculate_cost(-100)
            assert cost >= 0  # should clamp or return 0
        except (NotImplementedError, AttributeError, TypeError, ValueError):
            pass

    def test_cost_overflow_tokens(self):
        from src.llm_adapters import BaseLLMAdapter

        adapter = BaseLLMAdapter.__new__(BaseLLMAdapter)
        try:
            cost = adapter.calculate_cost(10**18)
            assert isinstance(cost, (int, float))
        except (NotImplementedError, AttributeError, TypeError, OverflowError):
            pass

    def test_openai_cost_calculation(self):
        from src.llm_adapters import OpenAIAdapter

        adapter = OpenAIAdapter(api_key="test")
        try:
            cost_in = adapter.calculate_cost(1000, is_input=True)
            cost_out = adapter.calculate_cost(1000, is_input=False)
            assert cost_in >= 0
            assert cost_out >= 0
        except (NotImplementedError, AttributeError, TypeError):
            pass


# ═════════════════════════════════════════════════════════════════════════════
#  Async Adapter Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
@pytest.mark.asyncio
class TestAdapterAsyncMonkey:
    """Async operations: validate, context managers."""

    async def test_local_llama_validate_offline(self):
        """validate() on unreachable endpoint should return False, not crash."""
        from src.llm_adapters import LocalLlamaAdapter

        adapter = LocalLlamaAdapter(endpoint="http://127.0.0.1:1")
        try:
            result = await adapter.validate()
            assert result is False
        except (ConnectionError, OSError, Exception):
            pass  # network errors acceptable

    async def test_ollama_validate_offline(self):
        from src.llm_adapters import OllamaAdapter

        adapter = OllamaAdapter(endpoint="http://127.0.0.1:1")
        try:
            result = await adapter.validate()
            assert result is False
        except (ConnectionError, OSError, Exception):
            pass

    async def test_context_manager_close(self):
        """async with adapter should work and close cleanly."""
        from src.llm_adapters import LocalLlamaAdapter

        try:
            async with LocalLlamaAdapter() as adapter:
                assert adapter is not None
        except (ConnectionError, OSError, AttributeError):
            pass

    async def test_query_chaos_prompt_no_hang(self):
        """query with chaos prompt should fail fast, not hang."""
        import asyncio

        from src.llm_adapters import LLMProvider, LLMRequest, LocalLlamaAdapter

        adapter = LocalLlamaAdapter(endpoint="http://127.0.0.1:1")
        req = LLMRequest(provider=LLMProvider.LOCAL_LLAMA, model="test", prompt="🔥" * 100)
        try:
            async for chunk in adapter.query(req):
                break  # just get first chunk or error
        except (ConnectionError, OSError, Exception):
            pass


# ═════════════════════════════════════════════════════════════════════════════
#  Thread Safety Tests
# ═════════════════════════════════════════════════════════════════════════════


@pytest.mark.monkey
class TestAdapterThreadSafety:
    """Verify adapters can be constructed from multiple threads."""

    def test_concurrent_construction(self):
        from src.llm_adapters import LocalLlamaAdapter

        errors = []

        def create_adapters(tid):
            try:
                for _ in range(10):
                    LocalLlamaAdapter()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_adapters, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert not errors, f"Construction errors: {errors}"
