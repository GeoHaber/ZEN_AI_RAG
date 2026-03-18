@echo off
title ZEN AI RAG — AI Chat Assistant
cd /d "%~dp0"
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if not "%%A:~0,1%%"=="#" if not "%%A"=="" set "%%A=%%B"
    )
)
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe zena_flet.py %*
) else (
    python zena_flet.py %*
)
pause
