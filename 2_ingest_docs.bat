@echo off
title [HR Search] Ingest Documents
echo ============================================
echo   Ingest tai lieu HR vao Qdrant
echo ============================================
echo.

call conda activate dev-tuan
cd /d "%~dp0"
set "PYTHONPATH=%CD%"

if not exist "data\corpus" (
    mkdir "data\corpus"
    echo [!] Thu muc data\corpus vua duoc tao.
    echo     Hay bo file PDF/DOCX/TXT vao do roi chay lai.
    pause
    exit /b
)

dir /b /s "data\corpus\*.pdf" "data\corpus\*.docx" "data\corpus\*.txt" "data\corpus\*.md" >nul 2>&1
if errorlevel 1 (
    echo [!] Thu muc data\corpus khong co file indexable.
    echo     Hay bo file PDF/DOCX/TXT/MD vao do roi chay lai.
    pause
    exit /b
)

echo Dang ingest cac file tu data\corpus ...
echo.
python -m scripts.ingest_folder --folder data/corpus --doc-type learning --department IT
set ERR=%ERRORLEVEL%

echo.
if %ERR% neq 0 (
    echo [!] Ingest co loi ^(exit code %ERR%^). Xem log phia tren.
) else (
    echo Done! Tai lieu da duoc index.
)
pause
