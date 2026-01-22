# -*- coding: utf-8 -*-
"""
test_security.py - Unit tests for security module
Tests file validation (size, extension, encoding)
"""
import pytest
from security import FileValidator
from config_system import config

class TestFileValidator:
    """Test FileValidator class."""
    
    def test_valid_file(self):
        """Test valid file passes all checks."""
        content = b"Hello, this is a valid file!"
        is_valid, error, decoded = FileValidator.validate_file("test.txt", content)
        
        assert is_valid is True
        assert error is None
        assert decoded == "Hello, this is a valid file!"
    
    def test_file_too_large(self):
        """Test file size limit enforcement."""
        # Create 11 MB file (over 10 MB limit)
        large_content = b"X" * (11 * 1024 * 1024)
        is_valid, error, decoded = FileValidator.validate_file("large.txt", large_content)
        
        assert is_valid is False
        assert "too large" in error.lower()
        assert decoded is None
    
    def test_invalid_extension(self):
        """Test extension whitelist."""
        # .exe not in whitelist
        is_valid, error, decoded = FileValidator.validate_file("malware.exe", b"binary")
        
        assert is_valid is False
        assert "not allowed" in error.lower()
        assert decoded is None
    
    def test_valid_extensions(self):
        """Test all whitelisted extensions."""
        valid_extensions = ['.txt', '.md', '.py', '.js', '.json', '.csv']
        
        for ext in valid_extensions:
            is_valid, _, _ = FileValidator.validate_file(f"file{ext}", b"content")
            assert is_valid is True, f"Extension {ext} should be valid"
    
    def test_invalid_utf8(self):
        """Test UTF-8 encoding validation."""
        # Invalid UTF-8 bytes
        invalid_content = b'\x80\x81\x82\x83'
        is_valid, error, decoded = FileValidator.validate_file("bad.txt", invalid_content)
        
        assert is_valid is False
        assert "encoding" in error.lower()
        assert decoded is None
    
    def test_unicode_content(self):
        """Test valid UTF-8 with unicode characters."""
        content = "Hello 世界 🌍".encode('utf-8')
        is_valid, error, decoded = FileValidator.validate_file("unicode.txt", content)
        
        assert is_valid is True
        assert error is None
        assert "世界" in decoded
        assert "🌍" in decoded
    
    def test_empty_file(self):
        """Test empty file handling."""
        is_valid, error, decoded = FileValidator.validate_file("empty.txt", b"")
        
        assert is_valid is True  # Empty files are valid
        assert decoded == ""
    
    def test_max_size_boundary(self):
        """Test file at exact size limit."""
        # Exactly 10 MB
        exact_size = config.MAX_FILE_SIZE
        content = b"X" * exact_size
        is_valid, _, _ = FileValidator.validate_file("exact.txt", content)
        
        assert is_valid is True  # Should pass at exact limit
        
        # One byte over
        content_over = b"X" * (exact_size + 1)
        is_valid, error, _ = FileValidator.validate_file("over.txt", content_over)
        
        assert is_valid is False
        assert "too large" in error.lower()


class TestPathTraversal:
    """Test path traversal detection."""
    
    def test_path_traversal_dotdot(self):
        """Test detection of .. path traversal."""
        assert FileValidator.is_path_traversal("../etc/passwd") is True
        assert FileValidator.is_path_traversal("..\\windows\\system32") is True
        assert FileValidator.is_path_traversal("foo/../bar") is True
    
    def test_path_traversal_tilde(self):
        """Test detection of ~ home directory traversal."""
        assert FileValidator.is_path_traversal("~/secret") is True
        assert FileValidator.is_path_traversal("~user/.ssh") is True
    
    def test_path_traversal_env_vars(self):
        """Test detection of environment variable injection."""
        assert FileValidator.is_path_traversal("$HOME/secret") is True
        assert FileValidator.is_path_traversal("%USERPROFILE%\\secret") is True
    
    def test_safe_paths(self):
        """Test that safe paths are allowed."""
        assert FileValidator.is_path_traversal("myfile.txt") is False
        assert FileValidator.is_path_traversal("subdir/file.txt") is False
        assert FileValidator.is_path_traversal("path/to/document.pdf") is False
    
    def test_edge_cases(self):
        """Test edge cases in path traversal detection."""
        assert FileValidator.is_path_traversal("") is False
        assert FileValidator.is_path_traversal("file..txt") is False  # .. not as path separator
        assert FileValidator.is_path_traversal("my-file_name.txt") is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
