@echo off
title [Document Search] Ingest Documents
echo ============================================
echo   Ingest tai lieu vao Qdrant
echo ============================================
echo.
echo [!] LUU Y: Tat FastAPI (3_run_api.bat) truoc khi chay script nay.
echo     Qdrant local mode chi cho 1 process truy cap cung luc.
echo     Neu FastAPI dang chay, nhan Ctrl+C o terminal do truoc.
echo.
pause

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
echo (Incremental: chi embed file moi hoac da thay doi)
echo.
python -m scripts.ingest_folder --folder data/corpus --doc-type learning --department IT
set ERR=%ERRORLEVEL%

echo.
if %ERR% neq 0 (
    echo [!] Ingest co loi ^(exit code %ERR%^). Xem log phia tren.
    echo     Neu loi "AlreadyLocked" -> tat FastAPI truoc khi ingest.
) else (
    echo Done! Tai lieu + anh da duoc index.
    echo Gio co the chay lai 3_run_api.bat va 5_run_web.bat.
)
pause
