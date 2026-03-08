#!/usr/bin/env python
"""Quick import test to diagnose ZEN_AI_RAG startup issues."""

import sys
from pathlib import Path

# Set up paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 60)
print("ZEN_AI_RAG Import Diagnostics")
print("=" * 60)

tests = [
    ("config_system", "config, EMOJI"),
    ("ui.styles", "Styles"),
    ("ui.bootstrap", "setup_logging, setup_crash_handler, initialize_services"),
    ("ui.state", "UIState"),
    ("ui.handlers", "UIHandlers"),
    ("ui.layout", "build_page"),
    ("ui.background", "start_background_gateways, run_system_checks"),
    ("ui.testing", "register_test_endpoints"),
    ("ui_components", "setup_app_theme, setup_common_dialogs, setup_drawer, setup_rag_dialog"),
    ("async_backend", "AsyncZenAIBackend"),
    ("mock_backend", "MockAsyncBackend"),
    ("ui.locales", "get_locale"),
]

failed = []
for module_name, items in tests:
    try:
        mod = __import__(module_name, fromlist=items.split(", "))
        for item in items.split(", "):
            getattr(mod, item.strip())
        # [X-Ray auto-fix] print(f"✓ {module_name}: {items}")
    except Exception as e:
        # [X-Ray auto-fix] print(f"✗ {module_name}: {e}")
        failed.append((module_name, str(e)))

print("\n" + "=" * 60)
if failed:
    # [X-Ray auto-fix] print(f"FAILED: {len(failed)} imports")
    for mod, err in failed:
        # [X-Ray auto-fix] print(f"  - {mod}: {err[:80]}")
        pass
else:
    print("All imports OK!")
print("=" * 60)
