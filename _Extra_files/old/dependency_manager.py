import os
import re
import sys
import time
import subprocess
from pathlib import Path
from typing import Set, Dict, List

def safe_print(*args, **kwargs):
    """Thread-safe print with automatic flush=True."""
    kwargs['flush'] = kwargs.get('flush', True)
    print(*args, **kwargs)

def get_imports_from_file(file_path: Path) -> Set[str]:
    """Extract top-level imports from a python file."""
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Match "import package" and "from package import ..."
        patterns = [
            r'^import\s+([a-zA-Z0-9_]+)',
            r'^from\s+([a-zA-Z0-9_]+)\s+import'
        ]
        
        for line in content.splitlines():
            for pattern in patterns:
                match = re.match(pattern, line.strip())
                if match:
                    imports.add(match.group(1))
    except Exception as e:
        safe_print(f"Error reading {file_path}: {e}")
    return imports

def scan_project_imports(root_dir: Path) -> Set[str]:
    """Scan all python files in the project for imports."""
    all_imports = set()
    skip_dirs = {'.git', '__pycache__', 'venv', '.venv', 'env'}
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            if file.endswith('.py'):
                all_imports.update(get_imports_from_file(Path(root) / file))
    return all_imports

# Mapping of import names to PyPI package names
IMPORT_TO_PACKAGE = {
    'nicegui': 'nicegui',
    'fastapi': 'fastapi',
    'uvicorn': 'uvicorn',
    'httpx': 'httpx',
    'websockets': 'websockets',
    'psutil': 'psutil',
    'bs4': 'beautifulsoup4',
    'aiohttp': 'aiohttp',
    'aiofiles': 'aiofiles',
    'numpy': 'numpy',
    'qdrant_client': 'qdrant-client',
    'sentence_transformers': 'sentence-transformers',
    'rank_bm25': 'rank-bm25',
    'pypdf': 'pypdf',
    'pdfplumber': 'pdfplumber',
    'requests': 'requests',
    'openai': 'openai',
    'dotenv': 'python-dotenv',
    'tiktoken': 'tiktoken',
    'tqdm': 'tqdm',
    'scipy': 'scipy',
    'pandas': 'pandas',
    'onnxruntime': 'onnxruntime',
    'markdown': 'markdown',
    'bleach': 'bleach',
    'pyttsx3': 'pyttsx3',
    'speech_recognition': 'SpeechRecognition',
    'pyaudio': 'PyAudio',
    'colorlog': 'colorlog',
    'starlette': 'starlette',
    'multipart': 'python-multipart',
    'hf_transfer': 'hf_transfer',
    'cv2': 'opencv-python',
    'PIL': 'Pillow',
    'pytesseract': 'pytesseract',
    'fitz': 'pymupdf',
    'faiss': 'faiss-cpu'
}

def generate_requirements(root_dir: Path):
    """Generate requirements.txt based on scanned imports."""
    scanned = scan_project_imports(root_dir)
    
    # Standard library modules
    std_lib = {
        'os', 'sys', 're', 'pathlib', 'time', 'hashlib', 'logging', 
        'threading', 'collections', 'math', 'typing', 'json', 'random',
        'asyncio', 'uuid', 'datetime', 'subprocess', 'shutil', 'abc',
        'functools', 'inspect', 'traceback', 'base64', 'io', 'tempfile',
        'argparse', 'queue', 'socket', 'pickle', 'copy', 'enum', 'glob',
        'csv', 'ctypes', 'dataclasses', 'platform', 'signal', 'sqlite3',
        'statistics', 'string', 'unittest', 'urllib', 'wave', 'zipfile',
        'itertools', 'operator', 'importlib', 'selectors', 'contextlib',
        'http', 'urllib', 'xml', 'concurrent', 'multiprocessing',
        'pkg_resources', 'distutils', 'warnings', 'site', 'inspect',
        'traceback', 'array', 'bisect', 'heapq', 'mimetypes', 'textwrap'
    }
    
    # Filter out local imports
    # Get all .py files stems in project
    local_stems = {p.stem for p in root_dir.glob('**/*.py')}
    # Get all top-level directory names
    local_dirs = {p.name for p in root_dir.iterdir() if p.is_dir()}
    
    local_modules = local_stems | local_dirs
    local_modules.add('dependency_manager') # self reference
    
    # Force mapping for these if detected
    known_packages = set(IMPORT_TO_PACKAGE.values())

    needed_packages = set()
    for imp in scanned:
        if imp in std_lib:
            continue
        
        if imp in local_modules:
            continue

        pkg = IMPORT_TO_PACKAGE.get(imp, imp)
        
        # Additional heuristic: if it's not in our map AND it's a stem of a local file, skip
        if imp in local_stems:
            continue
            
        # If it's all lowercase and not in mapping, and looks like a project file (starts with agent_, etc)
        if imp.startswith(('agent_', 'search_', 'model_', 'zena_', 'startup_', 'update_')):
            continue

        if pkg:
            needed_packages.add(pkg)
            
    # Write to requirements.txt
    req_file = root_dir / "requirements.txt"
    # Filter out empty or obviously wrong ones
    final_packages = {p for p in needed_packages if p and p not in local_modules and p not in std_lib}
    
    sorted_packages = sorted(list(final_packages))
    
    with open(req_file, 'w', encoding='utf-8') as f:
        f.write("# Auto-generated requirements for ZenAI RAG project\n")
        f.write("# Generated on: " + time.ctime() + "\n\n")
        for pkg in sorted_packages:
            f.write(f"{pkg}\n")
            
    safe_print(f"Generated {req_file} with {len(sorted_packages)} packages.")
    return sorted_packages

def check_updates():
    """Check if installed libraries are up to date."""
    safe_print("\n🔍 Checking for outdated libraries...")
    try:
        # Run pip list --outdated
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            import json
            outdated = json.loads(result.stdout)
            if not outdated:
                safe_print("✅ All libraries are up to date!")
            else:
                safe_print(f"⚠️ Found {len(outdated)} outdated libraries:")
                for item in outdated:
                    # Some pip versions use 'version' instead of 'installed_version'
                    inst_v = item.get('version') or item.get('installed_version', 'Unknown')
                    latest_v = item.get('latest_version', 'Unknown')
                    safe_print(f" - {item['name']}: {inst_v} -> {latest_v}")
        else:
            safe_print(f"❌ Error checking updates: {result.stderr}")
    except Exception as e:
        safe_print(f"❌ Pip check failed: {e}")

if __name__ == "__main__":
    root = Path(os.getcwd())
    packages = generate_requirements(root)
    check_updates()
