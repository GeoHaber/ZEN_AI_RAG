#!/usr/bin/env python3
"""
Workspace cleanup script - organize ZEN_AI_RAG into clean structure.
Creates: docs/, tests/, scripts/, OLD/ directories
Moves non-essential files to appropriate locations.
"""

import os
import shutil
from pathlib import Path

# Color codes for terminal output
class Colors:
    """Colors class."""
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

ROOT = Path("c:/Users/dvdze/Documents/_Python/Dev/ZEN_AI_RAG")

# Files to move to docs/
DOCS_FILES = {
    '.md': [
        'ARCHITECTURE', 'AUDIO_INJECTION', 'CHANGELOG', 'CLEANUP_VERIFICATION',
        'COMPLETION_STATUS', 'CROSS_PLATFORM', 'DESIGN_REVIEW', 'DOCUMENTATION_STANDARD',
        'FINAL_PHASE', 'FIX_MICROPHONE', 'HOW_TO_RUN', 'INSTALL', 'METRICS_AND_KPI',
        'MICROPHONE', 'MODEL_BROWSER', 'MULTI_LLM', 'PHASE4', 'QUICKSTART', 'QUICK_START',
        'QUICK_REFERENCE', 'README', 'SESSION_COMPLETION', 'USER_MANUAL', 'To_dodo'
    ],
    '.txt': [
        'bench_debug', 'branding_violations', 'crash_log', 'diag_', 'full_test_log',
        'pytest_', 'server_log', 'startup_debug', 'startup_diag', 'ui_fatal', 'ui_traceback',
        'verify_log', 'voice_debug', 'voice_trace', 'zenai_debug', 'nebula_debug',
        'nebula_engine', 'orchestrator_debug'
    ],
    '.log': ['*']  # All log files
}

# Files to move to tests/
TESTS_FILES = [
    'test_*.py', 'run_tests.py', 'pytest.ini', 'verify_*.py', 'verify_install.py'
]

# Files to move to scripts/
SCRIPTS_FILES = [
    'install.py', 'install.bat', 'install.sh', 'cleanup_policy.py',
    'startup_check.py', 'run_all_tests.ps1', 'debug_*.bat', 'capture_crash.bat',
    'dependency_manager.py', 'feature_detection.py', 'intelligent_router.py',
    'state_management.py', 'verify_imports.py', 'verify_server*.py', 'verify_rag.py',
    'setup.py', 'cleanup_workspace.ps1'
]

# Files to move to OLD/
OLD_FILES = [
    'diagnose_*.py', 'debug_*.py', 'debug_*.bat', 'stress_test_*.py',
    'benchmark*.py', 'mini_rag.py', 'mock_backend.py', 'async_backend.py',
    'reproduce_*.py', 'rag_inspector.py', 'rag_verification_script.py',
    'streamlit_*.py', 'ui_components.py', 'phase3_*.py',
    'config_system.py', 'decorators.py', 'security.py', 'semantic_cache.py',
    'utils_temp.py', 'verification_demo.py', 'model_manager.py',
    'check_audio_array.py', 'voice_debug.log'
]

# Essential files to keep in root
ESSENTIAL_FILES = {
    'zena.py', 'start_llm.py', 'config.py', 'requirements.txt',
    'README.md', 'setup.py', 'start_zenAI.bat', 'voice_service.py',
    'settings.py', 'utils.py', 'config.json', 'settings.json',
    'knowledge_base.json'
}

def ensure_dirs():
    """Create necessary directories."""
    dirs = ['docs', 'tests', 'scripts', 'OLD']
    for d in dirs:
        path = ROOT / d
        path.mkdir(exist_ok=True)
        print(f"{Colors.GREEN}[DIR]{Colors.END} {d}/")

def move_file(src, dest_dir):
    """Safely move a file."""
    try:
        src_path = ROOT / src
        dest_path = ROOT / dest_dir / src
        
        if src_path.exists() and not dest_path.exists():
            shutil.move(str(src_path), str(dest_path))
            print(f"{Colors.GREEN}[MOVE]{Colors.END} {src} -> {dest_dir}/")
            return True
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.END} {src}: {e}")
    return False

def move_pattern(pattern, dest_dir):
    """Move files matching a pattern."""
    from glob import glob
    for filepath in glob(str(ROOT / pattern)):
        filename = Path(filepath).name
        try:
            dest_path = ROOT / dest_dir / filename
            if not dest_path.exists():
                shutil.move(filepath, str(dest_path))
                print(f"{Colors.GREEN}[MOVE]{Colors.END} {filename} -> {dest_dir}/")
        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.END} {filename}: {e}")

def cleanup_pycache():
    """Remove __pycache__ directories."""
    for pycache in ROOT.rglob('__pycache__'):
        try:
            shutil.rmtree(pycache)
            print(f"{Colors.GREEN}[DELETE]{Colors.END} {pycache.relative_to(ROOT)}/")
        except Exception as e:
            print(f"{Colors.YELLOW}[SKIP]{Colors.END} {pycache}: {e}")

def main():
    """Main."""
    os.chdir(str(ROOT))
    
    print(f"\n{Colors.CYAN}{Colors.BOLD}=== ZEN_AI_RAG WORKSPACE CLEANUP ==={Colors.END}\n")
    
    # Create directories
    print(f"{Colors.YELLOW}Creating directories...{Colors.END}")
    ensure_dirs()
    
    # Move documentation
    print(f"\n{Colors.YELLOW}Moving documentation files...{Colors.END}")
    move_pattern('*.md', 'docs')
    move_pattern('*.txt', 'docs')
    move_pattern('*.log', 'docs')
    
    # Move test files
    print(f"\n{Colors.YELLOW}Moving test files...{Colors.END}")
    move_pattern('test_*.py', 'tests')
    move_pattern('verify_*.py', 'tests')
    move_file('run_tests.py', 'tests')
    move_file('pytest.ini', 'tests')
    
    # Move script files
    print(f"\n{Colors.YELLOW}Moving script files...{Colors.END}")
    for pattern in SCRIPTS_FILES:
        move_pattern(pattern, 'scripts')
    
    # Move old/diagnostic files
    print(f"\n{Colors.YELLOW}Moving old/non-essential files...{Colors.END}")
    for pattern in OLD_FILES:
        move_pattern(pattern, 'OLD')
    
    # Clean up pycache
    print(f"\n{Colors.YELLOW}Cleaning __pycache__...{Colors.END}")
    cleanup_pycache()
    
    # Report
    print(f"\n{Colors.CYAN}{Colors.BOLD}=== CLEANUP COMPLETE ==={Colors.END}\n")
    
    # Count files
    root_files = len(list(ROOT.glob('*.py'))) + len(list(ROOT.glob('*.bat'))) + len(list(ROOT.glob('*.sh')))
    docs_files = len(list((ROOT / 'docs').glob('*')))
    tests_files = len(list((ROOT / 'tests').glob('*')))
    scripts_files = len(list((ROOT / 'scripts').glob('*')))
    old_files = len(list((ROOT / 'OLD').glob('*')))
    
    print(f"{Colors.GREEN}Root directory:{Colors.END} ~{root_files} essential files")
    print(f"{Colors.GREEN}docs/:{Colors.END} {docs_files} files")
    print(f"{Colors.GREEN}tests/:{Colors.END} {tests_files} files")
    print(f"{Colors.GREEN}scripts/:{Colors.END} {scripts_files} files")
    print(f"{Colors.GREEN}OLD/:{Colors.END} {old_files} files")
    print()

if __name__ == '__main__':
    main()
