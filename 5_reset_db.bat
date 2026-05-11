@echo off
title [HR Search] Reset Database
echo ============================================
echo   XOA va tao lai collection Qdrant
echo   (Tat ca tai lieu da index se bi mat!)
echo ============================================
echo.

call conda activate dev-tuan
cd /d "%~dp0"
set "PYTHONPATH=%CD%"

set /p confirm="Ban co chac muon xoa? (y/N): "
if /i not "%confirm%"=="y" (
    echo Huy bo.
    pause
    exit /b
)

python -m scripts.reset_db

echo.
echo Done! Database da reset.
pause
