@echo off
title ZEN AI RAG — AI Chat Assistant
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe zena_flet.py %*
) else (
    python zena_flet.py %*
)
pause
