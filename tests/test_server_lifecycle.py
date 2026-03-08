import pytest
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zena_mode import server
from zena_mode.server import build_llama_cmd, validate_environment


# [X-Ray auto-fix] print(f"\n[DEBUG] Server Module Attributes: {dir(server)}")
class TestServerLifecycle:
    """
    Verification Test for Server Startup Logic.
    Ensures safe settings are applied and environment is validated.
    """

    def test_build_llama_cmd_safe_defaults(self):
        """Verify build_llama_cmd uses safe batch sizes (512)."""
        # Pass explicit model_path to avoid global dependency issues
        cmd = build_llama_cmd(port=8001, threads=4, batch=512, ubatch=512, model_path=Path("test_model.gguf"))

        # Check command structure
        assert "llama-server.exe" in cmd[0]
        assert "--port" in cmd
        assert "8001" in cmd

        # Verify Batch Size Flags
        assert "--batch-size" in cmd
        batch_idx = cmd.index("--batch-size")
        assert cmd[batch_idx + 1] == "512", "Batch size should be 512 for stability"

        assert "--ubatch-size" in cmd
        ubatch_idx = cmd.index("--ubatch-size")
        assert cmd[ubatch_idx + 1] == "512", "Micro-batch size should be 512"

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    def test_validate_environment_success(self, mock_stat, mock_exists):
        """Verify validation passes if binaries exist."""
        # Mock exists=True
        mock_exists.return_value = True
        # Mock size > 1000/1MB
        mock_stat.return_value.st_size = 10000000

        # We also need to mock is_port_active or ensure it returns False
        with patch("zena_mode.server.is_port_active", return_value=False):
            result = validate_environment()

        assert result is True, "Validation should pass if files exist"

    @patch("pathlib.Path.exists")
    def test_validate_environment_missing_bin(self, mock_exists):
        """Verify validation fails if binaries are missing."""
        # Mock exists=False
        mock_exists.return_value = False

        result = validate_environment()

        assert result is False, "Validation should fail if files are missing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
