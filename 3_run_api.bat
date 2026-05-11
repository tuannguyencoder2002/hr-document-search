@echo off
title [Document Search] FastAPI Server
echo ============================================
echo   Khoi dong FastAPI API (port 8000)
echo ============================================
echo.

call conda activate dev-tuan
cd /d "%~dp0"
set "PYTHONPATH=%CD%"

REM Force Ollama to use all GPU layers (see scripts\fix_ollama_gpu.bat
REM for a one-time system-wide setup).
set "OLLAMA_NUM_GPU=99"
set "OLLAMA_FLASH_ATTENTION=1"
set "OLLAMA_KEEP_ALIVE=30m"

echo Dang khoi dong...
echo API docs: http://localhost:8000/docs
echo Nhan Ctrl+C de dung.
echo.

uvicorn src.api.main:app --reload --port 8000
pause
