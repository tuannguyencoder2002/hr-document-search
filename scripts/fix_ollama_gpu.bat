@echo off
title Fix Ollama GPU Offload + Flash Attention
echo ============================================
echo   Fix: Force Ollama to use full GPU
echo ============================================
echo.
echo Buoc 1: Dung Ollama hien tai (neu dang chay)
taskkill /f /im ollama.exe 2>nul
taskkill /f /im ollama_llama_server.exe 2>nul
timeout /t 2 >nul

echo.
echo Buoc 2: Set environment variables (system-wide, persistent)
setx OLLAMA_NUM_GPU 99
setx OLLAMA_FLASH_ATTENTION 1
setx OLLAMA_KEEP_ALIVE 30m
echo   OLLAMA_NUM_GPU=99 (all layers on GPU)
echo   OLLAMA_FLASH_ATTENTION=1 (faster + less VRAM for KV cache)
echo   OLLAMA_KEEP_ALIVE=30m (keep model resident between requests)

echo.
echo Buoc 3: Khoi dong lai Ollama
start "" "C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama app.exe"
timeout /t 5 >nul

echo.
echo Buoc 4: Pre-load model vao VRAM (ngan Ollama unload)
ollama run qwen3:8b "/bye"
timeout /t 3 >nul

echo.
echo Buoc 5: Kiem tra GPU offload
ollama ps
echo.
echo ============================================
echo   KET QUA MONG DOI:
echo   - SIZE_VRAM gan bang SIZE (100%% GPU)
echo   - Neu thap: GPU khong du VRAM, thu giam num_ctx
echo   - Toc do mong doi: 25-35 tok/s tren RTX 5060
echo ============================================
echo.
echo Neu OK, chay lai 3_run_ui.bat
echo Neu van cham, chay: nvidia-smi (xem GPU co bi process khac chiem)
pause
