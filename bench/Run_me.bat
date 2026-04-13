@echo off
title RAG Test Bench

:: Global llama.cpp defaults (shared across repos)
if "%ZENAI_LLAMA_SERVER%"=="" set "ZENAI_LLAMA_SERVER=C:\Ai\_bin\llama-server.exe"
if "%SWARM_MODELS_DIR%"=="" set "SWARM_MODELS_DIR=C:\Ai\Models"
if "%PATH:C:\Ai\_bin;=%"=="%PATH%" set "PATH=C:\Ai\_bin;%PATH%"

echo.
echo  +--------------------------------------------------------+
echo  :         RAG Test Bench                                 :
echo  :         Flask RAG Pipeline Benchmarking                :
echo  +--------------------------------------------------------+
echo.
echo Server: http://127.0.0.1:5050
echo Press Ctrl+C to stop
echo.

cd /d "%~dp0"

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else if exist env\Scripts\activate.bat (
    call env\Scripts\activate.bat
)

start "" http://127.0.0.1:5050
python app.py

pause
