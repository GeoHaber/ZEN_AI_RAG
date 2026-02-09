@echo off
REM ============================================================================
REM ZEN_AI_RAG Fresh Installation Script (Windows)
REM ============================================================================
REM One-command setup for virgin systems
REM Handles: venv creation, pip upgrade, dependency install, verification
REM ============================================================================

setlocal enabledelayedexpansion
cls

echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                ZEN_AI_RAG Fresh Installation Setup                         ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM Check Python installation
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python not found!
    echo.
    echo Please install Python 3.12+ from https://www.python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   OK: Python %PYTHON_VERSION% detected
echo.

REM Create virtual environment
echo [2/5] Creating virtual environment...
if exist venv (
    echo   Using existing venv directory
) else (
    python -m venv venv
    if errorlevel 1 (
        echo   ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo   OK: Virtual environment created
)
echo.

REM Activate venv
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo   ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo   OK: Virtual environment activated
echo.

REM Upgrade pip, setuptools, wheel
echo [4/5] Upgrading pip, setuptools, wheel...
python -m pip install --quiet --upgrade pip setuptools wheel
if errorlevel 1 (
    echo   ERROR: Failed to upgrade pip tools
    pause
    exit /b 1
)
echo   OK: Pip tools upgraded
echo.

REM Install dependencies
echo [5/5] Installing dependencies from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo   ERROR: Failed to install dependencies
    echo   This may be a temporary network issue. Try again:
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo   OK: All dependencies installed
echo.

REM Verification
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                    Installation Complete!                                  ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo NEXT STEPS:
echo.
echo 1. Verify installation (optional but recommended):
echo    python verify_install.py
echo.
echo 2. Run the application:
echo    python zena.py
echo.
echo 3. To activate in future terminals:
echo    venv\Scripts\activate.bat
echo.
pause
