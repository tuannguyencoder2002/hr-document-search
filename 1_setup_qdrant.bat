@echo off
title [HR Search] Setup Qdrant Collection
echo ============================================
echo   Tao collection Qdrant (local embedded)
echo ============================================
echo.

call conda activate dev-tuan
cd /d "%~dp0"
set "PYTHONPATH=%CD%"

python -m scripts.setup_qdrant

echo.
echo Done! Collection da san sang.
pause
