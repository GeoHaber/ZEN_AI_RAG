import os
from pathlib import Path
import pytest

from security import validate_path
from config import BASE_DIR, MODEL_DIR


def test_validate_path_within_base_dir(tmp_path):
    """Test validate path within base dir."""
    # Create a temp file inside BASE_DIR (simulate)
    Path(BASE_DIR)
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")

    # Use allowed_roots to include tmp_path
    resolved = validate_path(str(test_file), allowed_roots=[tmp_path.resolve()])
    assert resolved.exists()


def test_validate_path_rejects_system_paths():
    """Test validate path rejects system paths."""
    if os.name == 'nt':
        bad = 'C:\\Windows\\system32\\cmd.exe'
    else:
        bad = '/usr/bin/passwd'

    with pytest.raises(ValueError):
        validate_path(bad)
