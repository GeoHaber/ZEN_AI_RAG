"""
directory_scanner.py - Local directory RAG indexing
"""
import os
import time
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class DirectoryScanner:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.documents = []
        self.supported_extensions = {
            '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml',
            '.csv', '.log', '.yaml', '.yml', '.ini', '.cfg', '.conf',
            '.rst', '.tex', '.sh', '.bat', '.ps1', '.c', '.cpp', '.h',
            '.java', '.go', '.rs', '.php', '.rb', '.swift', '.kt'
        }
        self.skip_dirs = {
            '__pycache__', '.git', '.svn', 'node_modules', '.venv', 'venv',
            'env', '.env', 'dist', 'build', '.idea', '.vscode', 'target',
            '.cache', 'cache', 'tmp', 'temp', '.pytest_cache', '.mypy_cache'
        }
        self.max_file_size = 1024 * 1024  # 1 MB max per file
    
    def should_skip_dir(self, dir_path: Path) -> bool:
        """Check if directory should be skipped."""
        return dir_path.name in self.skip_dirs or dir_path.name.startswith('.')
    
    def should_index_file(self, file_path: Path) -> bool:
        """Check if file should be indexed."""
        # Check extension
        if file_path.suffix.lower() not in self.supported_extensions:
            return False
        
        # Check size
        try:
            if file_path.stat().st_size > self.max_file_size:
                logger.debug(f"[DirScanner] Skipping large file: {file_path}")
                return False
        except:
            return False
        
        return True
    
    def read_file_safe(self, file_path: Path) -> str:
        """Safely read file content."""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                logger.error(f"[DirScanner] Error reading {file_path}: {e}")
                return ""
        
        logger.warning(f"[DirScanner] Could not decode {file_path}")
        return ""
    
    def scan(self, max_files: int = 1000) -> List[Dict]:
        """Recursively scan directory and extract text content."""
        start_time = time.time()
        file_count = 0
        
        logger.info(f"[DirScanner] Starting scan of {self.root_dir}")
        
        for root, dirs, files in os.walk(self.root_dir):
            root_path = Path(root)
            
            # Filter out directories to skip
            dirs[:] = [d for d in dirs if not self.should_skip_dir(root_path / d)]
            
            for file in files:
                if file_count >= max_files:
                    logger.info(f"[DirScanner] Reached max files limit: {max_files}")
                    break
                
                file_path = root_path / file
                
                if not self.should_index_file(file_path):
                    continue
                
                try:
                    file_start = time.time()
                    content = self.read_file_safe(file_path)
                    
                    if len(content) > 50:  # Skip empty/tiny files
                        relative_path = file_path.relative_to(self.root_dir)
                        
                        self.documents.append({
                            "url": str(file_path),
                            "title": str(relative_path),
                            "content": content,
                            "extension": file_path.suffix,
                            "size": len(content)
                        })
                        
                        file_time = time.time() - file_start
                        file_count += 1
                        
                        if file_count % 100 == 0:
                            logger.info(f"[DirScanner] Indexed {file_count} files...")
                        
                        logger.debug(f"[DirScanner] ✅ Indexed: {relative_path} ({len(content)} chars) | Time: {file_time:.2f}s")
                
                except Exception as e:
                    logger.error(f"[DirScanner] Error processing {file_path}: {e}")
            
            if file_count >= max_files:
                break
        
        total_time = time.time() - start_time
        total_size = sum(doc['size'] for doc in self.documents)
        
        logger.info(f"[DirScanner] ✅ Completed: {len(self.documents)} files in {total_time:.2f}s")
        logger.info(f"[DirScanner] Total content: {total_size / 1024:.1f} KB ({total_size / (1024*1024):.2f} MB)")
        
        return self.documents
    
    def get_stats(self) -> Dict:
        """Get scanning statistics."""
        if not self.documents:
            return {}
        
        extensions = {}
        for doc in self.documents:
            ext = doc['extension']
            extensions[ext] = extensions.get(ext, 0) + 1
        
        return {
            'total_files': len(self.documents),
            'total_size': sum(doc['size'] for doc in self.documents),
            'extensions': extensions,
            'root_dir': str(self.root_dir)
        }
