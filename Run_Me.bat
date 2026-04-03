@echo off
title ZEN AI RAG — AI Chat Assistant

:: Global llama.cpp defaults (shared across repos)
if "%ZENAI_LLAMA_SERVER%"=="" set "ZENAI_LLAMA_SERVER=C:\Ai\_bin\llama-server.exe"
if "%SWARM_MODELS_DIR%"=="" set "SWARM_MODELS_DIR=C:\Ai\Models"
if "%PATH:C:\Ai\_bin;=%"=="%PATH%" set "PATH=C:\Ai\_bin;%PATH%"

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
