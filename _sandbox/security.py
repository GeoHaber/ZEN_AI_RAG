# -*- coding: utf-8 -*-
"""
security.py - Security validation utilities for ZenAI
"""
from pathlib import Path
from typing import Tuple, Optional
from config_system import config, EMOJI
from config import BASE_DIR, MODEL_DIR
import os

def validate_path(user_path: str, allowed_roots: Optional[list[Path]] = None) -> Path:
    """Resolve and validate a user-supplied path.

    - Expands user (~), resolves symlinks where possible, and ensures the
      resulting path is contained within one of the allowed_roots (by default
      `BASE_DIR` and `MODEL_DIR`).
    - Rejects obvious system paths.
    """
    if not user_path:
        raise ValueError("Empty path")

    p = Path(user_path).expanduser()
    try:
        resolved = p.resolve(strict=False)
    except Exception:
        resolved = p

    # Default allowed roots
    if allowed_roots is None:
        allowed_roots = [Path(BASE_DIR).resolve(), Path(MODEL_DIR).resolve()]

    # Reject system paths explicitly
    sys_roots = [Path('/usr'), Path('/bin'), Path('/etc'), Path('/Windows'), Path('/Program Files'), Path('/System')]
    # On Windows also include C:\Windows paths
    if os.name == 'nt':
        sys_roots.extend([Path(r) for r in [os.environ.get('SystemRoot', 'C:\\Windows'), 'C:\\Program Files']])

    for root in sys_roots:
        try:
            if resolved.is_relative_to(root.resolve()):
                raise ValueError("Access to system paths is denied")
        except Exception:
            # Path.is_relative_to may raise on some platforms; ignore and continue
            pass

    # Ensure resolved path is within allowed roots
    for root in allowed_roots:
        try:
            if resolved.is_relative_to(root):
                return resolved
        except Exception:
            # fallback to manual check
            if str(resolved).startswith(str(root)):
                return resolved

    raise ValueError(f"Path {user_path} is not inside allowed directories")
import logging

logger = logging.getLogger(__name__)


class FileValidator:
    """Validate uploaded files for security."""
    
    @staticmethod
    def is_path_traversal(filename: str) -> bool:
        """
        Check if filename contains path traversal attempts.
        
        Args:
            filename: Name of the uploaded file
            
        Returns:
            True if path traversal detected, False otherwise
        """
        if not filename:
            return False
        
        # Normalize path separators for cross-platform check
        normalized = filename.replace('\\', '/')
        
        # Check for directory traversal patterns (.. as path component)
        # Split by / and check each component
        parts = normalized.split('/')
        for part in parts:
            # ".." as a standalone path component is traversal
            if part == '..':
                return True
            # Home directory reference
            if part.startswith('~'):
                return True
        
        # Check for environment variable injection
        if '$' in filename or '%' in filename:
            return True
        
        # Check if starts with root
        if normalized.startswith('/'):
            return True
            
        return False
    
    @staticmethod
    def validate_file(
        filename: str, 
        content: bytes
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate uploaded file for security.
        
        Args:
            filename: Name of the uploaded file
            content: Raw bytes content
        
        Returns:
            Tuple of (is_valid, error_message, decoded_content)
            - is_valid: True if file passes all checks
            - error_message: Error description if validation fails, None otherwise
            - decoded_content: UTF-8 decoded string if valid, None otherwise
        """
        # Path traversal check
        if FileValidator.is_path_traversal(filename):
            error = "Invalid filename (path traversal detected)"
            logger.warning(f"[Security] {error}: {filename}")
            return (False, error, None)
        
        # Size check
        if len(content) > config.MAX_FILE_SIZE:
            size_mb = len(content) / (1024 * 1024)
            max_mb = config.MAX_FILE_SIZE / (1024 * 1024)
            error = f"File too large ({size_mb:.1f} MB, max {max_mb:.0f} MB)"
            logger.warning(f"[Security] {error}: {filename}")
            return (False, error, None)
        
        # Extension check
        file_ext = Path(filename).suffix.lower()
        if file_ext not in config.ALLOWED_EXTENSIONS:
            error = f"File type '{file_ext}' not allowed"
            logger.warning(f"[Security] {error}: {filename}")
            return (False, error, None)
        
        # Encoding check - must be valid UTF-8
        try:
            decoded = content.decode('utf-8', errors='strict')
        except UnicodeDecodeError as e:
            error = "Invalid file encoding (must be UTF-8)"
            logger.warning(f"[Security] {error}: {filename} - {e}")
            return (False, error, None)
        
        # All checks passed
        logger.info(f"[Security] File validated: {filename} ({len(content)} bytes)")
        return (True, None, decoded)
    
    @staticmethod
    def sanitize_content(content: str, max_length: int = 100000) -> str:
        """
        Sanitize file content before passing to LLM.
        
        Args:
            content: Raw file content
            max_length: Maximum allowed length
        
        Returns:
            Sanitized content
        """
        # Truncate if too long
        if len(content) > max_length:
            logger.warning(f"[Security] Content truncated from {len(content)} to {max_length} chars")
            content = content[:max_length] + "\n\n[... content truncated ...]"
        
        # Remove null bytes and other problematic characters
        content = content.replace('\x00', '')
        
        return content
