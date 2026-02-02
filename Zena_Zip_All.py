import os
import zipfile
import fnmatch
from pathlib import Path
from datetime import datetime

IGNORE_PATTERNS = [
    ".git*", "__pycache__", "*.pyc", "*.pyd", "*.pyo", 
    ".venv", "venv", "env", "node_modules", 
    "*.log", "*.tmp", "*.bak", "*.swp",
    "dist", "build", "*.egg-info",
    "ZenAI_RAG_Source_*.zip", # Don't zip previous zips
    "test_history.json", ".coverage", ".pytest_cache"
]

def load_gitignore(root: Path):
    """Load .gitignore patterns if available."""
    gitignore = root / ".gitignore"
    patterns = []
    if gitignore.exists():
        with open(gitignore, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    return patterns

def should_ignore(path: Path, root: Path, patterns: list):
    """Check if path matches ignore patterns."""
    rel_path = str(path.relative_to(root)).replace("\\", "/")
    name = path.name
    
    # Check explicitly denied patterns first
    for pattern in patterns + IGNORE_PATTERNS:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_path, pattern):
            return True
            
        # Recursive directory check (e.g. models/ should be ignored if listed)
        # Simple heuristic: if any part of the path matches a directory pattern
        parts = rel_path.split("/")
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True
                
    return False

def create_zena_zip():
    base_dir = Path(os.getcwd())
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_zip = base_dir / f"ZenAI_RAG_Source_{date_str}.zip"
    
    print(f"📦 Packaging Source Code: {output_zip.name}")
    
    gitignore_patterns = load_gitignore(base_dir)
    print(f"📝 Loaded {len(gitignore_patterns)} patterns from .gitignore")
    
    count = 0
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_dir):
            # Sort for deterministic output
            dirs.sort()
            files.sort()
            
            root_path = Path(root)
            
            # Skip ignored directories
            if should_ignore(root_path, base_dir, gitignore_patterns):
                dirs[:] = [] # Don't verify children of ignored dirs
                continue
                
            for file in files:
                file_path = root_path / file
                if should_ignore(file_path, base_dir, gitignore_patterns):
                    continue
                
                # Check specifics
                if file.endswith((".py", ".md", ".json", ".html", ".css", ".js", ".bat", ".sh", ".txt", ".ini")):
                    rel_path = file_path.relative_to(base_dir)
                    print(f"  + {rel_path}")
                    zipf.write(file_path, arcname=str(rel_path))
                    count += 1
                
                # Binaries in _bin (explicit include)
                elif "_bin" in str(file_path) and file.endswith((".exe", ".dll")):
                    rel_path = file_path.relative_to(base_dir)
                    print(f"  + {rel_path} (Binary)")
                    zipf.write(file_path, arcname=str(rel_path))
                    count += 1

    print(f"\n✅ Done! Added {count} files to {output_zip.name}")

if __name__ == "__main__":
    create_zena_zip()
