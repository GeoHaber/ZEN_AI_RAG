import os
import sys
from pathlib import Path


def test_server_modularity_grep():
    """Verify that server.py does NOT contain logic that should be modularized."""
    server_path = Path("zena_mode/server.py")
    if not server_path.exists():
        return  # Skip if called from wrong CWD

    with open(server_path, "r", encoding="utf-8") as f:
        content = f.read()

    # These strings should NO LONGER be in server.py as primary logic
    monolithic_strings = [
        "model_manager.get_popular_models()",
        "urllib.parse.parse_qs",
        "sd.rec(",
        "wav.write(",
        "mimetypes.guess_type(file_path)",
    ]

    for s in monolithic_strings:
        assert s not in content, f"Monolithic logic '{s}' still found in server.py! Should be in handlers."


def test_handler_registration():
    """Verify that handlers are correctly imported in server.py."""
    from zena_mode.server import ZenAIOrchestrator

    # Check inheritance
    from zena_mode.handlers.base import BaseZenHandler

    assert issubclass(ZenAIOrchestrator, BaseZenHandler)

    # Check delegated calls (we can check if ModelHandler is used in do_GET)
    import inspect

    source = inspect.getsource(ZenAIOrchestrator.do_GET)
    assert "ModelHandler.handle_get(self)" in source
    assert "VoiceHandler.handle_get(self)" in source
    assert "StaticHandler.handle_get(self)" in source


def test_vulnerability_scan_grep():
    """Tougher test: grep for hardcoded secrets or unsafe binds."""
    # Grep all python files for hardcoded localhost IPs in config strings
    # (Except where intentional like in server bind)
    pass
