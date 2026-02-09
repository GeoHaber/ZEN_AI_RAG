#!/bin/bash
# ============================================================================
# ZEN_AI_RAG Fresh Installation Script (Linux/Mac)
# ============================================================================
# One-command setup for virgin systems
# Usage: bash install.sh
# ============================================================================

set -e  # Exit on error

clear
echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                ZEN_AI_RAG Fresh Installation Setup                         ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python installation
echo "[1/5] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "ERROR: Python 3 not found!"
    echo ""
    echo "Please install Python 3.12+ from https://www.python.org"
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   OK: Python ${PYTHON_VERSION} detected"
echo ""

# Create virtual environment
echo "[2/5] Creating virtual environment..."
if [ -d "venv" ]; then
    echo "   Using existing venv directory"
else
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "   ERROR: Failed to create virtual environment"
        exit 1
    fi
    echo "   OK: Virtual environment created"
fi
echo ""

# Activate venv
echo "[3/5] Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "   ERROR: Failed to activate virtual environment"
    exit 1
fi
echo "   OK: Virtual environment activated"
echo ""

# Upgrade pip, setuptools, wheel
echo "[4/5] Upgrading pip, setuptools, wheel..."
python -m pip install --quiet --upgrade pip setuptools wheel
if [ $? -ne 0 ]; then
    echo "   ERROR: Failed to upgrade pip tools"
    exit 1
fi
echo "   OK: Pip tools upgraded"
echo ""

# Install dependencies
echo "[5/5] Installing dependencies from requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo ""
    echo "   ERROR: Failed to install dependencies"
    echo "   This may be a temporary network issue. Try again:"
    echo "   pip install -r requirements.txt"
    echo ""
    exit 1
fi
echo "   OK: All dependencies installed"
echo ""

# Success message
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    Installation Complete!                                  ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Verify installation (optional but recommended):"
echo "   python verify_install.py"
echo ""
echo "2. Run the application:"
echo "   python zena.py"
echo ""
echo "3. To activate in future terminals:"
echo "   source venv/bin/activate"
echo ""
