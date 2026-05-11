@echo off
title [HR Search] FastAPI Server
echo ============================================
echo   Khoi dong FastAPI API (port 8000)
echo ============================================
echo.

call conda activate dev-tuan
cd /d "%~dp0"
set "PYTHONPATH=%CD%"

echo Dang khoi dong...
echo API docs: http://localhost:8000/docs
echo Nhan Ctrl+C de dung.
echo.

uvicorn src.api.main:app --reload --port 8000
pause
