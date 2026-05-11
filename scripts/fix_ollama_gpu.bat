@echo off
title Fix Ollama GPU Offload
echo ============================================
echo   Fix: Force Ollama to use full GPU
echo ============================================
echo.
echo Buoc 1: Dung Ollama hien tai (neu dang chay)
taskkill /f /im ollama.exe 2>nul
taskkill /f /im ollama_llama_server.exe 2>nul
timeout /t 2 >nul

echo.
echo Buoc 2: Set OLLAMA_NUM_GPU=99 (system-wide)
setx OLLAMA_NUM_GPU 99
echo   Da set OLLAMA_NUM_GPU=99

echo.
echo Buoc 3: Khoi dong lai Ollama
start "" "C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama app.exe"
timeout /t 5 >nul

echo.
echo Buoc 4: Kiem tra model da load len GPU chua
ollama ps
echo.
echo Neu thay "100%%" GPU -> OK.
echo Neu thay 0%% hoac thap -> GPU driver co van de, chay: nvidia-smi
echo.
echo Buoc 5: Pre-load model vao VRAM
ollama run qwen3:8b "/bye"
echo.
echo Done! Gio chay lai 3_run_ui.bat
pause
