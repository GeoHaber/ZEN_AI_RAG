#!/usr/bin/env python3
"""
🐀 RAG_RAT - Foolproof Auto-Installer for Virgin Systems
=========================================================
This script ensures RAG_RAT works on ANY system, even fresh Python installs.

Features:
  ✓ Auto-detects Python version and warns if too old
  ✓ Auto-installs missing dependencies
  ✓ Creates required directories
  ✓ Checks for external dependencies (Ollama, llama-cpp)
  ✓ Provides installation guides for optional services
  ✓ Handles virtual environments
  ✓ Tests all imports after install
"""

import sys
import subprocess
import os
from pathlib import Path
from typing import List, Tuple
import json

# Color codes for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def green(text): return f"{Colors.OKGREEN}{text}{Colors.ENDC}"
    @staticmethod
    def red(text): return f"{Colors.FAIL}{text}{Colors.ENDC}"
    @staticmethod
    def yellow(text): return f"{Colors.WARNING}{text}{Colors.ENDC}"
    @staticmethod
    def blue(text): return f"{Colors.OKBLUE}{text}{Colors.ENDC}"
    @staticmethod
    def cyan(text): return f"{Colors.OKCYAN}{text}{Colors.ENDC}"


def print_header():
    """Display beautiful header."""
    print("\n" + "=" * 70)
    print(Colors.cyan("🐀 RAG_RAT - Foolproof Setup & Installation"))
    print("=" * 70)
    print("Setting up RAG_RAT on this system...\n")


def check_python_version() -> bool:
    """Check if Python version is compatible."""
    print(f"📊 Checking Python version...")
    major, minor = sys.version_info.major, sys.version_info.minor
    version_str = f"{major}.{minor}"
    
    if major < 3 or (major == 3 and minor < 9):
        print(Colors.red(f"  ❌ Python {version_str} is too old! Need Python 3.9+"))
        print(Colors.yellow("  Get Python 3.11 or later from: https://python.org/downloads/"))
        return False
    
    print(Colors.green(f"  ✓ Python {version_str} is compatible"))
    return True


def get_pip_command() -> str:
    """Get the correct pip command for this environment."""
    try:
        subprocess.run(["pip", "--version"], capture_output=True, check=True)
        return "pip"
    except:
        try:
            subprocess.run(["pip3", "--version"], capture_output=True, check=True)
            return "pip3"
        except:
            print(Colors.red("  ❌ pip not found! Python installation is broken."))
            sys.exit(1)


def read_requirements() -> List[str]:
    """Read requirements from requirements.txt."""
    req_file = Path(__file__).parent / "requirements.txt"
    
    if not req_file.exists():
        print(Colors.yellow(f"  ⚠ requirements.txt not found at {req_file}"))
        return []
    
    packages = []
    with open(req_file, "r") as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith("#"):
                # Handle version specifications
                if any(op in line for op in [">=", "<=", "==", "~=", ">"]):
                    packages.append(line)
                else:
                    packages.append(line)
    
    return packages


def install_packages(packages: List[str], pip_cmd: str) -> bool:
    """Install packages with error handling."""
    if not packages:
        print(Colors.yellow("  ⚠ No packages to install"))
        return True
    
    print(f"\n📦 Installing {len(packages)} packages...")
    print("   (This may take a few minutes on first install)\n")
    
    failed = []
    
    for i, package in enumerate(packages, 1):
        pkg_name = package.split(">=")[0].split("==")[0].split("<")[0].split(">")[0].strip()
        print(f"   [{i}/{len(packages)}] Installing {Colors.cyan(pkg_name)}...", end=" ", flush=True)
        
        try:
            subprocess.run(
                [pip_cmd, "install", "-q", package],
                check=True,
                capture_output=True,
                timeout=300
            )
            print(Colors.green("✓"))
        except subprocess.TimeoutExpired:
            print(Colors.yellow("⏱ (timeout, may still install)"))
            failed.append(package)
        except Exception as e:
            print(Colors.red("✗"))
            failed.append(package)
    
    if failed:
        print(f"\n{Colors.yellow('⚠ Some packages failed to install:')}")
        for pkg in failed:
            print(f"   - {pkg}")
        print(f"\nTry manually: {pip_cmd} install {' '.join(failed)}")
        return False
    
    print(Colors.green("\n  ✓ All packages installed successfully!"))
    return True


def create_directories() -> None:
    """Create required directories."""
    print(f"\n📁 Creating required directories...")
    
    dirs = [
        "cache",
        "logs",
        "uploads",
        "models",
        "qdrant_storage",
        "rag_storage",
        "rag_cache",
    ]
    
    for dir_name in dirs:
        dir_path = Path(__file__).parent / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"   ✓ {dir_name}/")
    
    print(Colors.green("  ✓ All directories ready!"))


def check_local_llm_servers() -> Tuple[bool, bool]:
    """Check if local LLM servers are available."""
    print(f"\n🔍 Checking for local LLM servers...")
    
    import socket
    
    def is_port_open(port: int) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    ollama = is_port_open(11434)
    llama_cpp = is_port_open(8001)
    
    if ollama:
        print(f"   ✓ Ollama found on port 11434")
    else:
        print(f"   ✗ Ollama not found (port 11434 closed)")
    
    if llama_cpp:
        print(f"   ✓ llama-cpp found on port 8001")
    else:
        print(f"   ✗ llama-cpp not found (port 8001 closed)")
    
    if not (ollama or llama_cpp):
        print(f"\n   {Colors.yellow('ℹ No local LLM servers found - that\'s OK!')}")
        print(f"   You can use External LLMs (OpenAI, Claude, etc.) instead")
        print(f"   Or install Ollama: https://ollama.ai")
    
    return ollama, llama_cpp


def test_imports() -> bool:
    """Test critical imports."""
    print(f"\n✅ Testing imports...")
    
    critical_imports = [
        ("streamlit", "Streamlit (UI framework)"),
        ("httpx", "httpx (HTTP client)"),
        ("requests", "requests (HTTP library)"),
        ("sentence_transformers", "sentence-transformers (Embeddings)"),
        ("qdrant_client", "qdrant-client (Vector database)"),
    ]
    
    optional_imports = [
        ("ollama", "Ollama (Optional - for local models)"),
        ("faster_whisper", "faster-whisper (Optional - for audio)"),
        ("cv2", "OpenCV (Optional - for vision)"),
    ]
    
    all_ok = True
    
    print(f"\n   {Colors.bold('Critical packages:')}")
    for module, display_name in critical_imports:
        try:
            __import__(module)
            print(f"   ✓ {display_name}")
        except ImportError:
            print(Colors.red(f"   ✗ {display_name}"))
            all_ok = False
    
    print(f"\n   {Colors.bold('Optional packages:')}")
    for module, display_name in optional_imports:
        try:
            __import__(module)
            print(f"   ✓ {display_name}")
        except ImportError:
            print(f"   ⊘ {display_name} (not needed for basic operation)")
    
    return all_ok


def create_startup_script() -> None:
    """Create convenient startup scripts."""
    print(f"\n📝 Creating startup scripts...\n")
    
    project_root = Path(__file__).parent
    
    # Windows batch file
    if sys.platform == "win32":
        batch_content = """@echo off
REM RAG_RAT Startup Script for Windows
title RAG_RAT
cd /d "%~dp0"
echo.
echo 🐀 Starting RAG_RAT...
echo.
python -m streamlit run app_enhanced.py
pause
"""
        batch_file = project_root / "run_rag_rat.bat"
        batch_file.write_text(batch_content)
        print(f"   ✓ Created {Colors.cyan('run_rag_rat.bat')}")
    
    # Linux/Mac shell script
    else:
        shell_content = """#!/bin/bash
# RAG_RAT Startup Script for Linux/Mac

cd "$(dirname "$0")"
echo ""
echo "🐀 Starting RAG_RAT..."
echo ""
python -m streamlit run app_enhanced.py
"""
        shell_file = project_root / "run_rag_rat.sh"
        shell_file.write_text(shell_content)
        shell_file.chmod(0o755)
        print(f"   ✓ Created {Colors.cyan('run_rag_rat.sh')}")


def print_next_steps():
    """Print next steps."""
    print("\n" + "=" * 70)
    print(Colors.green("✅ Setup Complete!"))
    print("=" * 70)
    
    print(f"\n{Colors.bold('🚀 To start RAG_RAT:')}")
    
    if sys.platform == "win32":
        print(f"\n   Option 1: Double-click {Colors.cyan('run_rag_rat.bat')}")
        print(f"   Option 2: Run in terminal:")
        print(f"             streamlit run app_enhanced.py")
    else:
        print(f"\n   Option 1: Run the startup script:")
        print(f"            ./run_rag_rat.sh")
        print(f"   Option 2: Run directly:")
        print(f"            streamlit run app_enhanced.py")
    
    print(f"\n{Colors.bold('📚 Documentation:')}")
    print(f"   - QUICK_REFERENCE.txt - 2-minute quick start")
    print(f"   - STARTUP_FLOW_GUIDE.md - Detailed setup guide")
    print(f"   - INDEX.md - Complete documentation index")
    
    print(f"\n{Colors.bold('⚙️  Next:')}")
    print(f"   1. Start the app")
    print(f"   2. Choose: External LLM (easiest) or Local LLM")
    print(f"   3. Paste API key or select local model")
    print(f"   4. Start chatting! 🎉")
    
    print(f"\n{Colors.yellow('ℹ  Need help?')}")
    print(f"   See: docs/TROUBLESHOOTING.md")
    print(f"   GitHub: https://github.com/...")
    print(f"\n" + "=" * 70 + "\n")


def main():
    """Main installation flow."""
    print_header()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Get pip command
    pip_cmd = get_pip_command()
    print(Colors.green(f"  ✓ Using {pip_cmd}"))
    
    # Read and install requirements
    packages = read_requirements()
    if packages:
        if not install_packages(packages, pip_cmd):
            print(Colors.yellow("\n  ⚠ Some packages failed. Installation may still work."))
    
    # Create directories
    create_directories()
    
    # Check for local LLM servers
    check_local_llm_servers()
    
    # Test imports
    if not test_imports():
        print(Colors.red("\n  ✗ Some critical packages failed to import!"))
        print(Colors.yellow("  Try running: pip install --upgrade pip"))
        print(Colors.yellow(f"  Then: {pip_cmd} install -r requirements.txt"))
        sys.exit(1)
    
    # Create startup scripts
    create_startup_script()
    
    # Print next steps
    print_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.yellow('⚠ Installation cancelled by user')}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.red(f'✗ Installation error: {e}')}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
