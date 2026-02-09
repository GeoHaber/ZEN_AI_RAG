@echo off
setlocal

:: ZenAI Startup Script
:: --------------------
:: This script launches the main orchestrator which handles:
:: 1. Dependency checks
:: 2. LLM Engine (llama-server)
:: 3. Backend API
:: 4. Web UI (NiceGUI)

echo ===============================================================================
echo    ZEN AI LAUNCHER
echo ===============================================================================

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

:: Run the Orchestrator
echo [*] Starting ZenAI System...
echo.
python start_llm.py

:: If it crashes, pause so user can see error
if %errorlevel% neq 0 (
    echo.
    echo [CRITICAL] The application crashed unexpectedly.
    echo Please share "crash_log.txt" with support.
    pause
)

endlocal
