@echo off
:: ZenAI Launcher - Use this to start ZenAI
:: This batch file keeps the console open so you can see any errors.

cd /d "%~dp0"
echo Starting ZenAI...
echo.

python start_llm.py

echo.
echo ====================================
echo ZenAI has exited.
if exist crash_log.txt (
    echo.
    echo CRASH LOG FOUND:
    type crash_log.txt
)
echo ====================================
pause
