@echo off
echo Starting ZenAI RAG Debug Mode...
echo This script will capture all output to 'crash_log.txt'
echo.

python start_llm.py > crash_log.txt 2>&1

echo.
echo ===================================================
echo        SERVER STOPPED / CRASHED
echo ===================================================
echo.
echo The log has been saved to: crash_log.txt
echo Please share the contents of that file.
echo.
pause
