@echo off
title [HR Search] Chainlit UI
echo ============================================
echo   Khoi dong Chainlit UI (port 7860)
echo ============================================
echo.

call conda activate dev-tuan
cd /d "%~dp0"
set "PYTHONPATH=%CD%"

REM Force Ollama to put ALL model layers on GPU (requires enough VRAM).
REM If you get OOM errors, reduce to e.g. 30 (partial offload).
set "OLLAMA_NUM_GPU=99"

echo Dang khoi dong...
echo UI se mo tai: http://localhost:7860
echo Nhan Ctrl+C de dung.
echo.

chainlit run app/chainlit_app.py --port 7860
pause
