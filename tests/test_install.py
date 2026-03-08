import unittest
import zipfile
import tempfile
import shutil
import os
import sys
import subprocess
from pathlib import Path


class TestDistribution(unittest.TestCase):
    """TestDistribution class."""

    def setUp(self):
        """Setup."""
        # Paths
        self.project_root = Path(os.getcwd())
        self.dist_path = self.project_root / "dist" / "ZenAI_Dist.zip"

        # Verify Dist Exists
        if not self.dist_path.exists():
            self.fail(f"Distribution ZIP not found at {self.dist_path}")

        # Create Sandbox
        self.sandbox = self.project_root / "sandbox_test"
        if self.sandbox.exists():
            shutil.rmtree(self.sandbox)
        self.sandbox.mkdir()

    def tearDown(self):
        """Teardown."""
        # Cleanup
        if self.sandbox.exists():
            try:
                shutil.rmtree(self.sandbox)
            except PermissionError:
                # Windows sometimes locks files briefly
                pass

    def test_installation_layout(self):
        """Unpack logic and verify file structure."""
        # [X-Ray auto-fix] print(f"\n📦 Unpacking {self.dist_path.name}...")
        try:
            with zipfile.ZipFile(self.dist_path, "r") as zip_ref:
                zip_ref.extractall(self.sandbox)
        except Exception as e:
            self.fail(f"Failed to unzip distribution: {e}")

        print("✅ Unpack success.")

        # Verify Critical Files
        critical_files = ["zena.py", "requirements.txt", "USER_MANUAL.md", "ui_components.py", "ui/locales/en.py"]

        missing = []
        for f in critical_files:
            p = self.sandbox / f
            if not p.exists():
                missing.append(f)

        self.assertFalse(missing, f"Missing critical files in distribution: {missing}")
        print("✅ Critical files verified.")

        # Verify NO Garbage
        garbage_signatures = [".venv", "node_modules", ".git", "__pycache__"]

        found_garbage = []
        for root, dirs, files in os.walk(self.sandbox):
            for d in dirs:
                if d in garbage_signatures:
                    found_garbage.append(d)

        self.assertFalse(found_garbage, f"Distribution contains garbage directories: {found_garbage}")
        print("✅ Cleanliness verified.")

    def test_startup_simulation(self):
        """Simulate running 'python zena.py' (dry run)."""
        # Unpack first
        with zipfile.ZipFile(self.dist_path, "r") as zip_ref:
            zip_ref.extractall(self.sandbox)

        # We can't easily start the GUI in a test, but we can verify imports.
        # Run a python command in that directory that imports zena

        print("🚀 Simulating Startup Check...")

        # Helper script to just verify imports work without starting GUI/Server
        checker_script = """
import sys
import os
try:
    # Add CWD to path implicit
    import zena
    import config_system
    import utils
    print("IMPORT_SUCCESS")
except ImportError as e:
    print(f"IMPORT_ERROR: {e}")
    sys.exit(1)
except Exception as e:
    # nicegui might fail to install, we catch that
    print(f"RUNTIME_ERROR: {e}")
"""
        check_file = self.sandbox / "check_install.py"
        check_file.write_text(checker_script)

        # Execute
        result = subprocess.run(
            [sys.executable, "check_install.py"], cwd=self.sandbox, capture_output=True, text=True, shell=False
        )

        # [X-Ray auto-fix] print(f"Output: {result.stdout}")
        # [X-Ray auto-fix] print(f"Stderr: {result.stderr}")
        # Check output
        if "nicegui" in result.stderr.lower() and "install" in result.stderr.lower():
            # This is actually GOOD - it means zena.py tried to import nicegui,
            # failed (maybe), but the script logic reached that point.
            # OR we check if imports succeeded.
            pass

        # We expect IMPORT_SUCCESS or specific knwon errors
        self.assertIn("IMPORT_SUCCESS", result.stdout + result.stderr, "Failed to import core modules in sandbox")
        print("✅ Startup Simulation Passed (Imports Working)")


if __name__ == "__main__":
    unittest.main()
