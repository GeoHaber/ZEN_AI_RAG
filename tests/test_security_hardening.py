import unittest
import os
import sys
import tempfile
from pathlib import Path

# Add root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from security import validate_path, FileValidator
from config_system import config


class TestSecurityHardening(unittest.TestCase):
    """TestSecurityHardening class."""

    def setUp(self):
        """Setup."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.test_dir.name).resolve()

        # Mock allowed roots in config logic for test
        self.allowed = [self.root]

    def tearDown(self):
        self.test_dir.cleanup()

    def test_strict_path_resolution(self):
        """Test that validate_path enforcement works with strict=True."""
        # Create a valid file
        safe_file = self.root / "safe.txt"
        safe_file.write_text("safe")

        # 1. Valid access
        try:
            res = validate_path(str(safe_file), allowed_roots=self.allowed)
            self.assertEqual(res, safe_file)
        except ValueError as e:
            self.fail(f"Valid path rejected: {e}")

        # 2. Path Traversal (Simulated)
        # On Windows, we can't easily create a symlink without Admin,
        # but we can test '..' resolution logic if strict=True is working
        try:
            # Try to access parent of root (which is outside allowed)
            # resolve() should handle names, check_roots handles the rest
            bad_path = self.root / ".." / "outside.txt"
            validate_path(str(bad_path), allowed_roots=self.allowed)
            self.fail("Path traversal should fail")
        except ValueError:
            pass  # Expected

    def test_magic_numbers(self):
        """Test magic number validation (MIME check)."""
        # Mock allowed extensions to include png for this test
        orig_exts = config.ALLOWED_EXTENSIONS
        config.ALLOWED_EXTENSIONS = {".png", ".jpg", ".txt", ".pdf"}

        try:
            # 1. Fake PNG (Text content in PNG extension)
            fake_png_name = "malware.png"
            fake_content = b"This is not a png image, it is text."

            is_valid, error, _ = FileValidator.validate_file(fake_png_name, fake_content)
            self.assertFalse(is_valid)
            self.assertIn("content does not match extension", error)

            # 2. Valid PNG (Partial Signature)
            real_png_name = "icon.png"
            real_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

            # Override size check for test simple
            orig_max = config.MAX_FILE_SIZE
            config.MAX_FILE_SIZE = 1024  # Small

            is_valid, error, _ = FileValidator.validate_file(real_png_name, real_content)
            self.assertTrue(is_valid, f"Valid PNG rejected: {error}")

            config.MAX_FILE_SIZE = orig_max
        finally:
            config.ALLOWED_EXTENSIONS = orig_exts

    def test_null_byte_sanitization(self):
        """Test content sanitization."""
        dirty = "Hello\x00World"
        clean = FileValidator.sanitize_content(dirty)
        self.assertEqual(clean, "HelloWorld")


if __name__ == "__main__":
    unittest.main()
