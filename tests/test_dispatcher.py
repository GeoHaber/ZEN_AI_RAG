import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from zena_mode.dispatcher import FastDispatcher


@pytest.mark.asyncio
async def test_level_0_regex():
    """Verify instant regex responses."""
    dispatcher = FastDispatcher(backend=None)

    # Greeting
    res = await dispatcher.dispatch("hello")
    assert res["type"] == "direct"
    assert "Hello" in res["content"]

    # Time
    res = await dispatcher.dispatch("what time is it?")
    assert res["type"] == "direct"
    assert "It is currently" in res["content"]


@pytest.mark.asyncio
async def test_level_1_heuristics():
    """Verify heuristic routing."""
    mock_rag = MagicMock()
    dispatcher = FastDispatcher(backend=None, rag_system=mock_rag)

    # Code
    res = await dispatcher.dispatch("write a python script to sort a list")
    assert res["type"] == "expert"
    assert res["expert"] == "code"

    # RAG
    res = await dispatcher.dispatch("search for moon landing")
    assert res["type"] == "rag"

    # General
    res = await dispatcher.dispatch("tell me a joke")
    assert res["type"] == "chat"


if __name__ == "__main__":
    # fast manual run
    async def run():
        d = FastDispatcher(None, MagicMock())
        print(await d.dispatch("hi"))
        print(await d.dispatch("python script"))

    asyncio.run(run())
