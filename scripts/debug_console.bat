@echo off
title ZenAI Debug Console
echo ========================================================
echo  ZenAI Console Launcher (No Redirection)
echo ========================================================
echo.
echo Running 'python start_llm.py'...
echo If it crashes, the error should stay visible below.
echo.

python start_llm.py

echo.
echo --------------------------------------------------------
echo  Process finished or crashed.
echo --------------------------------------------------------
pause
