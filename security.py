# -*- coding: utf-8 -*-
"""
security.py - Security validation utilities for ZenAI
"""
from pathlib import Path
from typing import Tuple, Optional
from config_system import config, EMOJI
import os

def validate_path(user_path: str, allowed_roots: Optional[list[Path]] = None) -> Path:
    """Resolve and validate a user-supplied path.

    - Expands user (~), resolves symlinks where possible, and ensures the
      resulting path is contained within one of the allowed_roots (by default
      `config.BASE_DIR` and `config.MODEL_DIR`).
    - Rejects obvious system paths.
    """
    if not user_path:
        raise ValueError("Empty path")

    p = Path(user_path).expanduser()
    try:
        # Resolve symlinks explicitly. 'strict=True' raises FileNotFoundError if it doesn't exist,
        # which is fine as we want to validate existing paths usually, OR we want to ensure
        # the parent exists. But for RAG/Uploads, the file usually exists.
        # However, to be safe against non-existent target paths (e.g. upload destination), 
        # we resolve and then check parents.
        # For existing files:
        if p.exists():
            resolved = p.resolve(strict=True)
            # Check for Symlink explicitly if platform supports it
            # (On Windows, resolve() follows symlinks, so we check if the resolved path is different 
            # from absolute path, OR use is_symlink() before resolve)
            if p.is_symlink():
                 raise ValueError("Symlinks not allowed")
        else:
             # For new files, resolve parent
             resolved = p.parent.resolve(strict=True) / p.name
    except Exception as e:
        # verification failed
        raise ValueError(f"Invalid path resolution: {e}")

    # Default allowed roots
    if allowed_roots is None:
        allowed_roots = [Path(config.BASE_DIR).resolve(), Path(config.MODEL_DIR).resolve()]

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
    def validate_magic_numbers(content: bytes, filename: str) -> bool:
        """
        Validate file content against magic numbers (signatures) for common types.
        A poor man's python-magic to avoid dependencies.
        """
        ext = Path(filename).suffix.lower()
        
        # Magic Signatures
        # PDF: %PDF- (25 50 44 46 2D)
        if ext == '.pdf':
            return content.startswith(b'%PDF-')
        
        # PNG: .PNG (89 50 4E 47 0D 0A 1A 0A)
        if ext == '.png':
            return content.startswith(b'\x89PNG\r\n\x1a\n')
            
        # JPEG: FF D8 FF
        if ext in ['.jpg', '.jpeg']:
            return content.startswith(b'\xff\xd8\xff')
            
        # TXT / MD / JSON: Check for UTF-8 and no binary control chars (simple heuristic)
        if ext in ['.txt', '.md', '.json', '.py', '.js', '.csv']:
            try:
                # Must be valid UTF-8
                text = content.decode('utf-8')
                # Check for excessive null bytes which might indicate binary
                if text.count('\x00') > 0:
                    return False
                return True
            except UnicodeDecodeError:
                return False
                
        # For other types, we default to allowing if extension is consistent
        # This is a baseline hardening; specific parsers should also validate.
        return True

    @staticmethod
    def validate_file(
        filename: str, 
        content: bytes
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate uploaded file for security.
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
            
        # MAGIC NUMBER CHECK (New)
        if not FileValidator.validate_magic_numbers(content, filename):
            error = f"File content does not match extension '{file_ext}'"
            logger.warning(f"[Security] {error}: {filename}")
            return (False, error, None)
        
        # Encoding check - only if it claims to be text
        decoded = None
        if file_ext in ['.txt', '.md', '.json', '.csv', '.py', '.js']:
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
        """Sanitize file content before passing to LLM."""
        # Truncate if too long
        if len(content) > max_length:
            logger.warning(f"[Security] Content truncated from {len(content)} to {max_length} chars")
            content = content[:max_length] + "\n\n[... content truncated ...]"
        
        # Remove null bytes and other problematic characters
        content = content.replace('\x00', '')
        
        return content
