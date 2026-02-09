@echo off
echo ========================================================
echo  ZenAI Startup Diagnostic Launcher
echo ========================================================
echo.
echo Launching start_llm.py...
echo.

python start_llm.py > startup_stdout.txt 2> startup_stderr.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] CRASH DETECTED (Exit Code: %ERRORLEVEL%)
    echo.
    echo --- ERROR OUTPUT (stderr) ---
    type startup_stderr.txt
    echo.
    echo -----------------------------
) else (
    echo.
    echo [OK] Execution finished successfully (or process exited normally).
)

echo.
echo Press any key to exit...
pause >nul
