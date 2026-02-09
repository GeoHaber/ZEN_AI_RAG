# -*- coding: utf-8 -*-
"""
cleanup_policy.py - Automated cleanup for uploads directory
"""
import logging
import time
from pathlib import Path
from typing import Optional
import threading

logger = logging.getLogger(__name__)


class UploadCleanupPolicy:
    """Manages cleanup of old uploaded files."""

    def __init__(
        self,
        upload_dir: Path,
        max_age_hours: int = 24,
        max_files: int = 100,
        max_size_mb: int = 500
    ):
        """
        Initialize cleanup policy.

        Args:
            upload_dir: Directory containing uploaded files
            max_age_hours: Delete files older than this (hours)
            max_files: Maximum number of files to keep
            max_size_mb: Maximum total size in MB
        """
        self.upload_dir = Path(upload_dir)
        self.max_age_hours = max_age_hours
        self.max_files = max_files
        self.max_size_mb = max_size_mb
        self._lock = threading.Lock()

    def cleanup(self) -> dict:
        """
        Run cleanup based on policy.

        Returns:
            dict with cleanup stats: {'deleted': int, 'freed_mb': float}
        """
        with self._lock:
            if not self.upload_dir.exists():
                logger.debug(f"[Cleanup] Upload directory does not exist: {self.upload_dir}")
                return {'deleted': 0, 'freed_mb': 0.0}

            files = list(self.upload_dir.glob('*'))
            if not files:
                return {'deleted': 0, 'freed_mb': 0.0}

            deleted_count = 0
            freed_bytes = 0

            # Step 1: Delete files older than max_age_hours
            current_time = time.time()
            max_age_seconds = self.max_age_hours * 3600

            for file_path in files:
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        try:
                            size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_count += 1
                            freed_bytes += size
                            logger.info(f"[Cleanup] Deleted old file: {file_path.name} (age: {file_age / 3600:.1f}h)")
                        except Exception as e:
                            logger.error(f"[Cleanup] Failed to delete {file_path.name}: {e}")

            # Refresh file list after age-based cleanup
            files = [f for f in self.upload_dir.glob('*') if f.is_file()]

            # Step 2: If still too many files, delete oldest until under limit
            if len(files) > self.max_files:
                # Sort by modification time (oldest first)
                files_by_time = sorted(files, key=lambda f: f.stat().st_mtime)
                files_to_delete = len(files) - self.max_files

                for file_path in files_by_time[:files_to_delete]:
                    try:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_count += 1
                        freed_bytes += size
                        logger.info(f"[Cleanup] Deleted excess file: {file_path.name}")
                    except Exception as e:
                        logger.error(f"[Cleanup] Failed to delete {file_path.name}: {e}")

            # Step 3: If total size exceeds limit, delete oldest until under size limit
            files = [f for f in self.upload_dir.glob('*') if f.is_file()]
            total_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)

            if total_size_mb > self.max_size_mb:
                # Sort by modification time (oldest first)
                files_by_time = sorted(files, key=lambda f: f.stat().st_mtime)

                for file_path in files_by_time:
                    if total_size_mb <= self.max_size_mb:
                        break

                    try:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_count += 1
                        freed_bytes += size
                        total_size_mb -= size / (1024 * 1024)
                        logger.info(f"[Cleanup] Deleted oversized file: {file_path.name}")
                    except Exception as e:
                        logger.error(f"[Cleanup] Failed to delete {file_path.name}: {e}")

            freed_mb = freed_bytes / (1024 * 1024)
            if deleted_count > 0:
                logger.info(f"[Cleanup] Completed: {deleted_count} files deleted, {freed_mb:.2f} MB freed")

            return {'deleted': deleted_count, 'freed_mb': round(freed_mb, 2)}

    def get_stats(self) -> dict:
        """
        Get current upload directory stats.

        Returns:
            dict with stats: {'count': int, 'size_mb': float, 'oldest_hours': float}
        """
        with self._lock:
            if not self.upload_dir.exists():
                return {'count': 0, 'size_mb': 0.0, 'oldest_hours': 0.0}

            files = [f for f in self.upload_dir.glob('*') if f.is_file()]
            if not files:
                return {'count': 0, 'size_mb': 0.0, 'oldest_hours': 0.0}

            total_size = sum(f.stat().st_size for f in files)
            oldest_mtime = min(f.stat().st_mtime for f in files)
            oldest_hours = (time.time() - oldest_mtime) / 3600

            return {
                'count': len(files),
                'size_mb': round(total_size / (1024 * 1024), 2),
                'oldest_hours': round(oldest_hours, 1)
            }


# Global instance
_cleanup_policy: Optional[UploadCleanupPolicy] = None


def get_cleanup_policy(upload_dir: Path = None) -> UploadCleanupPolicy:
    """Get or create global cleanup policy instance."""
    global _cleanup_policy
    if _cleanup_policy is None:
        if upload_dir is None:
            upload_dir = Path(__file__).parent / "uploads"
        _cleanup_policy = UploadCleanupPolicy(
            upload_dir,
            max_age_hours=24,  # Delete files older than 24 hours
            max_files=100,     # Keep max 100 files
            max_size_mb=500    # Keep max 500 MB total
        )
    return _cleanup_policy
