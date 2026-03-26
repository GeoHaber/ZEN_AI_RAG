#!/usr/bin/env python3
"""
ZEN_RAG v4.0 — Flet application shell.

Launch::
    python app.py               # native desktop window
    flet run app.py             # same, via flet CLI
    flet run --web app.py       # opens in browser

Architecture:
    Core/               Pure business logic (no UI imports)
    backend_protocol.py Shared UIBackend interface
    backend_impl.py     Concrete implementation for all backends
    ui_flet/state.py    Framework-agnostic AppState + helpers
    ui_flet/theme.py    Flet theme engine
    ui_flet/sidebar.py  Settings sidebar (v2: full panel list)
    ui_flet/chat_panel.py  Chat panel (v2: AppState + ConcreteBackend)
    ui_flet/source_config.py   Welcome + scanning
    ui_flet/data_inspector.py  Data/DB/Cleanup/Cache/Eval/Dedup panels
    ui_flet/marketplace_panel.py  Model marketplace
"""

from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

import flet as ft

# Suppress known harmless warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*swigvarlink.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PyType_Spec.*metaclass.*tp_new.*")

# Ensure project root and src are importable
ROOT = Path(__file__).parent
SRC = ROOT / "src"
for path in [ROOT, SRC]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# ── Imports from ui_flet (Flet-native) ────────────────────────────────────────
from ui_flet.state import AppState, get_llm_config  # noqa: E402
from ui_flet.theme import TH, build_flet_theme  # noqa: E402
from ui_flet.sidebar import build_sidebar_v2  # noqa: E402
from ui_flet.chat_panel import build_chat_panel_v2  # noqa: E402
from ui_flet.marketplace_panel import build_marketplace_panel  # noqa: E402
from ui_flet.data_inspector import (  # noqa: E402
    build_data_status_bar,
    build_data_tab,
    build_db_panel,
    build_cleanup_panel,
    build_cache_panel,
    build_eval_panel,
    build_dedup_panel,
)

# ── Shared backend (same code as NiceGUI uses) ───────────────────────────────
from backend_impl import create_backend  # noqa: E402

# i18n (framework-agnostic, lives in ui/)
try:
    from ui.i18n import set_language  # noqa: E402
except ImportError:
    def set_language(_lang: str) -> bool:
        return False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global app state (framework-agnostic)
state = AppState()

# Shared backend — both UIs use the same implementation
backend = create_backend()


# =============================================================================
# PANEL ROUTER
# =============================================================================

def _build_sources_panel(page):
    from ui_flet.source_config import build_config_panel
    return build_config_panel(page, state, lambda: _rebuild(page))

_PANEL_BUILDERS = {
    "zena": lambda page: build_chat_panel_v2(page, state, backend),
    "sources": _build_sources_panel,
    "marketplace": lambda page: build_marketplace_panel(page, state),
    "data": lambda page: build_data_tab(state),
    "cleanup": lambda page: build_cleanup_panel(page, state),
    "db": lambda page: build_db_panel(page, state),
    "cache": lambda page: build_cache_panel(page, state),
    "eval": lambda page: build_eval_panel(page, state),
    "dedup": lambda page: build_dedup_panel(page, state),
    "dashboard": lambda page: _build_dashboard(page),
    "voice": lambda page: _build_voice(page),
    "gateways": lambda page: _build_gateways(page),
}


def _build_dashboard(page):
    from ui_flet.dashboard_panel import build_quality_dashboard
    return build_quality_dashboard(page, state)


def _build_voice(page):
    from ui_flet.voice_panel import build_voice_lab_panel
    return build_voice_lab_panel(page, state)


def _build_gateways(page):
    from ui_flet.gateways_panel import build_gateways_panel
    return build_gateways_panel(page, state, backend)


def _build_main_content(page: ft.Page) -> ft.Container:
    """Route to the active panel."""
    # If the user is on a specific tool panel, show it
    panel_key = state.active_panel

    # "Chat" (zena) is the default. If no data, show config panel instead of empty chat.
    if panel_key == "zena" and not state.has_data:
        from ui_flet.source_config import build_config_panel

        return build_config_panel(page, state, lambda: _rebuild(page))

    # Data status bar (always show if we have data)
    status_bar = build_data_status_bar(page, state, lambda: _rebuild(page)) if state.has_data else ft.Container()

    builder = _PANEL_BUILDERS.get(panel_key, _PANEL_BUILDERS["zena"])
    panel = builder(page)

    return ft.Container(
        content=ft.Column([status_bar, panel], expand=True, spacing=0),
        expand=True,
    )


# =============================================================================
# FULL APP REBUILD
# =============================================================================


def _rebuild(page: ft.Page):
    """Rebuild the entire app layout. Called on state changes."""
    TH._dark = state.dark_mode
    set_language(state.app_language)
    page.theme = build_flet_theme(state.dark_mode)
    page.theme_mode = ft.ThemeMode.DARK if state.dark_mode else ft.ThemeMode.LIGHT
    page.bgcolor = TH.bg

    sidebar = build_sidebar_v2(page, state, lambda: _rebuild(page))
    main_content = _build_main_content(page)

    page.controls.clear()
    page.controls.append(
        ft.Row(
            [sidebar, ft.VerticalDivider(width=1, color=TH.border), main_content],
            expand=True,
            spacing=0,
        )
    )
    page.update()


# =============================================================================
# ENTRY POINT
# =============================================================================


def main(page: ft.Page):
    page.title = "ZEN_RAG Pro"
    page.window.width = 1200
    page.window.height = 800
    page.padding = 0
    page.spacing = 0

    _rebuild(page)


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)
