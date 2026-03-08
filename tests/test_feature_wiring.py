# -*- coding: utf-8 -*-
"""
tests/test_feature_wiring.py - Ensures features are properly connected to UI

These tests catch cases where features exist in code but are not wired to the UI,
preventing "ghost features" that users can never access.

NOTE: These are static analysis tests that read source files directly.
They do NOT require the app to be running and don't use network fixtures.
"""

import unittest
import re
from pathlib import Path
import sys

# Skip conftest fixtures - these are pure static analysis tests
import pytest

pytestmark = pytest.mark.usefixtures()  # Override any auto-use fixtures

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))


class _TestFeatureWiringBase(unittest.TestCase):
    """Base methods for TestFeatureWiring."""

    def setUpClass(cls):
        """Load source files for analysis."""
        cls.root = Path(__file__).parent.parent
        cls.ui_components_path = cls.root / "ui_components.py"
        cls.zena_path = cls.root / "zena.py"
        cls.asgi_server_path = cls.root / "zena_mode" / "asgi_server.py"

        # Load file contents
        with open(cls.ui_components_path, "r", encoding="utf-8") as f:
            cls.ui_components_code = f.read()
        with open(cls.zena_path, "r", encoding="utf-8") as f:
            cls.zena_code = f.read()
        with open(cls.asgi_server_path, "r", encoding="utf-8") as f:
            cls.asgi_server_code = f.read()

    # =========================================================================
    # TUTORIAL SYSTEM
    # =========================================================================
    def test_tutorial_button_exists_in_ui(self):
        """Tutorial should have a trigger button in the UI."""
        # Check that start_tutorial or start_tour is called somewhere clickable
        self.assertIn(
            "start_tour", self.ui_components_code, "Tutorial function should be wired to a button in ui_components.py"
        )

    def test_tutorial_button_has_id(self):
        """Tutorial button should have an ID for testing."""
        self.assertIn(
            "ui-tour-btn", self.ui_components_code, "Tutorial button should have id='ui-tour-btn' for test automation"
        )

    # =========================================================================
    # HELP SYSTEM
    # =========================================================================
    def test_help_docs_indexed_on_startup(self):
        """Internal documentation should be indexed on app startup for help queries."""
        self.assertIn("index_internal_docs", self.zena_code, "index_internal_docs should be called in zena.py")
        # Check it's actually called, not just imported
        # Look for pattern: index_internal_docs(
        self.assertRegex(
            self.zena_code,
            r"index_internal_docs\s*\(",
            "index_internal_docs() should be called (not just imported) in zena.py",
        )

    # =========================================================================
    # VOICE LAB
    # =========================================================================
    def test_voice_lab_endpoint_exists(self):
        """Voice Lab should have a working endpoint in the ASGI server."""
        self.assertIn(
            "/voice/lab", self.asgi_server_code, "Voice Lab endpoint '/voice/lab' should exist in asgi_server.py"
        )

    def test_voice_lab_button_points_to_correct_url(self):
        """Voice Lab button should open the correct endpoint."""
        # Check that the iframe URL matches the endpoint
        self.assertIn(
            "localhost:8002/voice/lab",
            self.ui_components_code,
            "Voice Lab iframe should point to http://localhost:8002/voice/lab",
        )

    # =========================================================================
    # RAG DIALOG
    # =========================================================================
    def test_rag_dialog_exists(self):
        """RAG dialog should be defined and callable."""
        self.assertIn("setup_rag_dialog", self.ui_components_code, "setup_rag_dialog should exist in ui_components.py")


class TestFeatureWiring(_TestFeatureWiringBase, unittest.TestCase):
    """Tests that verify features are properly wired to the UI."""

    @classmethod

    # =========================================================================
    # MODEL MANAGEMENT
    # =========================================================================
    def test_model_switch_button_exists(self):
        """Model switching should be accessible from UI."""
        self.assertIn(
            "switch_to_model", self.ui_components_code, "switch_to_model function should exist for model switching"
        )

    # =========================================================================
    # SETTINGS DIALOG
    # =========================================================================
    def test_settings_dialog_wired(self):
        """Settings dialog should be wired to a button."""
        self.assertIn(
            "dialogs['settings'].open()", self.ui_components_code, "Settings dialog should be openable from UI"
        )

    # =========================================================================
    # QUALITY DASHBOARD / JUDGE
    # =========================================================================
    def test_quality_dashboard_exists(self):
        """Quality dashboard should be importable and used."""
        self.assertIn(
            "create_quality_tab", self.ui_components_code, "create_quality_tab should be called in the Judge dialog"
        )

    # =========================================================================
    # NEW CHAT BUTTON
    # =========================================================================
    def test_new_chat_button_exists(self):
        """New Chat button should exist with proper ID."""
        self.assertIn("BTN_NEW_CHAT", self.ui_components_code, "New Chat button with ID should exist in UI")

    # =========================================================================
    # ASGI API COMPLETENESS
    # =========================================================================
    def test_asgi_has_health_endpoint(self):
        """ASGI server should have /health endpoint."""
        self.assertIn("/health", self.asgi_server_code, "Health check endpoint should exist")

    def test_asgi_has_model_list_endpoint(self):
        """ASGI server should have model listing endpoint."""
        self.assertIn("/list", self.asgi_server_code, "Model list endpoint should exist")

    def test_asgi_has_tts_endpoint(self):
        """ASGI server should have TTS endpoint."""
        self.assertIn("/api/tts", self.asgi_server_code, "TTS endpoint should exist")

    def test_asgi_has_stt_endpoint(self):
        """ASGI server should have STT endpoint."""
        self.assertIn("/api/stt", self.asgi_server_code, "STT endpoint should exist")


class TestUIElementIDs(unittest.TestCase):
    """Tests that important UI elements have IDs for automation."""

    @classmethod
    def setUpClass(cls):
        """Setupclass."""
        cls.root = Path(__file__).parent.parent
        cls.registry_path = cls.root / "ui" / "registry.py"
        with open(cls.registry_path, "r", encoding="utf-8") as f:
            cls.registry_code = f.read()

    def test_critical_ui_ids_defined(self):
        """Critical UI elements should have IDs in the registry."""
        critical_ids = [
            "INPUT_CHAT",
            "BTN_SEND",
            "BTN_ATTACH",
            "BTN_VOICE",
            "BTN_SETTINGS",
            "BTN_NEW_CHAT",
        ]
        for id_name in critical_ids:
            with self.subTest(id_name=id_name):
                self.assertIn(id_name, self.registry_code, f"UI_IDS.{id_name} should be defined in registry.py")


class TestImportIntegrity(unittest.TestCase):
    """Tests that imported functions are actually used."""

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).parent.parent
        with open(cls.root / "zena.py", "r", encoding="utf-8") as f:
            cls.zena_code = f.read()

    def test_imported_tutorial_is_used(self):
        """start_tutorial should be used in UI components."""
        # Tutorial button is wired in ui_components.py, not zena.py
        ui_components_path = self.root / "ui_components.py"
        with open(ui_components_path, "r", encoding="utf-8") as f:
            ui_code = f.read()

        # Should have start_tutorial imported and called
        self.assertIn("start_tutorial", ui_code, "start_tutorial should be used in ui_components.py")

    def test_imported_help_system_is_used(self):
        """Imported index_internal_docs should be called."""
        import_match = re.search(r"from zena_mode\.help_system import index_internal_docs", self.zena_code)
        if import_match:
            after_import = self.zena_code[import_match.end() :]
            # Should have a function call
            self.assertRegex(
                after_import, r"index_internal_docs\s*\(", "index_internal_docs is imported but never called in zena.py"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
