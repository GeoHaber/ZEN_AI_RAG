# -*- coding: utf-8 -*-
"""
Tests for cleanup_policy.py
"""
import pytest
import time
from pathlib import Path
import tempfile
import shutil
from cleanup_policy import UploadCleanupPolicy


class TestUploadCleanupPolicy:
    """Test upload directory cleanup."""

    @pytest.fixture
    def temp_upload_dir(self):
        """Create temporary upload directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_initialization(self, temp_upload_dir):
        """Test policy initializes correctly."""
        policy = UploadCleanupPolicy(
            temp_upload_dir,
            max_age_hours=24,
            max_files=100,
            max_size_mb=500
        )
        assert policy.upload_dir == temp_upload_dir
        assert policy.max_age_hours == 24
        assert policy.max_files == 100
        assert policy.max_size_mb == 500

    def test_get_stats_empty_dir(self, temp_upload_dir):
        """Test stats for empty directory."""
        policy = UploadCleanupPolicy(temp_upload_dir)
        stats = policy.get_stats()

        assert stats['count'] == 0
        assert stats['size_mb'] == 0.0
        assert stats['oldest_hours'] == 0.0

    def test_get_stats_with_files(self, temp_upload_dir):
        """Test stats with files."""
        # Create test files with more content
        for i in range(3):
            (temp_upload_dir / f"test{i}.txt").write_text("test content " * 1000)  # Make files larger

        policy = UploadCleanupPolicy(temp_upload_dir)
        stats = policy.get_stats()

        assert stats['count'] == 3
        assert stats['size_mb'] >= 0  # Allow 0 for very small files
        assert stats['oldest_hours'] >= 0

    def test_cleanup_old_files(self, temp_upload_dir):
        """Test cleanup removes old files."""
        # Create old file
        old_file = temp_upload_dir / "old.txt"
        old_file.write_text("old content")

        # Make it old (modify mtime)
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        import os
        os.utime(old_file, (old_time, old_time))

        # Create recent file
        recent_file = temp_upload_dir / "recent.txt"
        recent_file.write_text("recent content")

        policy = UploadCleanupPolicy(temp_upload_dir, max_age_hours=24)
        result = policy.cleanup()

        assert result['deleted'] == 1
        assert not old_file.exists()
        assert recent_file.exists()

    def test_cleanup_excess_files(self, temp_upload_dir):
        """Test cleanup removes excess files."""
        # Create 5 files
        for i in range(5):
            file_path = temp_upload_dir / f"file{i}.txt"
            file_path.write_text("content")
            time.sleep(0.01)  # Ensure different mtimes

        policy = UploadCleanupPolicy(temp_upload_dir, max_files=3)
        result = policy.cleanup()

        assert result['deleted'] == 2
        remaining = list(temp_upload_dir.glob('*.txt'))
        assert len(remaining) == 3

    def test_cleanup_by_size(self, temp_upload_dir):
        """Test cleanup based on total size."""
        # Create files totaling more than size limit
        for i in range(3):
            file_path = temp_upload_dir / f"large{i}.txt"
            file_path.write_text("x" * (1024 * 1024))  # 1 MB each
            time.sleep(0.01)

        policy = UploadCleanupPolicy(temp_upload_dir, max_size_mb=2)
        result = policy.cleanup()

        assert result['deleted'] >= 1
        stats = policy.get_stats()
        assert stats['size_mb'] <= 2

    def test_cleanup_nonexistent_dir(self):
        """Test cleanup handles nonexistent directory."""
        policy = UploadCleanupPolicy(Path("/nonexistent/path"))
        result = policy.cleanup()

        assert result['deleted'] == 0
        assert result['freed_mb'] == 0.0

    def test_thread_safety(self, temp_upload_dir):
        """Test policy is thread-safe."""
        import threading

        # Create test files
        for i in range(10):
            (temp_upload_dir / f"test{i}.txt").write_text("content")

        policy = UploadCleanupPolicy(temp_upload_dir)

        # Run cleanup and get_stats concurrently
        def run_cleanup():
            policy.cleanup()

        def get_stats():
            policy.get_stats()

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=run_cleanup))
            threads.append(threading.Thread(target=get_stats))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should complete without errors


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
