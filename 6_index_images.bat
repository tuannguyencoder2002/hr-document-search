@echo off
title [Document Search] Index Images (CLIP)
echo ============================================
echo   Extract + Index anh tu tai lieu (CLIP)
echo ============================================
echo.
echo [!] LUU Y: Tat FastAPI (3_run_api.bat) truoc khi chay.
echo.
pause

call conda activate dev-tuan
cd /d "%~dp0"
set "PYTHONPATH=%CD%"

if not exist "data\corpus" (
    echo [!] Thu muc data\corpus khong ton tai.
    pause
    exit /b
)

echo Dang extract va index anh tu data\corpus ...
echo (Chi xu ly PDF va DOCX co anh nhung)
echo.
python scripts/index_images.py --folder data/corpus
set ERR=%ERRORLEVEL%

echo.
if %ERR% neq 0 (
    echo [!] Co loi. Xem log phia tren.
) else (
    echo Done! Anh da duoc index vao collection hr_images.
)
pause
