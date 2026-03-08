#!/usr/bin/env python3
"""
🐀 RAG_RAT - Pre-flight Checks Before App Start
===============================================
This module runs before the Streamlit app to ensure all dependencies are ready.
If something is missing, it provides clear guidance on how to fix it.
"""

import sys
import os
import subprocess
import socket
import importlib
from pathlib import Path
from typing import Tuple, List, Dict, Optional
import json

# =============================================================================
# STARTUP CHECK CONFIGURATION
# =============================================================================

CRITICAL_MODULES = [
    "streamlit",
    "httpx",
    "requests",
    "sentence_transformers",
    "qdrant_client",
]

OPTIONAL_MODULES = [
    "ollama",
    "faster_whisper",
    "cv2",
    "PyPDF2",
    "pydantic",
]

# =============================================================================
# COLOR OUTPUT
# =============================================================================


class Color:
    """ANSI color codes."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"

    @staticmethod
    def strip(text: str) -> str:
        """Remove color codes from text."""
        for attr in dir(Color):
            if not attr.startswith("_") and attr != "strip":
                text = text.replace(getattr(Color, attr), "")
        return text


# =============================================================================
# LOGGING & REPORTING
# =============================================================================


class StartupLogger:
    """Simple logger for startup checks."""

    def __init__(self):
        self.checks: List[Dict[str, str]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def success(self, msg: str):
        """Log success."""
        # [X-Ray auto-fix] print(f"{Color.GREEN}✓{Color.END} {msg}")
        self.checks.append({"status": "ok", "message": msg})

    def error(self, msg: str):
        """Log error."""
        # [X-Ray auto-fix] print(f"{Color.RED}✗{Color.END} {msg}")
        self.checks.append({"status": "error", "message": msg})
        self.errors.append(msg)

    def warning(self, msg: str):
        """Log warning."""
        # [X-Ray auto-fix] print(f"{Color.YELLOW}⚠{Color.END} {msg}")
        self.checks.append({"status": "warning", "message": msg})
        self.warnings.append(msg)

    def info(self, msg: str):
        """Log info."""
        # [X-Ray auto-fix] print(f"{Color.CYAN}ℹ{Color.END} {msg}")
        self.checks.append({"status": "info", "message": msg})

    def header(self, msg: str):
        """Log section header."""
        # [X-Ray auto-fix] print(f"\n{Color.BOLD}{Color.CYAN}{msg}{Color.END}")

    def get_report(self) -> Dict:
        """Get summary report."""
        return {
            "total": len(self.checks),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "checks": self.checks,
        }


logger = StartupLogger()


# =============================================================================
# CHECK FUNCTIONS
# =============================================================================


def check_python_version() -> bool:
    """Check Python version compatibility."""
    major, minor = sys.version_info.major, sys.version_info.minor

    if major < 3 or (major == 3 and minor < 9):
        logger.error(f"Python {major}.{minor} is too old (need 3.9+)")
        logger.info("Download Python 3.11+: https://python.org/downloads/")
        return False

    logger.success(f"Python {major}.{minor}.{sys.version_info.micro} (compatible)")
    return True


def check_critical_imports() -> bool:
    """Check all critical module imports."""
    logger.header("📦 Checking Critical Packages")

    all_ok = True
    missing = []

    for module in CRITICAL_MODULES:
        try:
            importlib.import_module(module)
            logger.success(f"{module}")
        except ImportError:
            logger.error(f"{module} - NOT INSTALLED")
            missing.append(module)
            all_ok = False

    if missing:
        logger.warning(f"Missing {len(missing)} critical package(s)")
        logger.info(f"Run: pip install {' '.join(missing)}")

    return all_ok


def check_optional_imports() -> None:
    """Check optional imports."""
    logger.header("📚 Checking Optional Packages")

    for module in OPTIONAL_MODULES:
        try:
            importlib.import_module(module)
            logger.success(f"{module} (available)")
        except ImportError:
            logger.warning(f"{module} (not installed - optional)")


def check_local_llm_servers() -> Tuple[bool, bool]:
    """Check for running local LLM servers."""
    logger.header("🖥️  Checking Local LLM Servers")

    def check_port(host: str, port: int, name: str) -> bool:
        """Check port."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                logger.success(f"{name} running on {host}:{port}")
                return True
            else:
                logger.warning(f"{name} not found on {host}:{port}")
                return False
        except Exception as e:
            logger.warning(f"Could not check {name}: {e}")
            return False

    ollama = check_port("localhost", 11434, "Ollama")
    llama_cpp = check_port("localhost", 8001, "llama-cpp")

    if not (ollama or llama_cpp):
        logger.info("No local LLM servers found - will use External LLMs")
        logger.info("To use local models, install Ollama: https://ollama.ai")

    return ollama, llama_cpp


def check_directories() -> bool:
    """Check required directories exist."""
    logger.header("📁 Checking Directory Structure")

    project_root = Path(__file__).parent
    required_dirs = [
        "cache",
        "logs",
        "uploads",
    ]

    all_ok = True

    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            logger.success(f"{dir_name}/ exists")
        else:
            dir_path.mkdir(exist_ok=True)
            logger.success(f"{dir_name}/ created")

    return all_ok


def check_custom_modules() -> bool:
    """Check our custom modules can be imported."""
    logger.header("🐀 Checking RAG_RAT Modules")

    try:
        from config_enhanced import LLMConfig

        logger.success("config_enhanced.py")
    except Exception as e:
        logger.error(f"config_enhanced.py: {e}")
        return False

    try:
        from llm_adapters import LLMFactory, LLMProvider

        logger.success("llm_adapters.py")
    except Exception as e:
        logger.error(f"llm_adapters.py: {e}")
        return False

    try:
        from ui_components_beautiful import apply_theme

        logger.success("ui_components_beautiful.py")
    except Exception as e:
        logger.error(f"ui_components_beautiful.py: {e}")
        return False

    return True


def check_api_keys() -> bool:
    """Check for configured API keys."""
    logger.header("🔑 Checking API Keys")

    Path(__file__).parent / ".env"

    api_keys = {
        "OPENAI_API_KEY": "OpenAI",
        "ANTHROPIC_API_KEY": "Claude (Anthropic)",
        "HUGGINGFACE_API_KEY": "HuggingFace",
        "GOOGLE_API_KEY": "Google Gemini",
    }

    found_keys = []
    missing_keys = []

    for env_var, provider in api_keys.items():
        if os.getenv(env_var):
            logger.success(f"{provider} key configured")
            found_keys.append(provider)
        else:
            missing_keys.append(provider)

    if not found_keys:
        logger.warning("No external LLM API keys configured")
        logger.info("You can add API keys later in the startup screen")

    return len(found_keys) > 0


# =============================================================================
# MAIN STARTUP CHECK
# =============================================================================


def run_startup_checks() -> Tuple[bool, Dict]:
    """Run all startup checks."""
    # [X-Ray auto-fix] print(f"\n{Color.BOLD}{Color.CYAN}{'=' * 70}{Color.END}")
    # [X-Ray auto-fix] print(f"{Color.BOLD}{Color.CYAN}🐀 RAG_RAT - Pre-flight System Check{Color.END}")
    # [X-Ray auto-fix] print(f"{Color.BOLD}{Color.CYAN}{'=' * 70}{Color.END}\n")
    checks_passed = True

    # Core checks
    if not check_python_version():
        checks_passed = False

    if not check_critical_imports():
        checks_passed = False

    check_optional_imports()
    check_directories()

    # LLM availability
    ollama, llama_cpp = check_local_llm_servers()

    # Custom modules
    if not check_custom_modules():
        checks_passed = False

    # API keys (optional)
    check_api_keys()

    # Summary
    logger.header("📊 Summary")
    report = logger.get_report()

    print(f"\n{Color.CYAN}Total checks: {report['total']}{Color.END}")
    if report["errors"] > 0:
        print(f"{Color.RED}Errors: {report['errors']}{Color.END}")
    if report["warnings"] > 0:
        print(f"{Color.YELLOW}Warnings: {report['warnings']}{Color.END}")

    return checks_passed, report


def handle_missing_dependencies() -> None:
    """Handle case of missing dependencies."""
    # [X-Ray auto-fix] print(f"\n{Color.RED}{Color.BOLD}⚠️  SETUP REQUIRED{Color.END}")
    # [X-Ray auto-fix] print(f"{Color.RED}{'=' * 70}{Color.END}\n")
    # [X-Ray auto-fix] print(f"Some required packages are missing. Please run:\n")
    # [X-Ray auto-fix] print(f"  {Color.CYAN}python install.py{Color.END}\n")
    # [X-Ray auto-fix] print(f"This will:\n")
    # [X-Ray auto-fix] print(f"  • Auto-install all dependencies")
    # [X-Ray auto-fix] print(f"  • Create required directories")
    # [X-Ray auto-fix] print(f"  • Check for local LLM servers")
    # [X-Ray auto-fix] print(f"  • Test all imports\n")
    # [X-Ray auto-fix] print(f"{Color.RED}{'=' * 70}\n")


def handle_success() -> None:
    """Handle successful startup check."""
    # [X-Ray auto-fix] print(f"\n{Color.GREEN}{Color.BOLD}✅ ALL CHECKS PASSED - READY TO START!{Color.END}")
    # [X-Ray auto-fix] print(f"{Color.GREEN}{'=' * 70}{Color.END}\n")


# =============================================================================
# ENTRY POINT
# =============================================================================


def main():
    """Main entry point."""
    checks_passed, report = run_startup_checks()

    # [X-Ray auto-fix] print(f"\n{Color.BOLD}{Color.CYAN}{'=' * 70}{Color.END}\n")
    if not checks_passed:
        handle_missing_dependencies()
        return False
    else:
        handle_success()
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
